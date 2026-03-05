# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x.x   | Yes                |
| < 2.0   | No                 |

## Reporting a Vulnerability

If you discover a security vulnerability in this project, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainer or use GitHub's private vulnerability reporting feature.
3. Include a description of the vulnerability, steps to reproduce, and potential impact.

## Security Considerations

- **Personal Access Tokens**: Calendly API tokens are stored in the macOS Keychain via Alfred's secure password storage (`wf.save_password` / `wf.get_password`). Tokens are never written to disk in plaintext.
- **API Communication**: All Calendly API requests use HTTPS (`https://api.calendly.com`).
- **No Telemetry**: This workflow does not collect or transmit any user data beyond what is required for Calendly API calls.
- **Dependencies**: GitHub Actions are pinned to specific commit hashes to prevent supply chain attacks. Dependabot monitors for updates.
