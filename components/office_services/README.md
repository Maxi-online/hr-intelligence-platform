# Shared Office Agent Services

Shared infrastructure for agent configuration, orchestration, model requests, memory and history. The three subprojects have independent requirements and Docker Compose files:

- [Central database](central_database/README.md): schema, configuration/state storage and initialization utilities.
- [Supervisor service](supervisor_service/README.md): message entry point, agent coordination, status and statistics.
- [Unified LLM service](unified_llm_service/README.md): database-backed agent configuration, context construction and model-request handling.

`central_database/init_database.py`, `supervisor_service/config.py` and `unified_llm_service/config.py` expose the main configuration boundaries. The runtime services use PostgreSQL; the database directory also retains a separate MySQL-oriented schema/reference. These dialects must not be treated as interchangeable initialization scripts.

Use the local configuration examples and environment-variable names. Filled settings, credentials, real conversations and user records remain outside Git. Initialization and migrations are explicit operator actions against a dedicated demonstration database; they are not started by the root offline suite.

Validate a synthetic workflow by checking stored status, observed tool invocation, error propagation and confirmed handoff. A text response or registry entry alone is not proof that an external tool ran. The complete cross-component deployment, permissions and persistence/replay behavior need integration testing.

The root [README](../../README.md) explains the other recruitment components and the exact offline validation boundary. Each subproject's README lists its API and deployment entry points.
