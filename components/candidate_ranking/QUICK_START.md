# Candidate Ranking: quickstart

For a credential-free introduction, use the [root README](../../README.md) and
offline demo. The steps below start the connected candidate-ranking component;
they require your own employer authorization and provider/database configuration.

## Prepare and start

Run from `components/candidate_ranking` in an existing checkout:

```powershell
Copy-Item config/settings.example.yaml config/settings.yaml
Copy-Item .env.example .env
```

Populate the private values described in [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md)
and [OAUTH_SETUP.md](OAUTH_SETUP.md). Initialize these files only once so an
existing deployment's values are not overwritten.

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Open `http://localhost:8501`. Use a vacancy belonging to, or accessible to, the
authorized employer account. The frontend retrieves responses, loads resumes,
invokes analysis, and presents ranked candidates. Open
`http://localhost:8088/docs` for the gateway's current request schema.

## Gateway request

This operator-driven example asks for a real vacancy URL instead of embedding
a fabricated customer vacancy ID:

```powershell
$vacancyUrl = Read-Host 'Vacancy URL accessible to the authorized employer'
$requestBody = @{ vacancy_url = $vacancyUrl; limit = 10 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8088/vacancy/top' -ContentType 'application/json' -Body $requestBody
```

## Service addresses

| Service | Port |
| --- | --- |
| Frontend | 8501 |
| Gateway | 8088 |
| Search | 8001 |
| Ranking | 8002 |
| HH API adapter | 8003 |
| Analysis | 8005 |
| ClickHouse HTTP / native | 8123 / 9000 |

Employer response retrieval uses employer negotiations and requires the account's
permissions. On 401/403, review the OAuth session; on 429, wait for the provider's
rate-limit window. Analysis settings reference `OPENAI_API_KEY`; the multi-agent
batch endpoint is `/multi-agent/batch` on the analysis service.

See [INSTALL.md](INSTALL.md) for local services, logs and update procedures.
