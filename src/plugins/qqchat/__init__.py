"""LLM 聊天插件。

行为：
- 私聊：任何文字消息都会回复
- 群聊：被 @ 时回复；或消息以触发词开头（默认 "AI"）时回复
- 每条会话（私聊=人，群聊=人+群）保留最近若干轮上下文记忆
- 发送 /清空记忆（或 /clear /reset /新对话）可重置当前会话记忆
"""
import asyncio
from collections import deque

from nonebot import get_driver, on_command, on_message
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
    PrivateMessageEvent,
)
from nonebot.log import logger
from openai import AsyncOpenAI

# ------------------------------------------------------------------ 配置
driver = get_driver()
_conf = driver.config

API_KEY = str(getattr(_conf, "llm_api_key", "") or "").strip()
BASE_URL = str(getattr(_conf, "llm_base_url", "") or "").strip()
MODEL = str(getattr(_conf, "llm_model", "deepseek-chat") or "").strip()
MAX_TOKENS = max(64, int(getattr(_conf, "llm_max_tokens", 1024) or 1024))
TRIGGERS = [
    t.strip().lower()
    for t in str(getattr(_conf, "group_triggers", "AI") or "").split(",")
    if t.strip()
]

# 判定 Key 是否真实可用（排除 .env 里的占位符）
_KEY_INVALID = not API_KEY or (
    "在这里粘贴" in API_KEY or API_KEY.startswith("sk-你的") or "your_api" in API_KEY.lower()
)

SYSTEM_PROMPT = (
    "你是一个友善的 QQ 聊天机器人助手，名字叫「小Q」。"
    "回答简洁、自然、口语化，使用简体中文；不知道的事就直说不知道，不要编造。"
)

_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=API_KEY, base_url=BASE_URL)
    return _client


# ------------------------------------------------------------------ 会话状态
# 会话 id -> 最近 N 条消息（user/assistant 交替）
_histories: dict[str, deque[dict[str, str]]] = {}
# 会话 id -> 处理锁：同一会话上一条没回完就忽略新消息，避免重复回复
_busy: dict[str, asyncio.Lock] = {}
HISTORY_MAX = 16  # 记住最近 16 条（约 8 轮对话）


def _session_id(ev: MessageEvent) -> str:
    """会话标识：私聊按人，群聊按 群+人。"""
    if isinstance(ev, PrivateMessageEvent):
        return f"private:{ev.user_id}"
    return f"group:{ev.group_id}:{ev.user_id}"


def _plain_text(ev: MessageEvent) -> str:
    """只取文本内容（去掉 @、图片、表情等 CQ 码）。"""
    return "".join(
        seg.data.get("text", "") for seg in ev.message if seg.type == "text"
    ).strip()


# ------------------------------------------------------------------ 触发规则
def _chat_rule(ev: MessageEvent) -> bool:
    if isinstance(ev, PrivateMessageEvent):
        return True  # 私聊全接
    if isinstance(ev, GroupMessageEvent):
        if ev.to_me:  # 被 @
            return True
        low = _plain_text(ev).lower()
        return any(low.startswith(tg) for tg in TRIGGERS)
    return False


chat = on_message(rule=_chat_rule, priority=10, block=True)


@chat.handle()
async def handle_chat(bot: Bot, ev: MessageEvent):
    sid = _session_id(ev)

    if _KEY_INVALID:
        await chat.finish(
            "我还没配置大模型 API Key 呢。\n"
            "请在项目根目录的 .env 文件里填好 LLM_API_KEY（顺便看下 LLM_BASE_URL / LLM_MODEL），"
            "然后重启机器人（Ctrl+C 后重新 python bot.py）。"
        )

    text = _plain_text(ev)
    if not text:
        return  # 纯图片/表情等消息，不处理

    # 群聊触发词模式：去掉触发词本身，剩下的才是要聊的内容
    if isinstance(ev, GroupMessageEvent) and not ev.to_me:
        low = text.lower()
        for tg in TRIGGERS:
            if low.startswith(tg):
                text = text[len(tg):].lstrip(" ，,。.:：！!?？")
                break
        if not text:
            return

    hist = _histories.setdefault(sid, deque(maxlen=HISTORY_MAX))
    lock = _busy.setdefault(sid, asyncio.Lock())
    if lock.locked():
        return  # 正在处理上一条，忽略本条，避免重复回复

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *list(hist),
        {"role": "user", "content": text},
    ]

    async with lock:
        try:
            async with asyncio.timeout(90):
                resp = await get_client().chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=0.7,
                )
            reply = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            logger.opt(exception=True).error("LLM 调用失败")
            await chat.finish(f"调用大模型出错啦：{type(e).__name__}: {e}")

    if not reply:
        await chat.finish("（模型这次没返回内容，换个说法再问我一次吧～）")

    reply = reply[:3000]  # 防止超长消息被 QQ 截断
    hist.append({"role": "user", "content": text})
    hist.append({"role": "assistant", "content": reply})

    if isinstance(ev, GroupMessageEvent):
        await chat.finish(Message(MessageSegment.at(ev.user_id)) + " " + reply)
    else:
        await chat.finish(reply)


# ------------------------------------------------------------------ 清空记忆
reset_cmd = on_command(
    "清空记忆",
    aliases={"clear", "reset", "新对话", "重置"},
    priority=1,
    block=True,
)


@reset_cmd.handle()
async def handle_reset(bot: Bot, ev: MessageEvent):
    sid = _session_id(ev)
    if _histories.pop(sid, None) is not None:
        await reset_cmd.finish("好的，我已忘记之前的对话，我们重新开始吧～")
    await reset_cmd.finish("本来就没有记住什么呀，直接开始聊吧～")
