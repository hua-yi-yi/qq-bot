# QQ AI 聊天机器人（NoneBot2 + NapCat + 大模型）

架构一览：

```
你的手机QQ小号 ──登录──> [NapCat Shell (Windows)]  ──OneBot反向WS──> [NoneBot2 (WSL2/Linux)] ──OpenAI兼容API──> [DeepSeek / OpenAI / 其他]
```

- **NapCat**：跑在 **Windows**，负责用你的 QQ 小号登录并把收发消息转成标准 OneBot 协议
- **NoneBot2**：跑在 **WSL2**（本项目位置），机器人框架，收到消息后调用大模型并回复
- 两者通过 WebSocket 连接：NapCat 主动连 `ws://127.0.0.1:8080/onebot/v11/ws`（Windows 的 127.0.0.1:8080 会自动转发进 WSL2，无需额外配网络）

---

## 一、机器人侧（本项目，已在 WSL2 就绪）

```bash
conda activate qqbot
cd ~/Desktop/qq-chatbot        # 项目根目录
pip install -r requirements.txt  # 首次运行前装一次依赖
```

1. 编辑 **`.env`**，把 `LLM_API_KEY` 换成你的真实 Key（其余默认即可）
   - 默认已配**硅基流动免费模型**：注册 [SiliconFlow](https://cloud.siliconflow.cn)（手机号即可、不充值）→
     控制台「API 密钥」页创建 Key 粘贴进去即可；免费模型有限速但个人聊天够用
   - 想要效果更强的：注册 [DeepSeek 开放平台](https://platform.deepseek.com) 充 10 元，
     把 `.env` 里 `LLM_BASE_URL=https://api.deepseek.com/v1`、`LLM_MODEL=deepseek-chat`
   - 换模型前可用下面命令先验证 Key 和模型 id（不用等 QQ）：
     ```bash
     curl https://api.siliconflow.cn/v1/chat/completions \
       -H "Authorization: Bearer 你的Key" -H "Content-Type: application/json" \
       -d '{"model":"Qwen/Qwen2.5-7B-Instruct","messages":[{"role":"user","content":"你好"}]}'
     ```
     返回内容即成功；报"模型不存在"就去控制台「模型广场」找一个标【免费】的模型 id 替换
2. 启动机器人（**先启动它**，NapCat 才能连上来）：

```bash
python bot.py
```

看到日志里出现 `OneBot V11 ... WebSocket` / 监听 8080 之类的字样即成功。
此时 Windows 的 `http://127.0.0.1:8080/onebot/v11/ws` 应该可以连上（可由 NapCat 验证）。

---

## 二、NapCat 侧（在 Windows 上操作）

> 需要 **Windows 10/11 x64**。建议用**小号**，第三方协议有一定封号风险。

1. 下载一键包：https://github.com/NapNeko/NapCatQQ/releases/latest
   → 下载 **`NapCat.Shell.Windows.OneKey.zip`**
2. 解压到**不含空格和中文**的路径，例如 `D:\NapCat\`（官方强调这点，否则可能启动失败）
3. 双击运行 **`NapCatInstaller.exe`**，等待它自动化部署（会联网准备 QQ 运行环境，稍等片刻）
4. 进入部署生成的 `NapCat.XXXX.Framework` 目录，双击运行 **`NapCatWinBootMain.exe`**
5. QQ 登录窗口出现 → 用**你的小号手机 QQ** 扫码登录（提示 QQ 损坏/频繁弹窗时，装
   [LiteLoaderQQNT-Kill-Update](https://github.com/Mzdyl/LiteLoaderQQNT-Plugin-Loader/issues) 相关插件，见下方 FAQ）
6. 登录成功后控制台会打印 **WebUI 地址和随机密码**，浏览器打开（默认 `http://127.0.0.1:6099/webui`）登录

### 配置 OneBot 反向 WebSocket（让 NapCat 连上 NoneBot）

在 NapCat WebUI 里：

1. 进入 **网络配置（Network）**
2. 新建一个 **WebSocket 客户端（WS Client / 反向 WS）**
3. 设置：
   - 上报地址 / URL：`ws://127.0.0.1:8080/onebot/v11/ws`
   - 消息格式：`Array`（数组）
   - 访问令牌：**留空**（两侧都要为空，保持一致）
4. 保存后 NapCat 会自动重连。若显示连接成功 → 大功告成！

> 若连不上，看下文 FAQ「连不上 8080」。

---

## 三、测试

1. 用另一个 QQ 号给机器人小号发一句 **"你好"** → 应收到大模型回复
2. 把机器人小号拉进群，群里 **@它** 说话 → 回复并 @ 你
3. 群里不 @，发 **"AI 今天天气怎么样"** → 也会回复（触发词可在 .env 的 `GROUP_TRIGGERS` 改）
4. 发送 **/清空记忆** 可重置上下文

---

## 四、常见问题 FAQ

**Q1: NapCat 连不上 ws://127.0.0.1:8080**
先确认 WSL2 里 `python bot.py` 正在运行。
如果仍不行，可能是 Windows→WSL2 的 localhost 转发未开，改用 WSL2 的 IP：
在 WSL2 里执行 `hostname -I`（如 `172.22.x.x`），把 NapCat 地址改成
`ws://172.22.x.x:8080/onebot/v11/ws`（注意 .env 里 `HOST=0.0.0.0` 已保证可被外部连入；
若是该模式需在 Windows 防火墙放行对应端口）。

**Q2: 提示 QQ 文件损坏 / 频繁弹窗**
安装插件 [LiteLoaderQQNT-Kill-Update](https://github.com/Mzdyl/LiteLoaderQQNT-Plugin-Loader)，或在 NapCat 交流群求助。

**Q3: 缺 DLL / 运行库**
安装微软运行库：https://aka.ms/vs/17/release/vc_redist.x64.exe

**Q4: 机器人回复报错「401/鉴权失败」**
`.env` 里 `LLM_API_KEY` 填错或平台余额不足；`LLM_BASE_URL`/`LLM_MODEL` 与平台不匹配。

**Q5: 机器人没反应**
① 私聊没反应：NapCat 是否已登录且 WS 显示已连接；
② 群聊没反应：需要 @机器人 或 触发词开头（见 `.env` 的 `GROUP_TRIGGERS`）；
③ 看 bot.py 所在终端日志有没有报错。

**Q6: 如何开机自启 / 长期运行**
以后部署到云服务器（Linux）可把 NapCat 换成 Docker 版、NoneBot 用 systemd/supervisor 守护，教程见
https://napneko.github.io/ ；本项目在 Windows 下临时跑建议直接开两个终端。

---

## 五、把项目托管到 GitHub（可选）

```bash
cd ~/Desktop/qq-chatbot
git init
git add .
git commit -m "init: QQ AI chatbot (nonebot2 + onebot v11)"
# 在 GitHub 网页新建空仓库后（不要勾选生成 README）：
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

> `.gitignore` 已排除 `.env`，密钥不会上传。以后换机器：`git clone` + 复制一份 `.env` 即可。

---

## 六、扩展方向

- 插件生态：nonebot2 有海量现成插件（搜 `nonebot-plugin`），放一个文件夹进 `src/plugins/` 即生效
- 换模型/加人设：改 `.env` 与插件里的 `SYSTEM_PROMPT`
- 多账号：NapCat 支持多开，配多个 WS 客户端连不同端口
- 本项目结构：
  - `bot.py` — 入口
  - `.env` — 全部配置（密钥在这里）
  - `src/plugins/qqchat/` — 聊天插件本体
