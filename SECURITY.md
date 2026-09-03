# Security Policy

## Supported Versions

Only the latest release is actively supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

Please **do not** open a public issue for security vulnerabilities.

Instead, report them privately by emailing the maintainers. We will respond
within a reasonable time and work with you to resolve the issue responsibly.

## Security Notes

- WakeVoice processes local audio and can execute skills that control the
  desktop (open apps, simulate keyboard/mouse, read the screen). Only enable
  skills you trust and review the skills you install.
- Never commit API keys, access tokens, or personal memory files. Use
  environment variables (e.g. `OPENAI_API_KEY`) and the `.gitignore` rules.
- The extension (Model Context Protocol) client launches arbitrary commands
  configured in `config.yaml`. Only point it at servers you trust.
