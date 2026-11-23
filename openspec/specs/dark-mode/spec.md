# dark-mode Specification

## Purpose
Provides a persisted user theme preference with light, dark and system modes for the Synapse-RAG UI. System mode follows OS changes live; the chosen mode paints on the first frame without a flash and keeps every page readable in all themes.

## Requirements

### Requirement: User theme toggle

The system SHALL provide an accessible toggle that cycles the UI through `light`, `dark` and `system` modes. The current mode SHALL be exposed via `aria-label`, `title` and `data-theme` on `<html>`; `aria-pressed` SHALL NOT be used because the control is not binary.

#### Scenario: Toggle cycles through all three modes

- **WHEN** a user activates the theme toggle in the app header or on the login card three times
- **THEN** the mode changes light → dark → system → light, `data-theme` reflects the mode, the icon changes (sun / moon / monitor), and the computed background changes to the mode's theme (with system resolved against the OS preference)

#### Scenario: Toggle is reachable on mobile

- **WHEN** the viewport is 390×844
- **THEN** the toggle is at least 44×44 CSS pixels, is not squeezed by the header title, and the document has no horizontal scrolling (`scrollWidth === clientWidth`)

### Requirement: Theme persistence

The system SHALL persist the selected mode (`light`/`dark`/`system`) in `localStorage` under `theme` and SHALL restore the exact mode on the next visit — not just the effective dark class. Unset or invalid values default to `system`.

#### Scenario: Choice survives reload

- **WHEN** a user switches to system and reloads the application
- **THEN** `document.documentElement.dataset.theme === 'system'` and the toggle shows the monitor icon with a system label

#### Scenario: First visit follows the OS preference

- **WHEN** no valid stored theme exists and the OS prefers dark
- **THEN** the application renders in dark mode on first paint

### Requirement: System preference following

In `system` mode the system SHALL follow OS `prefers-color-scheme` changes live without a reload. In `light` and `dark` modes the system SHALL ignore OS preference changes.

#### Scenario: OS switches while in system mode

- **WHEN** the OS preference changes from dark to light (or vice versa) while the stored mode is `system`
- **THEN** `.dark`, `colorScheme` and the computed background update immediately with no reload

#### Scenario: Explicit choice is stable across OS changes

- **WHEN** the OS preference changes while the stored mode is `dark` or `light`
- **THEN** the rendered theme does not change

### Requirement: No flash of the wrong theme

The system SHALL apply the stored or default mode to `<html>` synchronously during HTML parsing, before any stylesheet or application script paints.

#### Scenario: Dark theme paints on first frame

- **WHEN** a user with stored `theme = 'dark'` loads any page
- **THEN** `document.documentElement.classList.contains('dark')` is true and `document.documentElement.style.colorScheme === 'dark'` before the application mounts, and the first painted body background is the dark token

#### Scenario: System mode paints on first frame

- **WHEN** a user with stored `theme = 'system'` loads any page while the OS prefers dark
- **THEN** the first painted body background is the dark token, `data-theme === 'system'`, and the inline bootstrap and the mounted toggle compute the same effective dark

#### Scenario: Native controls follow the theme

- **WHEN** dark mode is active (explicitly or via system)
- **THEN** native `<dialog>` backdrops, scrollbars and form controls render with dark `color-scheme` rather than light defaults

### Requirement: Readable contrast in both themes

The system SHALL provide dark companions for all light surfaces, text, borders, focus indicators and status badges so that content remains legible in both themes.

#### Scenario: Surfaces and text adapt

- **WHEN** dark mode is active (explicitly or via system) on any page (Login, Chat, Documents, Accounts, Staff, Audit)
- **THEN** cards, tables, inputs and dialogs use dark surfaces, primary text uses `dark:text-slate-100/200/300`, and no light pastel badge background is left with dark text

#### Scenario: Layout and behavior unchanged

- **WHEN** a user switches themes
- **THEN** every `v-model` binding, filter, dialog, Enter-to-send handler, `aria-*` attribute, and the mobile card/table split continue to work exactly as before
