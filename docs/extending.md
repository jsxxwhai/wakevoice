# 扩展指南：加技能 / Agent / MCP

## 1. 添加一个技能（最简单）

```python

from assistant.skills.base import Skill, SkillContext

def my_skill():

    def handler(params, ctx):

        return "你触发了自定义技能！"

    return Skill(

        name="my_skill",

        description="我的自定义技能",

        patterns=[r"(?:测试|自定义)"],

        keywords=["测试"],

        handler=handler,

    )

# 在 app 里注册：

app.skills.register(my_skill())

```

## 2. 添加一个 Agent

```python

from assistant.agents.hub import Agent, AgentContext

agent = Agent(

    name="translator",

    role="翻译官",

    description="中英互译",

    handler=lambda text, ctx: translate(text),

)

app.agents.register(agent)

```

## 3. 自定义唤醒词

编辑 config/config.example.yaml：

```yaml

wake:

  word: 你好伙伴   # 改成任意唤醒词

```

## 4. 接入自定义 MCP 服务器

在 config.yaml 的 mcp.servers 里添加：

```yaml

mcp:

  servers:

    - name: my_server

      command: ["python", "my_mcp_server.py"]

```

然后调用：

```python

result = app.mcp.call("my_server", "tool_name", {"arg": 1})

```

## 5. 切换情绪语音

```python

# 开心

app.speak("今天天气真好！", emotion="happy")

# 难过

app.speak("我有点难过。", emotion="sad")

# 生气

app.speak("这太过分了！", emotion="angry")

```

