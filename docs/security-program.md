# TaskBrain Finance Security Program

Last updated: June 10, 2026

This document defines the initial security program for TaskBrain Finance while it is operated as a small private beta. It is intended to become more formal before broader public availability.

## Information Security Policy

TaskBrain Finance stores and processes consumer financial data only for the purpose of read-only personal financial dashboards, cash-flow forecasting, recurring expense analysis, AI-assisted financial summaries, and planning tools.

The application does not initiate payments, transfers, ACH flows, account verification, account changes, or trades.

Security objectives:

- Protect financial data from unauthorized access.
- Keep Plaid access tokens, OpenAI API keys, session secrets, and encryption keys out of source control.
- Require user authentication and authenticator-app MFA before Plaid Link can be opened.
- Encrypt sensitive integration tokens before database storage.
- Keep production services private or protected by HTTPS and a trusted access boundary.
- Maintain a documented patch, vulnerability, access-review, deletion, and retention process.

## Access Control Policy

Access to TaskBrain Finance is limited to named user accounts. Shared accounts are not allowed.

Roles:

- `owner`: can manage user access and security settings.
- `member`: can use personal finance features for their own account.

Rules:

- The first registered account is the initial `owner`.
- Later registered accounts default to `member`.
- Disabled accounts cannot log in or use existing sessions.
- The backend prevents removing the last active owner.
- MFA is required before a user can create or exchange a Plaid Link token.
- Secrets are stored only in environment variables or ignored local files.
- Owner-only security endpoints expose recent audit events and access-review records.
- Account registration, successful login, MFA changes, user access changes, Plaid connection changes, and access-review completion are written to an audit log.

## MFA Policy

Users must enable authenticator-app TOTP MFA before connecting financial institutions through Plaid Link. Password-only accounts may sign in, but they cannot open Plaid Link or add new institution connections.

Internal operator accounts that administer the host, GitHub, Plaid, OpenAI, or deployment environment should use MFA wherever those services support it.

## Data Encryption Policy

Current controls:

- Plaid access tokens are encrypted before storage.
- MFA TOTP secrets are encrypted before storage.
- API keys and application secrets are stored outside source control.
- Session cookies are HTTP-only, signed, and set `secure` outside local development.

Required before broader consumer launch:

- Enable full-disk encryption or database-level encryption for the host that stores SQLite data.
- Document key backup and key rotation procedures.
- Verify backups are encrypted at rest.

## Data Retention And Deletion Policy

Consumer financial data is retained only while the user keeps an active TaskBrain Finance account and/or active Plaid connection.

Deletion controls:

- Disconnecting a Plaid Item attempts to revoke the Plaid Item and removes associated local accounts, balances, transactions, recurring streams, snapshots, sync history, and AI summaries.
- Disabled user accounts cannot access the application.
- Full account deletion should be completed before broader public launch.

Retention review:

- Review retained accounts and Plaid Items at least quarterly during private beta.
- Remove test users, stale connections, and unneeded local databases.
- Keep only backups that are needed for recovery, and delete expired backups.

## Vulnerability Management Policy

Run the local security audit before production changes and at least monthly during beta:

```bash
./.venv/bin/python finance/backend/scripts/security_audit.py
```

The audit includes local secret/config checks, runtime EOL/support checks, an inactive-user deprovisioning dry run, Python dependency auditing, and frontend dependency auditing.

Patch targets:

- Critical vulnerabilities: patch or mitigate within 7 days.
- High vulnerabilities: patch or mitigate within 14 days.
- Medium vulnerabilities: patch or mitigate within 30 days.
- Low vulnerabilities: review during the next monthly maintenance window.

If a vulnerability cannot be patched inside the target window, document the reason, compensating control, and planned remediation date.

## End-Of-Life Software Policy

The owner should review operating system, Python, Node.js, browser/runtime, and application dependency support status at least quarterly. The local security audit runs `finance/backend/scripts/eol_check.py` to record runtime support evidence.

EOL software should be upgraded or removed before it reaches unsupported status whenever practical. Unsupported software that stores or processes consumer financial data must not be used for a public release without a documented compensating control and migration plan.

## Access Reviews And Deprovisioning

Review user access at least quarterly during private beta. The owner should create and complete an in-app access review before inviting beta users and then repeat the review quarterly or after any role/access change.

Review items:

- Active app users and roles.
- Active Plaid Items.
- GitHub repository access.
- Plaid Dashboard access.
- OpenAI Platform access.
- Raspberry Pi host access.

Deprovisioning steps:

- Disable app users that no longer need access.
- Run `finance/backend/scripts/deprovision_inactive_users.py` on a daily cron schedule to disable inactive non-owner app users.
- Remove dashboard/platform access for people who no longer need it.
- Revoke or rotate credentials if a device, account, or secret may be compromised.
- Record the review date, reviewer, changes made, and follow-up actions.

## Review Log Template

Use this format for each quarterly review:

```text
Date:
Reviewer:
Scope reviewed:
Users removed or changed:
Secrets rotated:
Vulnerabilities found:
Patches applied:
Backups verified:
Follow-up actions:
```
