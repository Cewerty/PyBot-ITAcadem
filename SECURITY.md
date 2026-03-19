# Security Policy

## Supported Versions

Security fixes are expected primarily for:

| Version / Branch | Supported |
| --- | --- |
| `main` | :white_check_mark: |
| Latest stable release | :white_check_mark: |
| Older releases | :warning: best effort only |
| Unmaintained historical versions | :x: |

If a vulnerability only affects an old unsupported version but not the current codebase, a fix is not guaranteed.

## Reporting a Vulnerability

There is no bug bounty program for this project.

That said, responsible security reports are welcome and appreciated.

If you discover a security issue:

- Report critical issues privately so maintainers have time to investigate and fix them before public disclosure.
- Prefer private GitHub security reporting if it is available for the repository.
- If private GitHub reporting is unavailable, contact the maintainers directly through a non-public channel before opening a public issue.
- Do not publish a public issue first for critical vulnerabilities.

When writing a report:

- Be polite, clear, and professional.
- Describe the affected component, expected behavior, actual behavior, impact, and conditions under which the issue appears.
- Use general wording for exploitation details instead of providing a fully weaponized attack recipe.
- Do not include raw secrets, tokens, personal data, or other sensitive information in the report.
- Keep the report focused on functionality directly related to the bot, its integrations, and its business logic.
- Do not spend effort testing unrelated systems, third-party infrastructure, or functionality outside the actual scope of this project.

## Proof of Concept Guidance

Proofs of concept are allowed only in a limited, safe form.

- A PoC must demonstrate the issue without being directly usable for a real attack.
- Do not provide a complete exploit script, automated attack chain, mass scanner, or turnkey payload for real-world abuse.
- Prefer minimal reproduction steps, sanitized snippets, redacted screenshots, or reduced examples.
- If a PoC could realistically be reused against a live system, reduce it further before sharing it.

## Disclosure Expectations

For critical and high-severity issues:

- Report privately first.
- Give maintainers reasonable time to validate and remediate the issue.
- Coordinate public disclosure only after a fix, mitigation, or joint disclosure decision.

For lower-severity issues:

- A public issue may be acceptable if it does not materially increase risk, but private reporting is still preferred when in doubt.

## Legal and Data Protection Notes

This project should operate in a way that is compatible with Russian personal data requirements, including Federal Law No. 152-FZ on personal data.

When reporting issues:

- Avoid collecting, storing, or sharing unnecessary personal data.
- Minimize the use of real user data in examples and reproductions.
- Prefer sanitized or synthetic test data whenever possible.

## Guidance for Security Researchers

Please follow a simple "do no harm" standard:

- Do not degrade service availability.
- Do not attempt destructive actions, privilege escalation in real environments, mass scanning, spam, or data exfiltration.
- Do not test beyond what is necessary to confirm the issue.
- Do not pursue "fame-first" reporting. Responsible disclosure matters more than fast publication.
- Leave the project safer than you found it.

## What to Expect From Maintainers

Maintainers will try to:

- acknowledge a good-faith report in a reasonable timeframe;
- assess severity and reproducibility;
- ask clarifying questions if needed;
- coordinate remediation and disclosure when the report is valid.

Not every report will result in an immediate fix, but responsible reports are valued.
