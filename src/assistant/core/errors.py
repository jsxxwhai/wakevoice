"""Exception hierarchy for the assistant."""
from __future__ import annotations


class AssistantError(Exception):
    """Base error for the project."""


class ConfigError(AssistantError):
    """Invalid or missing configuration."""


class WakeWordError(AssistantError):
    """Wake-word engine failure."""


class STTError(AssistantError):
    """Speech-to-text failure."""


class TTSError(AssistantError):
    """Text-to-speech failure."""


class SkillError(AssistantError):
    """A skill raised a handled error."""


class MCPServerError(AssistantError):
    """MCP server connection or protocol error."""


class ScreenError(AssistantError):
    """Screen capture / OCR failure."""
