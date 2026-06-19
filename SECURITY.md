**English** | [Italiano](SECURITY.it.md)

# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.3.x | Yes, latest release |
| < 0.3 | No |

Sysbar is in active development. Security fixes are applied to the latest
release and the current `main`.

## Reporting a Vulnerability

To report a security vulnerability, use [GitHub Security
Advisories](https://github.com/AndreaBonn/sysbar/security/advisories/new).

Please include:
- Description of the vulnerability
- Steps to reproduce
- Expected vs actual behavior
- Impact assessment (what an attacker could achieve)

Response timeline:
- Acknowledgment: within 72 hours
- Fix for critical issues: within 30 days
- Coordinated public disclosure after the fix is released

## Security Measures Implemented

These are the measures verified in the codebase, not aspirational claims.

- **Minimal network surface**: the only network call the app makes is an
  optional update check against the GitHub Releases API over HTTPS, disabled
  through the `auto-check-updates` setting and bounded by a 5 second timeout
  (`src/sysbar/services/update_service.py`). The network speed metric is the
  other outbound path (`src/sysbar/services/metrics/speedtest.py`). No account,
  no telemetry.
- **No shell injection**: external commands are run through `subprocess` with
  arguments passed as a list, never `shell=True` (verified across `src/`;
  `src/sysbar/services/uninstall/command_query.py`,
  `src/sysbar/services/uninstall/package_remover.py`).
- **Privileged operations behind polkit**: package removal is delegated to the
  system package manager under a polkit authorization, not run as a raw
  privileged call (`src/sysbar/services/uninstall/package_remover.py`).
- **No secrets**: the app stores no credentials or tokens. Runtime configuration
  lives in GSettings; no environment variables are required in production
  (`.env.example`).
- **Dependency pinning**: the resolved dependency set is committed in `uv.lock`.

## Security Best Practices for Users

- Install only from the official [releases
  page](https://github.com/AndreaBonn/sysbar/releases) or the signed APT
  repository, and verify the published SHA256 of the `.deb` before installing.
- Keep the system GTK bindings updated through your distribution.

## Out of Scope

The following are not considered vulnerabilities for this project:

- Social engineering attacks
- Physical attacks against the machine
- Vulnerabilities in third-party dependencies already publicly disclosed (report
  these to the upstream maintainer)
- Denial of service through excessive legitimate use

## Acknowledgments

Security researchers who responsibly disclose vulnerabilities will be listed
here.

---

[Back to README](./README.md)
