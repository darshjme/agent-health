# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | ✅ Yes    |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, email **security@your-org.example** with:

1. A description of the vulnerability.
2. Steps to reproduce.
3. Potential impact.
4. Suggested fix (optional).

We will acknowledge your report within **48 hours** and aim to release a patch within **7 days** for critical issues.

## Security Design Notes

- `agent-health` has **zero runtime dependencies** — the attack surface is limited to the Python standard library.
- `HttpCheck` uses `urllib.request` and does **not** disable SSL verification by default.
- `DiskSpaceCheck` uses `shutil.disk_usage` (read-only, no elevated permissions required).
- `MemoryCheck` reads `/proc/meminfo` (read-only on Linux).
- No credentials, tokens, or secrets are stored or logged by this library.
