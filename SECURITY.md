# Security policy

## Supported version

Security fixes target the latest `main` branch and the current 1.x release.

## Reporting

Please use the repository's private **Security → Report a vulnerability** flow.
Do not publish an exploit in a public issue before a fix is available.

Include the affected route or file, reproduction steps, impact, and any proposed
mitigation. Never include real credentials or unrelated personal data.

## Current public surface

The v1 server accepts GET and HEAD requests only. It has no account system,
wallet, visitor posting, file upload, arbitrary model prompt, or administrative
mutation route. It emits a restrictive content-security policy and renders
autonomous text from a closed narrator.

Deployments should run one unprivileged container, expose only the application
port, keep the SQLite volume private, terminate TLS at the hosting platform, and
apply platform-level request limits.
