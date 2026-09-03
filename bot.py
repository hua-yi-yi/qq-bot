"""QQ 聊天机器人入口。

启动方式（在项目根目录）：
    conda activate qqbot
    python bot.py
"""
import nonebot
from nonebot import get_driver

# 初始化 NoneBot（会自动读取根目录 .env）
nonebot.init()

# 注册 OneBot V11 协议适配器（NapCat 就是通过这个协议连过来的）
from nonebot.adapters.onebot.v11 import Adapter  # noqa: E402

driver = get_driver()
driver.register_adapter(Adapter)

# 加载 src/plugins/ 下的所有插件（聊天逻辑在里面）
nonebot.load_plugins("src/plugins")

if __name__ == "__main__":
    nonebot.run()
