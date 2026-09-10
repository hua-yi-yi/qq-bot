# QQ AI 聊天机器人

**NoneBot2 + NapCat(OneBot V11) + OpenAI 兼容大模型**。
私聊自动回复、群聊 @/触发词 回复、多轮上下文记忆、关键词自动回复。

```
手机 QQ 小号 ─登录→ [NapCat Shell (Windows)] ─反向WS→ [NoneBot2 (WSL2/Linux)] ─→ 大模型 API
```

NapCat 在 Windows 侧用小号登录 QQ 并转成 OneBot 协议，NoneBot2 在 WSL2/Linux 侧处理消息、调用大模型。
NapCat 主动连 `ws://127.0.0.1:8080/onebot/v11/ws`，走 localhost 转发，无需配网络。

## 功能

- 私聊：任何文字消息自动回复
- 群聊：被 @ 必定回复并 @ 回去；以触发词开头（默认 `AI`）时按概率插话（`.env` `GROUP_REPLY_PROB`，默认 5%）
- 每个会话（人 / 群+人）独立记忆最近 8 轮上下文，防刷屏（上一条未回完忽略新消息）
- `/清空记忆`（或 `/clear`、`/reset`、`/新对话`）重置上下文
- 关键词自动回复：命中关键词直接回固定内容（文字/图片），不调用大模型
- 人设可改（插件内 `SYSTEM_PROMPT`）、触发词可配（`.env` `GROUP_TRIGGERS`）

## 一、机器人侧（WSL2/Linux）

```bash
pip install -r requirements.txt   # Python 3.11+
cp .env.example .env              # 填入自己的 Key
python bot.py                     # 先启动它，NapCat 才能连上
```

`.env` 三行大模型配置（OpenAI 兼容接口，三家任选）：

```ini
LLM_API_KEY=你的Key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

| 方案 | Base URL / Model |
|------|------------------|
| [硅基流动](https://cloud.siliconflow.cn)（默认，便宜快） | `https://api.siliconflow.cn/v1` · `deepseek-ai/DeepSeek-V4-Flash` |
| [阿里云百炼](https://bailian.console.aliyun.com)（新用户免费额度大） | `https://dashscope.aliyuncs.com/compatible-mode/v1` · `qwen-turbo` |
| [DeepSeek 官方](https://platform.deepseek.com)（需充值） | `https://api.deepseek.com/v1` · `deepseek-chat` |

看到 `OneBot V11 ... WebSocket` 监听 8080、以及 `Bot <QQ号> connected` 即成功。

## 二、NapCat 侧（Windows）

需要 Windows 10/11 x64 + QQ 桌面版 9.9.15+。**建议用小号**（第三方协议有封号风险）。

1. 下载 [`NapCat.Shell.zip`](https://github.com/NapNeko/NapCatQQ/releases/latest)，解压到不含空格/中文的路径（如 `D:\NapCat\Shell`）
2. 双击 `launcher.bat` 启动（UAC 点"是"；Win10 用 `launcher-win10.bat`）
3. 首次登录：无头模式不弹 QQ 窗口，二维码在 `cache/qrcode.png`，也可开 `http://127.0.0.1:6099/webui` 扫码（令牌见控制台或 `config/webui.json`）；之后启动自动登录
4. 配置反向 WS：编辑 `Shell/config/onebot11_你的QQ号.json`，在 `network.websocketClients` 加一项后重启 NapCat：

```json
{ "name": "NoneBot", "enable": true, "url": "ws://127.0.0.1:8080/onebot/v11/ws",
  "messagePostFormat": "array", "token": "" }
```

也可以在 WebUI「网络配置 → 新建 WebSocket 客户端」里填同样的地址（消息格式 Array、令牌留空）。

## 三、测试

1. 另一个 QQ 私聊小号发「你好」→ 收到 AI 回复
2. 群里 @机器人 → 回复并 @ 你；群里发「AI 今天天气怎么样」→ 也会回复
3. 发 `/清空记忆` → 重置上下文

## 四、关键词自动回复

消息**包含**关键词时直接回固定内容，不调用大模型；没命中才走 AI。
配置在 `src/plugins/qqchat/replies.json`，**改完保存立即生效**（热重载，无需重启）。

```json
{
  "enabled": true,
  "rules": [
    { "name": "菜单", "enabled": true, "keywords": ["菜单", "价格表"],
      "reply": "这是最新菜单～", "image": "D:\\NapCat\\images\\menu.png",
      "scope": "all", "require_at": false, "at_sender": false, "ignore_case": true }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `keywords` | 包含任意一个即命中（默认忽略大小写） |
| `reply` / `image` | 文字 / 图片，至少填一个，可同时填（先文字后图片）；图片支持本地路径、`https://`、`base64://` |
| `scope` | `all` / `private` / `group` |
| `require_at` / `at_sender` | 仅群聊：是否必须 @机器人触发 / 回复时是否 @ 发送者 |
| `enabled` | 总开关或单条规则开关 |

> 按数组顺序匹配，**第一条命中即回复并结束**。本地图片必须放在 NapCat（Windows 侧）能读到的路径，推荐 `D:\NapCat\images\`。

## 五、FAQ

- **报 402 balance is insufficient**：大模型余额不足，充值或换阿里云百炼免费额度（改 `.env` 三行）。
- **回复很慢**：用了排队严重的免费模型，换 `deepseek-ai/DeepSeek-V4-Flash` 或 `qwen-turbo`。
- **NapCat 连不上 8080**：确认 `python bot.py` 在跑；localhost 转发不通时改连 `ws://<WSL2-IP>:8080/onebot/v11/ws`（`hostname -I` 查看）。
- **QQ 提示损坏 / 缺 DLL**：装 [VC 运行库](https://aka.ms/vs/17/release/vc_redist.x64.exe)，或升级 QQ。
- **群里没反应**：需要 @它 或以触发词（默认 `AI`）开头。
- **想 7×24 运行**：NapCat 用 Docker 版 + systemd 守护，部署到云服务器（见 https://napneko.github.io/ ）。

## 六、项目结构

```
bot.py                  # 入口：注册 OneBot V11 适配器 + 加载插件
.env / .env.example     # 全部配置（.env 含密钥，不上传）
start-bot.sh            # start|stop|restart|status|log
src/plugins/qqchat/
├── __init__.py         # 聊天逻辑 + 关键词自动回复层
└── replies.json        # 关键词规则（改完即生效）
```

- **加功能**：找 `nonebot-plugin` 插件，丢进 `src/plugins/` 即生效
- **多账号**：NapCat 多开 + 多个 WS 客户端连不同端口

## 许可

MIT · 仓库：https://github.com/hua-yi-yi/qq-bot
