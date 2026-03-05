import asyncio
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from .collector import get_all_info
from astrbot.api import logger

@register("astrbot_plugin_fox_status", "GoodBoyboy", "一个用于获取 AstrBot 机器状态的插件。", "1.0.2")
class MyPlugin(Star):
    def __init__(self, context: Context, config: dict):
        super().__init__(context)
        self.config = config
    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""

    @filter.command("状态", alias={'状态信息', 'status'})
    async def status(self, event: AstrMessageEvent):
        """获取系统状态"""
        event.stop_event()
        # 对接插件配置
        config = self.config if self.config else {}
        
        # 异步调用 collector 的逻辑
        result = await asyncio.to_thread(get_all_info, config)
        
        yield event.plain_result(result)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""