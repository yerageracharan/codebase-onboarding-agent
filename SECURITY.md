# Security Policy

Do not publicly disclose exploitable details, repository credentials, private source code, or secret values in issues or pull requests.

Use GitHub's Security tab and **Report a vulnerability** flow for a private report when private vulnerability reporting is enabled. If it is unavailable, contact the repository owner privately through their GitHub profile and ask for a secure disclosure route. Do not publish details while arranging contact.

Include the affected version/commit, exact component, reproducible steps using a synthetic repository, observed impact, and redacted logs. Never attach a real private repository archive or live credentials.

This agent intentionally scans untrusted repository content. A security report should explain how an attacker crosses a boundary in this tool (for example, code execution, archive path escape, or secret disclosure), not merely that a scanned repository contains risky code.
