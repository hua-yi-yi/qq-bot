# QQ AI 聊天机器人（NoneBot2 + NapCat + 大模型）

基于 **NoneBot2 + NapCat(OneBot V11) + OpenAI 兼容大模型** 的 QQ 聊天机器人。
私聊自动回复、群聊 @/触发词 回复、多轮上下文记忆、插件式扩展。

```
📱 手机 QQ 小号 ──登录──> [NapCat Shell (Windows 无头)] ──OneBot反向WS──> [NoneBot2 (WSL2)] ──LLM API──> [DeepSeek / 硅基流动 / 其他]
```

- **NapCat**：Windows 侧，用小号登录 QQ，把收发消息转成标准 OneBot 协议
- **NoneBot2**：WSL2/Linux 侧，机器人框架，处理消息、调用大模型并发回
- 连接方式：NapCat 主动连 `ws://127.0.0.1:8080/onebot/v11/ws`（Windows→WSL2 的 localhost 转发，无需配网络）

## ✨ 功能特性

- 💬 私聊：任何文字消息自动回复
- 👥 群聊：被 @ 时回复（并 @ 回你）；消息以触发词开头（默认 `AI`）也回复；纯 @ 无内容自动忽略
- 🧠 每个会话（人 / 群+人）独立记住最近 8 轮上下文
- 🚦 防刷屏：同一条会话上一条未回完时忽略新消息
- 🔄 `/清空记忆`（或 `/clear`、`/reset`、`/新对话`）重置上下文
- 🎭 人设可改（插件内 `SYSTEM_PROMPT`）· 触发词可配（`.env` `GROUP_TRIGGERS`）
- 🎯 关键词自动回复：命中关键词直接回固定内容（**文字/图片**），不调用大模型 · 配置在 `src/plugins/qqchat/replies.json`，改完保存即生效

---

## 一、机器人侧（WSL2/Linux）

```bash
conda activate qqbot            # 或任意 Python 3.11+ 环境
cd ~/Desktop/qq-chatbot
pip install -r requirements.txt # 首次装依赖
```

### 1. 配置大模型（编辑 `.env`）

```ini
LLM_API_KEY=你的Key
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

**方案选择（三选一）**：

| 方案 | 说明 | 备注 |
|------|------|------|
| ① 硅基流动（默认） | [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 注册，送体验金；`DeepSeek-V4-Flash` 又快又便宜 | 体验金用完需充值（10 元够用很久） |
| ② 阿里云百炼（免费额度） | [bailian.console.aliyun.com](https://bailian.console.aliyun.com) 新用户可领约 7000 万 token；`LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1` | 免费，量大，需实名 |
| ③ DeepSeek 官方 | [platform.deepseek.com](https://platform.deepseek.com)，`LLM_BASE_URL=https://api.deepseek.com/v1`、`LLM_MODEL=deepseek-chat` | 充值 10 元起 |

> ⚠️ 2026 年起硅基流动已取消"永久免费模型"档，所有模型都需余额；免费首选**阿里云百炼**。

**验证 Key（不用等 QQ）**：
```bash
curl https://api.siliconflow.cn/v1/chat/completions \
  -H "Authorization: Bearer 你的Key" -H "Content-Type: application/json" \
  -d '{"model":"deepseek-ai/DeepSeek-V4-Flash","messages":[{"role":"user","content":"你好"}],"max_tokens":50}'
```
返回 JSON 内容即成功；报 402「balance is insufficient」= 余额不足，充值或换方案。

### 2. 启动机器人（先启动它，NapCat 才能连上）

```bash
python bot.py
```

看到 `OneBot V11 ... WebSocket` 监听 8080、以及后续 `Bot <QQ号> connected` 即成功。

---

## 二、NapCat 侧（Windows）

> 需要 **Windows 10/11 x64** + 已安装 **QQ 桌面版（9.9.15+）**。建议用**小号**（第三方协议有封号风险）。

### 安装（官方推荐：Shell 手动启动）

1. 下载 **`NapCat.Shell.zip`**：https://github.com/NapNeko/NapCatQQ/releases/latest
2. 解压到**不含空格/中文**的路径（如 `D:\NapCat\Shell`）
3. 双击 **`launcher.bat`** 启动（会请求管理员权限，UAC 点"是"；
   Win10 用 `launcher-win10.bat`；自动从注册表找到 QQ 安装路径）
4. 首次登录：Shell 无头模式**不弹 QQ 窗口**，二维码在 `cache/qrcode.png`；
   也可浏览器打开 **`http://127.0.0.1:6099/webui`**（登录令牌看控制台输出或 `config/webui.json` 的 `token` 字段）扫码
5. **手机 QQ（小号）扫码** → 登录成功
6. 之后每次启动自动登录（快速登录：`launcher.bat 你的QQ号`）

> 无头模式控制台看不到就查日志：`Shell/logs/` 下的 `.log` 文件。

### 配置 OneBot 反向 WebSocket（连接机器人）

**方法 A：直接改配置文件**（推荐，部署脚本已这么做）：
编辑 `Shell/config/onebot11_你的QQ号.json`：
```json
{
  "network": {
    "websocketClients": [
      {
        "name": "NoneBot",
        "enable": true,
        "url": "ws://127.0.0.1:8080/onebot/v11/ws",
        "messagePostFormat": "array",
        "token": ""
      }
    ]
  }
}
```
重启 NapCat（关掉 QQ 进程后重新运行 launcher.bat）生效。

