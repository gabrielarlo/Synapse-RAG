# Spec Delta

## Purpose

Provides a reusable input component and a consistent input visual language across all UI pages, with the Chat composer input as the source of truth.

## ADDED Requirements

### Requirement: Consistent input visual language

The system SHALL render text, number, password and search inputs with the Chat input tokens: slate-200 border, rounded-full pill shape, `px-4 py-2.5` padding, indigo focus border, and slate disabled background/foreground.

#### Scenario: Form input matches Chat pill

- **WHEN** a user views the Login form or Audit filters
- **THEN** each input is pill-shaped with the Chat border, focus, and disabled styling instead of the old `rounded-lg` style

#### Scenario: Selects use consistent tokens

- **WHEN** a user views a select (Staff role, Documents account, Chat scope)
- **THEN** the select uses the same border, focus, and disabled tokens as inputs while preserving compact layout (Chat scope selects keep `px-3 py-1.5 text-xs`) and current options

#### Scenario: Layout extras preserved

- **WHEN** a search input needs room for an icon or button (Chat history search, `pr-8`)
- **THEN** the reusable component preserves the extra padding and alignment instead of forcing `px-4 py-2.5` uniformly

### Requirement: Reusable input component API

The system SHALL provide a reusable input component supporting two-way binding, `text`/`number`/`password`/`search` types, placeholder, required, disabled, autocomplete, and accessibility attributes such as `aria-label`.

#### Scenario: Login username binding

- **WHEN** a user types a username in the reusable component
- **THEN** the bound model updates and submit uses the typed value

#### Scenario: Number coercion preserved

- **WHEN** a user types a numeric limit in the Audit filter
- **THEN** the value is coerced to a number (`typeof filters.limit === 'number'`) with min/width layout preserved

#### Scenario: Accessibility preserved

- **WHEN** a user navigates a form input by keyboard or screen reader
- **THEN** the `aria-label`, `required`, and focus states work as before

### Requirement: Chat composer behavior preserved

The system SHALL keep the Chat composer message input functional with Enter-to-send, Shift+Enter newline, `rows="1"`, and loading/disabled states.

#### Scenario: Enter sends message

- **WHEN** a user presses Enter in the Chat composer
- **THEN** the message sends and Shift+Enter inserts a newline instead

### Requirement: Out of scope controls untouched

Checkboxes (`accent-indigo-600`) and file inputs (`file:mr-2 file:px-3 ...` styling) SHALL remain native and SHALL NOT be replaced by the reusable input component.

#### Scenario: Checkbox remains native

- **WHEN** a user views the internal-mode checkbox in Documents or Chat
- **THEN** the checkbox keeps its native accent styling and not a pill text input

#### Scenario: File input remains native

- **WHEN** a user views the file upload or replace inputs in Documents
- **THEN** the inputs keep their `file:` button styling and change handlers
