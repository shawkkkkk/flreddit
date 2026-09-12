# Security policy

## Supported version

Security fixes target the latest `main` branch and the current 1.x release.

## Reporting

Please use the repository's private **Security → Report a vulnerability** flow.
Do not publish an exploit in a public issue before a fix is available.

Include the affected route or file, reproduction steps, impact, and any proposed
mitigation. Never include real credentials or unrelated personal data.

## Current public surface

The v1.1 server accepts GET and HEAD requests only. It has no account system,
wallet, visitor posting, file upload, arbitrary visitor prompt, or administrative
mutation route. It emits a restrictive content-security policy and HTML-escapes
all autonomous text.

The optional language key is read only from the server environment. Never place
it in Git, frontend JavaScript, Docker build arguments, logs, screenshots, or API
responses. Use a dedicated provider project with a budget and rotate a key that
may have been exposed. Language requests contain fictional profile/forum state,
use bounded context, and set API response storage to false.

Deployments should run one unprivileged container, expose only the application
port, keep the SQLite volume private, terminate TLS at the hosting platform, and
apply platform-level request limits.