**方法 B：WebUI 点击**：网络配置 → 新建 WebSocket 客户端 → 地址 `ws://127.0.0.1:8080/onebot/v11/ws`、消息格式 Array、令牌留空。

> 连不上的话：确认 WSL2 里 `python bot.py` 在跑；或把地址换成 WSL2 IP（`hostname -I` 查看），
> 且 `.env` 里 `HOST=0.0.0.0`（已默认）。

---

## 三、测试

1. 另一个 QQ 私聊小号发 **"你好"** → 收到 AI 回复
2. 群里 **@机器人** → 回复并 @ 你
3. 群里发 **"AI 今天天气怎么样"**（不 @）→ 也会回复
4. 发 **/清空记忆** → 重置上下文

---

## 四、常见问题 FAQ

**Q1: 机器人回复"调用大模型出错啦：…402…balance is insufficient"**
大模型余额不足。硅基流动充值 10 元，或换[阿里云百炼免费额度](https://bailian.console.aliyun.com)（改 `.env` 三行）。

**Q2: 回复很慢（20 秒以上）**
用了排队严重的免费/低优先级模型。换 `deepseek-ai/DeepSeek-V4-Flash`（默认，约 1 秒）或百炼的 `qwen-turbo`。

**Q3: NapCat 连不上 ws://127.0.0.1:8080**
① 确认 `python bot.py` 在跑；② Windows→WSL2 localhost 转发未开时，改连 `ws://<WSL2-IP>:8080/onebot/v11/ws`。

**Q4: QQ 提示损坏 / 缺 DLL**
装微软运行库 https://aka.ms/vs/17/release/vc_redist.x64.exe ；QQ 版本过低则升级 QQ。

**Q5: 群聊里机器人没反应**
需要 @它 或消息以触发词（默认 `AI`）开头；`GROUP_TRIGGERS` 可改。

**Q6: 想长期 7×24 运行**
把 NapCat 换成 Docker 版、NoneBot 用 systemd 守护，部署到云服务器（见 https://napneko.github.io/ ）。

---

## 五、GitHub 托管（本仓库）

> 仓库：**https://github.com/hua-yi-yi/qq-bot**（公开 · MIT 许可）· 推送走 SSH 443 通道

```bash
git add . && git commit -m "更新说明" && git push
# 换新机器克隆（公开仓库，二选一）：
git clone https://github.com/hua-yi-yi/qq-bot.git            # 通用方式
git clone ssh://git@ssh.github.com:443/hua-yi-yi/qq-bot.git  # 本机 GitHub 被墙时走 SSH 443
cp .env.example .env   # 新建配置并填自己的 Key
```

> ⚠️ 本机 hosts 屏蔽了 GitHub，必须用 SSH 443；`.gitignore` 已排除 `.env`，密钥不会上传。

---

## 六、项目结构 & 扩展

```
qq-chatbot/
├── bot.py                     # 入口：注册 OneBot V11 适配器 + 加载插件
├── .env                       # 全部配置（密钥，不上传）
├── .env.example               # 配置模板
├── requirements.txt
└── src/plugins/qqchat/        # 聊天插件（私聊/群聊/记忆/重置）
    ├── __init__.py            # 聊天逻辑 + 关键词自动回复层
    └── replies.json           # 关键词自动回复规则（改完即生效，无需重启）
```

- **加功能**：nonebot2 插件生态，搜索 `nonebot-plugin`，一个文件夹放 `src/plugins/` 即生效
- **改人设**：插件内 `SYSTEM_PROMPT`
- **多账号**：NapCat 多开 + 多个 WS 客户端连不同端口

---

## 七、关键词自动回复（文字 / 图片）

检测到消息里**包含**指定关键词时，直接回复固定内容，**不调用大模型**（毫秒级、省 token）；没命中才走 AI 聊天。

配置在 `src/plugins/qqchat/replies.json`，**改完保存立即生效**（热重载，无需重启 `python bot.py`）。

```json
{
  "enabled": true,
  "rules": [
    {
      "name": "菜单",
      "enabled": true,
      "keywords": ["菜单", "价格表"],
      "reply": "这是最新菜单～",
      "image": "D:\\NapCat\\images\\menu.png",
      "scope": "all",
      "require_at": false,
      "at_sender": false,
      "ignore_case": true
    }
  ]
}
```

| 字段 | 说明 |
|------|------|
| `keywords` | 关键词数组，消息文本**包含**任意一个即命中（默认忽略大小写） |
| `reply` | 回复的文字（可选，与 `image` 至少填一个） |
| `image` | 回复的图片（可选）。支持 ① 本地文件 `D:\NapCat\images\a.png` ② 网络地址 `https://...` ③ `base64://...` |
| `scope` | `all` 私聊+群聊 / `private` 仅私聊 / `group` 仅群聊 |
| `require_at` | 仅群聊；`true` 表示必须 @ 机器人才触发 |
| `at_sender` | 仅群聊；`true` 表示回复时顺带 @ 发送者 |
| `enabled` | 总开关或单条规则开关，`false` 临时停用 |

> ⚠️ 本地图片必须放在 **NapCat（Windows 侧）能读到的路径**，推荐统一放 `D:\NapCat\images\`；放 WSL 的 `/home/<用户名>/...` 里 NapCat 读不到。
> 规则按数组顺序匹配，**第一条命中即回复并结束**，不会继续走 AI。
> 文字与图片可同时填，会拼成一条消息（先文字后图片）。
