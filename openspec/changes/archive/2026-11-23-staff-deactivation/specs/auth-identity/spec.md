# Spec Delta

## Purpose

Adds a deactivated user state that immediately revokes all access and an admin-only action to set it, without deleting the user or their assignments.

## ADDED Requirements

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
