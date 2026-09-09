"""LLM 聊天插件。

行为：
- 私聊：任何文字消息都会回复
- 群聊：被 @ 时回复；或消息以触发词开头（默认 "AI"）时回复
- 每条会话（私聊=人，群聊=人+群）保留最近若干轮上下文记忆
- 发送 /清空记忆（或 /clear /reset /新对话）可重置当前会话记忆
"""
import asyncio
import json
from collections import deque
from pathlib import Path

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


# ------------------------------------------------------------------ 关键词自动回复
# 配置在同目录 replies.json，改完保存立即生效（热重载，无需重启机器人）
_REPLY_FILE = Path(__file__).parent / "replies.json"
_reply_cache: dict = {"mtime": None, "rules": [], "enabled": True}


def _load_reply_rules() -> None:
    """按需加载 replies.json：文件 mtime 变化时才重新读取。"""
    try:
        st = _REPLY_FILE.stat()
    except OSError:
        if _reply_cache["rules"]:
            logger.warning("replies.json 不存在，关键词回复已停用")
            _reply_cache.update({"mtime": None, "rules": [], "enabled": True})
        return

    if _reply_cache["mtime"] == st.st_mtime:
        return  # 没变，用缓存

    try:
        data = json.loads(_REPLY_FILE.read_text(encoding="utf-8"))
        rules = data.get("rules") or []
        if not isinstance(rules, list):
            raise ValueError("rules 字段必须是数组")
        _reply_cache.update({
            "mtime": st.st_mtime,
            "rules": [r for r in rules if isinstance(r, dict)],
            "enabled": bool(data.get("enabled", True)),
        })
        logger.info(
            f"关键词回复规则已加载：{len(_reply_cache['rules'])} 条"
            f"（全局开关 {'开' if _reply_cache['enabled'] else '关'}）"
        )
    except Exception as e:
        logger.error(f"replies.json 解析失败，继续沿用上一版规则：{e}")
        _reply_cache["mtime"] = st.st_mtime  # 避免同一条错误反复刷屏


def _match_reply(ev: MessageEvent) -> dict | None:
    """按顺序匹配规则，返回命中的规则字典；未命中返回 None。"""
    _load_reply_rules()
    if not _reply_cache["enabled"]:
        return None

    text = _plain_text(ev)
    if not text:
        return None

    is_private = isinstance(ev, PrivateMessageEvent)
    low = text.lower()

    for rule in _reply_cache["rules"]:
        if not rule.get("enabled", True):
            continue
        # 作用范围：all / private / group
        scope = str(rule.get("scope", "all")).lower()
        if scope == "private" and not is_private:
            continue
        if scope == "group" and is_private:
            continue
        # 群聊可选：必须 @ 机器人才触发
        if not is_private and rule.get("require_at") and not getattr(ev, "to_me", False):
            continue
        # 关键词：命中任意一个即可（包含匹配）
        keywords = rule.get("keywords")
        if isinstance(keywords, str):
            keywords = [keywords]
        if not keywords:
            continue
        ignore_case = bool(rule.get("ignore_case", True))
        haystack = low if ignore_case else text
        for kw in keywords:
            needle = str(kw).lower() if ignore_case else str(kw)
            if needle and needle in haystack:
                return rule
    return None


def _keyword_rule(ev: MessageEvent) -> bool:
    """规则函数：命中才让本 matcher 运行，否则完全放行给后面的 AI 聊天。"""
    return _match_reply(ev) is not None


def _image_file(value: str) -> str:
    """图片参数归一化：URL / base64 原样透传，本地路径转成 file:/// 形式。"""
    v = value.strip()
    if v.startswith(("http://", "https://", "file://", "base64://", "data:")):
        return v
    if len(v) > 2 and v[1] == ":":  # Windows 盘符，如 D:\pics\a.png
        return "file:///" + v.replace("\\", "/")
    return v


# priority=5 < 聊天插件的 10，所以先于大模型处理；block=True 命中后不再调 AI
keyword_reply = on_message(rule=_keyword_rule, priority=5, block=True)


@keyword_reply.handle()
async def handle_keyword(ev: MessageEvent):
    rule = _match_reply(ev)
    if not rule:
        return

    segments: list[MessageSegment] = []
    if isinstance(ev, GroupMessageEvent) and rule.get("at_sender"):
        segments += [MessageSegment.at(ev.user_id), MessageSegment.text(" ")]

    reply = str(rule.get("reply", "")).strip()
    if reply:
        segments.append(MessageSegment.text(reply))

    image = str(rule.get("image", "")).strip()
    if image:
        segments.append(MessageSegment.image(_image_file(image)))

    if not segments:
        return
    await keyword_reply.finish(Message(segments))
