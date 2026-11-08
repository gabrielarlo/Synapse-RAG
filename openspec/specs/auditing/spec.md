# Auditing Specification

## Purpose

Provides admins with an auditable view of platform activity, including natural-language audit questions that query event data instead of document vectors.

## Requirements

### Requirement: Admin-only audit surface

The system SHALL restrict all audit reads (trail UI/API) to `admin` role users and SHALL log auditable events (logins, uploads, ingestions, questions, escalations, credential issuance/rotation).

#### Scenario: Admin reads audit trail

- **WHEN** an admin requests the audit trail
- **THEN** the system returns timestamped events with actor, action, and scope

#### Scenario: Staff blocked from audit

- **WHEN** a staff user requests the audit trail
- **THEN** the system responds 403

### Requirement: audit-prefixed questions query events not vectors

Questions starting with `audit: ` (exact prefix, case-sensitive) on the internal path from an admin SHALL be answered from audit/event data and SHALL NOT trigger triage, retrieval, or generation; the prefix check runs after authz and before triage. Non-admin `audit: ` questions SHALL be rejected with 403. The external FAQ API SHALL NOT implement this requirement (see external-faq-api).

#### Scenario: Admin audit question answered

- **WHEN** an admin asks `audit: how many users do upload files today?`
- **THEN** the system returns a count computed from upload events for today with the time window stated

#### Scenario: Non-admin audit question rejected

- **WHEN** a staff user sends any `audit: `-prefixed question
- **THEN** the system responds 403 and performs no audit computation

### Requirement: V1 audit intent allowlist

V1 SHALL support exactly these audit intents: uploads count per day, active uploading users per day, questions count per account per day, escalation count per department per day, and login count per day. Any `audit: ` question outside this set SHALL be refused with a message listing the supported questions; all aggregations SHALL use parameterized queries only.

#### Scenario: Unsupported audit question refused

- **WHEN** an admin asks an `audit: ` question outside the allowlist
- **THEN** the system refuses with the list of supported audit questions and runs no ad-hoc query
