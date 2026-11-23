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

### Requirement: User deactivation

The system SHALL let an admin deactivate any other user by id. Deactivation SHALL be persisted on the user, SHALL be idempotent, SHALL be recorded in the audit trail, and SHALL NOT delete the user or their account assignments. An admin SHALL NOT be able to deactivate themselves through the API even if the UI hides the action.

#### Scenario: Admin deactivates another user

- **WHEN** an admin posts to the deactivate endpoint with another user's id
- **THEN** the system marks that user inactive, returns success, and appends a `user_deactivate` audit event

#### Scenario: Unknown or self target rejected

- **WHEN** an admin posts with an unknown user id or their own id
- **THEN** the system responds 404 for the unknown id and 422 for self, changing no user

#### Scenario: Non-admin cannot deactivate

- **WHEN** a staff user posts to the deactivate endpoint
- **THEN** the system responds 403 and changes no user

### Requirement: Deactivated users have no access

The system SHALL treat a deactivated user as unauthenticated for every purpose: login, token refresh, and all authenticated requests SHALL be refused with 403 `account deactivated`, including requests bearing a token issued before deactivation.

#### Scenario: Existing token stops working immediately

- **WHEN** a user is deactivated after already obtaining an access token, then calls any internal endpoint with that still-valid token
- **THEN** the system responds 403 and performs no data access

#### Scenario: Deactivated user cannot obtain new tokens

- **WHEN** a deactivated user submits correct login credentials or a valid refresh token
- **THEN** the system responds 403 and issues no token

#### Scenario: Deactivated session is cleared in the UI

- **WHEN** the UI receives a 403 whose detail is `account deactivated` on any request
- **THEN** it clears the stored access and refresh tokens and redirects to `/login` instead of leaving a stuck signed-in session; other 403 responses (for example staff hitting an admin-only route) do not clear the session

#### Scenario: Active users unaffected

- **WHEN** an active user logs in or calls an authenticated endpoint
- **THEN** behavior is unchanged from before this capability existed

### Requirement: Deactivation UI

The Staff page SHALL offer a deactivate icon action on each active user row except the signed-in admin, only when the signed-in user is an admin. The action SHALL require a confirmation dialog that names the exact user and states that access is revoked immediately, with a danger-styled confirm control; cancelling SHALL make no request. Deactivated rows SHALL display an `Inactive` state and SHALL NOT offer the action. The action SHALL remain usable at 390px width with no horizontal scrolling.

#### Scenario: Button is scoped correctly

- **WHEN** an admin views the user list
- **THEN** the deactivate button appears on other active users' rows and not on their own row or on inactive rows; a staff user sees no deactivate button

#### Scenario: Confirm and cancel

- **WHEN** an admin opens the confirmation for a named user
- **THEN** the dialog names that user and the consequence; Cancel closes it without a request, and confirm deactivates the user, shows a status message, and refreshes the list so the row becomes `Inactive`
