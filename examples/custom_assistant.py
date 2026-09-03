"""完整示例：创建一个自定义的 OpenVoice Desktop 助手，注册自己的技能和 Agent。

运行前先: pip install -e .
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from assistant.core.app import Assistant
from assistant.skills.base import Skill


def main():
    app = Assistant()

    # 1. 自定义唤醒词
    app.config.set("wake.word", "小助手")
    print("唤醒词已设为:", app.config.get("wake.word"))

    # 2. 注册一个自定义技能
    def hello_handler(params, ctx):
        name = params.get("name", "朋友")
        return f"你好，{name}！"

    app.skills.register(Skill(
        name="greet",
        description="打招呼",
        patterns=[r"(?:你好|嗨)\s*(?P<name>.*)"],
        keywords=["你好"],
        handler=hello_handler,
    ))

    # 3. 查看所有技能
    print("\n已注册技能:")
    for m in app.skills.all_manifests():
        print(f"  - {m['name']}: {m['description']}")

    # 4. 测试自定义技能
    result = app.handle_text("你好 小明")
    print("\n测试: 你好 小明 ->", result)

    # 5. 带情绪朗读
    print("\n（带情绪朗读需要 TTS + 网络/声卡）")
    # app.speak("今天真开心！", emotion="happy")

    app.shutdown()
    print("\n示例运行完成！")

if __name__ == "__main__":
    main()
