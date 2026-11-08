# Auth Identity Specification

## Purpose

Provides authenticated, role-scoped identity for the platform so admins manage every tenant while staff only ever see and act within their assigned accounts.

## Requirements

### Requirement: JWT authentication

The system SHALL authenticate internal users via JWT access tokens issued at login and SHALL reject expired or invalid tokens with 401.

#### Scenario: Login issues token

- **WHEN** a user posts valid credentials to the login endpoint
- **THEN** the system returns a signed JWT access token and a refresh mechanism

#### Scenario: Invalid token rejected

- **WHEN** a request carries an expired or malformed token
- **THEN** the system responds 401 without revealing which check failed

### Requirement: Admin and staff roles

The system SHALL support `admin` and `staff` roles where admins manage all tenants and staff are restricted to accounts explicitly assigned to them.

#### Scenario: Admin sees all tenants

- **WHEN** an admin lists accounts
- **THEN** the system returns every account in the system

#### Scenario: Staff sees only assigned accounts

- **WHEN** a staff user lists accounts
- **THEN** the system returns only accounts assigned to that staff user

#### Scenario: Staff blocked from unassigned account

- **WHEN** a staff user requests a resource in an account not assigned to them
- **THEN** the system responds 403

### Requirement: Per-request scope resolution

Every scoped request SHALL resolve exactly one explicit `account_id` (query/body param, required except for admins listing), verify the caller's membership for that account, and set it as the single RLS scope for the request; admins bypass membership via a separate policy but still pass an explicit `account_id` when acting within an account. The chat endpoint is exempt: omitting `account_id` there resolves to the internal-only scope (internal documents, no account content).

#### Scenario: Staff must name their account

- **WHEN** a staff user calls a scoped endpoint without `account_id` or with an unassigned `account_id`
- **THEN** the system responds 422 for the missing case and 403 for the unassigned case, performing no data access

#### Scenario: Chat defaults to internal scope

- **WHEN** a user posts a chat question without `account_id`
- **THEN** the system answers from internal documents only and never exposes any account's content

#### Scenario: Admin acts with explicit scope

- **WHEN** an admin calls a scoped endpoint with a valid `account_id`
- **THEN** the system applies that account's scope for the request

### Requirement: Staff to account many-to-many assignment

The system SHALL allow admins to assign a staff user to one or more accounts and an account to have multiple staff, with assignment changes effective on the next request.

#### Scenario: Assign staff to multiple accounts

- **WHEN** an admin assigns one staff user to two accounts
- **THEN** that staff user can access both accounts and no others

#### Scenario: Revoke assignment

- **WHEN** an admin removes a staff↔account assignment
- **THEN** subsequent requests by that staff to that account return 403

### Requirement: Rate-limited authentication endpoints

The system SHALL rate-limit login and token endpoints per client IP and SHALL return 429 with a retry hint when the limit is exceeded.

#### Scenario: Login brute force throttled

- **WHEN** a client exceeds the login attempt limit within the window
- **THEN** the system responds 429 without revealing whether credentials were valid
