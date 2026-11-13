# Unified LLM Service

Loads agent configuration and memory, builds request context, invokes the configured model adapter and records the interaction. Agent/tool descriptions are configuration; successful real tool invocation must be verified separately.

## Architecture

The implementation uses FastAPI, PostgreSQL, a configured model provider and HTTP integration helpers. `config.py` loads local settings; `app.py` defines the HTTP application. Shared tables include agent configuration, deployed-agent registry, operational/core memory and chat history. Database content and credentials are not part of the source release.

## Configuration and startup

From the repository root, run `python scripts/prepare_config.py` to create missing configuration files without overwriting existing settings. Review the service's example JSON and environment names, then supply your own values locally.

From this service directory, validate and optionally start its Compose deployment:

```bash
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

For a separate Python development environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python app.py
```

On Windows use `./.venv/Scripts/python.exe`. The configured HTTP port is 8102; the primary application endpoint is `POST /generate_response`. A running HTTP server does not verify provider access, database schema compatibility or tool permissions.

## Diagnostics

```bash
curl --fail http://localhost:8102/health
docker compose logs --tail=100
```

Use synthetic requests and a dedicated demonstration database. Check whether an error originated in settings resolution, database access, model invocation or a downstream service. Logs must not include credentials or raw private conversations.

## Integration contract

Agent configurations, prompts, model settings and memory are read through the service's persistence boundary. Sample agent IDs are fixtures rather than identities of actual employees. Adding a database configuration does not establish that its tools are implemented or permitted. Validate request schemas, persisted state, retry behavior and the observed result of any tool call.

Historical response-time, concurrency and memory figures are not treated as measured benchmarks. Measure them under a documented workload and provider configuration. The repository's root offline checks do not start this service or assess generated responses.

## Declared HTTP routes

| Source | Method | Declared route | Handler |
| --- | --- | --- | --- |
| `app.py` | GET | `/` | `root` |
| `app.py` | GET | `/health` | `health_check` |
| `app.py` | POST | `/generate_response` | `generate_response` |
| `app.py` | GET | `/agent_status/{agent_id}` | `get_agent_status` |
| `app.py` | GET | `/available_agents` | `get_available_agents` |
