# Security

## Scope

DeCypher is a controlled threat-intelligence demonstration platform. The repository contains synthetic data and an authorized local/mock scanner environment.

The scanner and autonomous mode are intended for targets that you are explicitly authorized to assess.

## Scanner safety boundary

- Autonomous scanning is disabled by default.
- The default scanner allowlist is limited to `127.0.0.1` and `localhost`.
- Do not point the scanner at third-party infrastructure without explicit authorization.
- Do not use the project to bypass access controls, deanonymize uninvolved individuals, or collect credentials.
- Treat scanner configuration changes as security-sensitive.

The normal HTTP scanner path verifies TLS by default (SCANNER_TLS_VERIFY=true) and disables redirects. The certificate-fingerprint detector intentionally uses a separate non-verifying TLS socket because it must observe certificate identity even when the certificate is self-signed or otherwise untrusted in the controlled fixture. Both paths are limited to the configured authorized-host allowlist.

## Secrets

Never commit:

- `.env` files
- API keys
- passwords
- private keys
- local TLS certificates
- database credentials

Use the provided `backend/.env.example` as a starting point.

## Reporting a security issue

For a vulnerability in this repository, do not publish exploit details in a public issue before the maintainer has had an opportunity to investigate.

Provide:

1. A concise description of the affected component.
2. Reproduction steps using the smallest safe example possible.
3. The security impact you observed.
4. Any relevant logs or screenshots with secrets and personal data removed.

For urgent issues, contact the repository owner through the GitHub account associated with this project.
