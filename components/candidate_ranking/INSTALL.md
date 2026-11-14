# Candidate Ranking: installation

This component reads vacancy responses and resumes through the HH API, analyzes
candidate evidence through the analysis services, and ranks the resulting
records. It contains a gateway, search, ranking, HH integration, analysis,
database, configuration and Streamlit frontend modules.

## Requirements

- Docker with the Compose plugin for the complete component stack.
- Python 3.11 or later for individual local services.
- Private provider credentials, an employer-authorized HH session and a configured database for connected operation.

The root repository's offline demo and tests run without these external accounts.
Full Docker and provider integration are separate deployment checks.

## Docker setup

```powershell
git clone https://github.com/Maxi-online/hr-intelligence-platform.git
cd hr-intelligence-platform/components/candidate_ranking
Copy-Item config/settings.example.yaml config/settings.yaml
Copy-Item .env.example .env
```

Populate the private runtime files using the exact variables in
[ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md). The example intentionally
contains no working customer account, tokens or proxy. Complete
[OAuth setup](OAUTH_SETUP.md) for the employer account you intend to use.

```powershell
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

Open the frontend at `http://localhost:8501` and the gateway schema at
`http://localhost:8088/docs`. Run these commands from the component directory;
the repository root is a collection of components rather than a single Compose stack.

## Local services

Create an isolated environment and install this component's declared dependencies.
Export the required private environment variables into every service process.

```powershell
py -3.11 -m venv .venv
& .venv/Scripts/python.exe -m pip install -r requirements.txt
```

Run each command below in a separate terminal with the same environment:

```powershell
& .venv/Scripts/python.exe gateway/main.py
& .venv/Scripts/python.exe search/main.py
& .venv/Scripts/python.exe ranking/main.py
& .venv/Scripts/python.exe hh_api/main.py
& .venv/Scripts/python.exe ai_analysis/main.py
& .venv/Scripts/python.exe -m streamlit run frontend/app.py --server.port=8501
```

Database and configuration dependencies still need to be reachable. Check the
YAML service addresses when switching between Docker DNS and local execution.

## Use and diagnose

Enter an accessible vacancy URL in the frontend and request the ranked responses.
The workflow retrieves responses, loads resumes, analyzes available evidence and
returns a ranked list. Inspect service logs when a stage fails:

```powershell
docker compose logs --tail=100 gateway hh_api ai_analysis
Invoke-RestMethod http://localhost:8088/health
```

For 401/403 responses, verify employer authorization and vacancy permissions.
For 429/503 responses, honor provider retry limits. For analysis failures,
check provider configuration and the analysis-service log. Do not log token values.

To update an existing installation, preserve private configuration, review the
incoming change, pull it, then run `docker compose up -d --build` again. Review
the repository's provenance and third-party notices for applicable rights.
