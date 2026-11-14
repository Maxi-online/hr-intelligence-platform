# Candidate Ranking: configuration and environment variables

The component reads `config/settings.yaml`. The tracked starting point is
`config/settings.example.yaml`; the populated file is private and ignored by Git.
`${NAME}` references are resolved against the process environment by
`shared/utils.py`. A missing required reference raises a configuration error.
An arbitrary Python command does not automatically load a `.env` file.

## Required settings

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` | Provider authentication for the analysis service |
| `HH_API_CLIENT_ID` | Registered HH application identifier |
| `HH_API_CLIENT_SECRET` | HH application secret |
| `HH_API_USER_AGENT` | Application identity accepted by the HH API |
| `HH_API_USER_TOKENS_ACCESS_TOKEN` | Employer-authorized access token |
| `HH_API_USER_TOKENS_REFRESH_TOKEN` | Refresh token for that employer session |
| `CLICKHOUSE_USERNAME` | Database account |
| `CLICKHOUSE_PASSWORD` | Database password |
| `SERVICES_AI_ANALYSIS_HOST` | Service host for local execution; use `localhost` locally |

Use the exact names in the example configuration and `.env.example`. Historical
guides used shorter `HH_CLIENT_*` aliases; those are not the references in the
current example. Other component entrypoints can expose additional variables.

## Docker Compose

Create a private `.env` from `.env.example`, populate the variables needed by the
selected component, and copy the example YAML to `config/settings.yaml`.
Compose reads `.env` for interpolation and passes configured `environment:`
entries into containers. `DOCKER_ENV=true` selects Docker service addresses.

```powershell
Copy-Item .env.example .env
Copy-Item config/settings.example.yaml config/settings.yaml
docker compose config --quiet
```

The first two commands initialize private files. Do not overwrite an existing
deployment configuration without preserving its values. The example proxy is
disabled and contains no inherited server, username or password.

## Local execution

Export required values into each service process from a private secret store.
Streamlit can also use `STREAMLIT_SERVER_PORT=8501` and
`STREAMLIT_SERVER_ADDRESS=127.0.0.1`. Optional proxy settings are configured only
when the operator explicitly enables the corresponding YAML section.

## Handling credentials

Do not commit populated YAML, `.env`, OAuth responses or access-token logs. Use
private runtime configuration and deployment secrets. The public examples are
configuration schemas, not preconfigured provider accounts. A token's expiry
must come from its own OAuth response rather than a historical timestamp.
