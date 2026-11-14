# Candidate analysis: configuration and interpretation

The component has two analysis paths: per-skill analysis and a multi-agent
assessment. Results are stored for reuse and can contribute to ranking.
These are model-generated assessments of supplied resume evidence; the repository
does not establish predictive hiring accuracy or validate the scores against
employee performance.

## Configure the provider

Start with `config/settings.example.yaml` and `.env.example`. Put populated
values only in ignored runtime configuration or a secret store. The example
uses `OPENAI_API_KEY` and currently selects `gpt-5-nano`; the agent YAML also
defines model and completion-token settings. Inspect the actual configuration
used by the chosen entrypoint rather than relying on an old fixed-model label.

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) and
[INSTALL.md](INSTALL.md) for propagation into Compose and local processes.
The repository does not bundle provider access or a working API key.

## Configuration surfaces

| Location | Responsibility |
| --- | --- |
| `config/settings.example.yaml` → private `config/settings.yaml` | Provider, service, database, cache and ranking settings |
| `ai_analysis/agent_configs.yaml` | Agent weights, thresholds, coordinator and monitoring configuration |
| `ai_analysis/agent_prompts.yaml` | Role rubrics, examples, JSON output requirements and language |
| `ai_analysis/agents.py` | Request execution, retries and agent result handling |
| `ai_analysis/master_coordinator.py` | Coordination and aggregation |

The public example disables proxy inheritance. Configure a proxy explicitly only
if your deployment needs one. Agent prompts request English output, and template
field names such as `candidate_data_json` and `position_requirements_json` remain
unchanged. Display labels do not determine agent configuration keys.

## Assessment paths

The per-skill path evaluates supplied skills against a search query and experience
description. Its result includes relevance, proficiency level, experience years
when supported, and a confidence estimate. The multi-agent path separates
requirements, resume presentation, technical skills, proficiency, experience,
formatting and anomaly checks before coordinator aggregation.

| Skill result field | Meaning |
| --- | --- |
| `skill_name` | Skill being assessed |
| `relevance_score` | Model's relevance assessment on the configured scale |
| `proficiency_level` | Reported proficiency category |
| `years_experience` | Evidence-supported experience estimate when available |
| `ai_confidence` | Model-reported confidence; not a calibrated probability |
| `analysis_timestamp` | Assessment time |

An analysis response also includes `candidate_id`, `skill_analysis`,
`overall_score`, `analysis_summary` and `processing_time`. The detailed response
can expose keyword relevance, filter match, recency and completeness components.
Do not confuse the per-skill 0–1 relevance scale with agents whose rubrics use
0–100 scores. Inspect the response model and coordinator before aggregating them.

## Ranking

The public ranking example assigns weights of 0.4 to keyword relevance, 0.3 to
filter match, 0.2 to recency and 0.1 to profile completeness. Those are editable
example settings, not measured optimal weights. Multi-agent coordinator weights
are configured separately. The presence of an analysis result does not prove
that every entrypoint uses the same ranking formula.

## Check the running service

These read-only probes require a running local deployment:

```powershell
Invoke-RestMethod http://localhost:8005/health
Invoke-RestMethod http://localhost:8005/config
Invoke-RestMethod http://localhost:8005/multi-agent/health
Invoke-RestMethod http://localhost:8005/multi-agent/agents
```

The following synthetic request invokes the configured provider if run. It is
an integration probe, not a credential-free test or a benchmark result:

```powershell
$body = @{
    candidate_id = 'synthetic-integration-probe'
    search_query = 'Python backend developer'
    skills = @('Python', 'Django', 'PostgreSQL')
    experience_description = 'Synthetic example: five years of backend development.'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://localhost:8005/analyze' -ContentType 'application/json' -Body $body
```

Available analysis routes include `/analyze`, `/analyze/batch`,
`/multi-agent/analyze` and `/multi-agent/batch`. Use each endpoint's actual schema;
the multi-agent route accepts structured candidate and position data.

## Persistence and monitoring

The workflow retrieves candidate data, checks stored records, analyzes eligible
new records, persists results and ranks candidates. Database statistics include
candidate count, analysis coverage, average scores and stored skill counts.
Inspect the frontend statistics panel and service logs for the deployed version.
Processing time in a sample response is not a latency benchmark.

```powershell
docker compose logs --tail=100 ai_analysis
```

## Troubleshooting and cost control

- Missing provider configuration: check that the variable exists in the analysis
  process; do not print its value. A populated `.env` alone is not a Python environment.
- Rate limiting: reduce request concurrency and honor provider retry guidance;
  increasing a timeout alone does not increase an account's rate limit.
- Model access errors: check the configured model and the account's access to it.
- Invalid output: inspect parsing/schema errors and the matching agent prompt.
- Cache or database errors: verify the selected database adapter and cache settings.

Reuse stored analyses when appropriate, cap completion length and record actual
token usage. Batch endpoints do not by themselves imply a discounted provider
batch API. No historical token price or per-candidate cost is asserted here;
consult the [provider's current pricing](https://openai.com/api/pricing/).

Possible follow-up work includes provider adapters, stronger resume extraction,
empirical score calibration, ATS integration and explicit evaluation datasets.
Those are development directions, not completed capabilities.
