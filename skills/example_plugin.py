"""Example plugin: define `register_skills(registry)` to add your own skill."""
from assistant.skills.base import Skill


def register_skills(registry):
    def say_hello(params, ctx):
        return "你好呀，我是一个本地插件技能！"

    registry.register(Skill(
        name="hello_plugin",
        description="示例插件：打招呼",
        patterns=["你好插件", "hello plugin"],
        keywords=["插件"],
        handler=say_hello,
    ))
