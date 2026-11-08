# Spec Delta

## Purpose

Establishes the deployable skeleton of the Synapse-RAG platform: containerized services, environment-driven configuration, and contributor guidelines so all later capabilities build on a consistent base.

## ADDED Requirements

### Requirement: Dockerized services excluding Ollama and PGSQL

The system SHALL ship a Docker Compose setup that containerizes API, UI, and worker services while Ollama and PGSQL run externally and are referenced via connection URLs.

#### Scenario: Compose up without bundled Ollama or PGSQL

- **WHEN** an operator runs `docker compose up --build` with a valid `.env`
- **THEN** API, UI, and worker containers start and connect to the external Ollama and PGSQL endpoints, and no `ollama` or `postgres` service is defined in the compose file

#### Scenario: Missing external dependency fails fast

- **WHEN** Ollama or PGSQL URLs are unreachable at startup
- **THEN** the API reports unhealthy with a log naming the unreachable dependency

### Requirement: .env-driven configuration

The system SHALL read all environment-specific settings (ports, URLs, secrets, model names, timeouts) from a `.env` file with documented defaults and fail fast on missing required secrets.

#### Scenario: Valid .env boots

- **WHEN** all required keys are present in `.env`
- **THEN** every service starts without code changes or hardcoded secrets

#### Scenario: Missing secret blocks boot

- **WHEN** a required secret (e.g. JWT secret) is absent
- **THEN** startup aborts with an error naming the missing key

### Requirement: AGENTS.md contributor guidelines

The repo SHALL include an `AGENTS.md` at root defining service layout, config conventions, code style, and quality gates (tests/checks before done).

#### Scenario: Guidelines present

- **WHEN** a contributor opens the repo
- **THEN** `AGENTS.md` describes where API, UI, worker, and config code live and how to run checks
