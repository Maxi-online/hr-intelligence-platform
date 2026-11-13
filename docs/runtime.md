# Runtime and configuration

Use separate virtual environments or containers for the component requirements. Recruitment and candidate-ranking components have their own Docker Compose files. Office services have separate Compose configurations under central_database, supervisor_service and unified_llm_service. Coordinator modules import as `master_agent` with `PYTHONPATH=components`. A root-level unified production Compose deployment is not asserted.

Use the component navigation and validation boundaries in the root [README](../README.md). Runtime services and external providers are not started by the offline replay.
