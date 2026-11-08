# Rag Answering Specification

## Purpose

Answers user questions with grounded, triaged responses that route or escalate when needed, stay scoped by row-level security, and use short-lived session memory for coherent follow-ups.

## Requirements

### Requirement: Decision-model triage of every non-audit internal question

On the internal path only, after authentication/authorization and after the `audit: ` prefix check, the system SHALL pass each remaining question through the configured Ollama decision model to produce a category, an escalation flag, and a department routing hint before retrieval/generation. Processing order SHALL be: authenticate → authorize (role + `account_id` membership) → `audit: ` prefix check → triage → RLS-scoped retrieval → generation.

#### Scenario: Routine question answered directly

- **WHEN** a user asks a routine FAQ-style question
- **THEN** triage returns a category with escalation false and the system proceeds to retrieval + generation

#### Scenario: Escalation flagged

- **WHEN** triage marks a question as needing escalation with a department
- **THEN** the answer includes the escalation notice and department, and the event is logged for audit

### Requirement: RLS-gated retrieval scoped to one resolved account plus internal

The system SHALL enforce PGSQL row-level security on every retrieval path using the single resolved `account_id`: results SHALL include only that account's documents plus `internal` documents; all other accounts' content SHALL be excluded. External FAQ callers are scoped to their own credential-bound account and SHALL NOT receive `internal` documents.

#### Scenario: Cross-account leak blocked

- **WHEN** a user scoped to account A queries a topic documented only under account B
- **THEN** the system answers without account B content (abstains or uses only allowed scope) and never exposes B's chunks

#### Scenario: Internal documents visible internally only

- **WHEN** an external FAQ caller queries a topic documented only in `internal` documents
- **THEN** the system withholds the `internal` content

### Requirement: Thirty-minute session memory bound to user and account

The system SHALL keep temporary per-session conversational context bound at creation to one `(user, account_id)` pair; sessions SHALL NOT be shared across users or accounts. `last_active` SHALL update only on an inbound user message and only after the TTL check for that message. A message arriving strictly more than 30 minutes after `last_active` SHALL be treated as a new session (old context wiped) and the answer SHALL include a notice that previous session context expired. The external FAQ API SHALL be stateless and offer no session memory.

#### Scenario: Follow-up uses context within window

- **WHEN** a user asks a follow-up within 30 minutes of their last message in the same session
- **THEN** the system uses the retained context in its answer

#### Scenario: Expired context disclosed

- **WHEN** a user sends a message more than 30 minutes after their last interaction in that session
- **THEN** the system answers without the old context and includes a notice that previous session context expired

#### Scenario: Session bound to its account

- **WHEN** a session created under account A receives a message scoped to account B
- **THEN** the system rejects it with 403 and does not merge or expose account A's context
