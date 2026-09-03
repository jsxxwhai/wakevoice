# Contributing

Thank you for your interest in contributing to OpenVoice Desktop!

## Setup

```bash
git clone <repo-url>
cd openvoice-desktop
pip install -e .[dev]
```

## Running tests and lint

```bash
python -m pytest tests/ -q
python -m ruff check src/ tests/
```

## Adding a skill

A skill is a small, self-describing callable. Register it through `SkillRegistry`:

```python
from assistant.skills.base import Skill

def my_handler(params, ctx):
    return "done"

registry.register(Skill(
    name="my_skill",
    description="what it does",
    patterns=[r"(?:触发|trigger)\s*(?P<arg>.+)"],
    keywords=["触发"],
    handler=my_handler,
))
```

For a drop-in local plugin, add a `.py` file to the `skills/` directory that
exposes `register_skills(registry)`.

## Adding an agent

```python
from assistant.agents.hub import Agent
app.agents.register(Agent(name="translator", role="翻译",
                          description="多语言翻译助手"))
```

## Style

- Target Python 3.10+.
- Keep imports lazy in hot paths to preserve the low-memory goal.
- Keep replies natural and warm; the assistant should not sound like a robot.

## Releasing

Maintainers publish a version by pushing a tag; CI then runs the full
test + lint gate and, only if everything passes, creates a GitHub Release
with the built `sdist`/`wheel` artifacts attached.

Before the first public release:

1. Put the real repository URL in `pyproject.toml` (`[project.urls]`) and in
   the README, replacing the `jsxxwhai` placeholders.
2. Add the remote and log in once:

   ```bash
   git remote add origin https://github.com/jsxxwhai/openvoice-desktop
   gh auth login
   ```

3. Tag and push:

   ```bash
   git tag v0.1.1
   git push origin main
   git push origin v0.1.1
   ```

The `Release` workflow (`.github/workflows/release.yml`) builds the package and
publishes the release using the automatic `GITHUB_TOKEN`; no personal token is
stored in the repository. You can also create a release from your local CLI with
`python scripts/publish_github.py`.
