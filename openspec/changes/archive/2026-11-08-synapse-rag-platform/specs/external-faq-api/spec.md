# Spec Delta

## Purpose

Gives each external account a self-service FAQ endpoint secured by a dedicated key pair so third parties can query their own knowledge without internal credentials.

## ADDED Requirements

### Requirement: Per-account API key and secret

The system SHALL issue each account an API key and API secret (stored hashed, rotatable, revocable) managed by admins and visible in full only at issuance/rotation.

#### Scenario: Issuance returns secret once

- **WHEN** an admin issues credentials for an account
- **THEN** the system returns the key and the plaintext secret exactly once and thereafter only shows key metadata

#### Scenario: Rotation invalidates old secret

- **WHEN** an admin rotates an account's secret
- **THEN** the old secret stops authenticating and the new one works immediately

### Requirement: External FAQ endpoint with key-secret auth

The system SHALL expose a stateless FAQ endpoint authenticating via API key + secret that answers only from the credential-bound account's own documents under RLS; `internal` documents and `audit: `-prefixed inputs SHALL NOT receive special handling — `audit: ` text is treated as a literal question string. The endpoint SHALL be rate-limited per key and return 429 when exceeded.

#### Scenario: Valid credentials get scoped answer

- **WHEN** an external caller presents a valid key/secret pair and a question
- **THEN** the system returns a grounded answer limited to that account's own documents

#### Scenario: Invalid or revoked credentials rejected

- **WHEN** a caller presents an unknown key, wrong secret, or revoked pair
- **THEN** the system responds 401 and performs no retrieval

#### Scenario: Cross-account access impossible via API

- **WHEN** account A's credentials query content belonging solely to account B
- **THEN** the system withholds B's content under RLS

#### Scenario: Audit prefix has no effect externally

- **WHEN** an external caller sends a question starting with `audit: `
- **THEN** the system treats it as literal question text against account A's own documents and never touches audit data
