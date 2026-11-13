# CandidateRanking — Переменные окружения

CandidateRanking использует YAML‑конфигурацию (`config/settings.yaml`) как источник правды. Переменные окружения можно применять для локальной разработки и CI/CD, но они не обязательны.

## Базовые переменные
```bash
# Режим запуска (используется для определения адресов сервисов)
DOCKER_ENV=true            # для запуска в Docker Compose
```

## OpenAI (опционально)
Если не хотите хранить ключ в YAML (`ai_analysis.openai_api_key`), задайте его через окружение контейнера `ai_analysis`.
```bash
OPENAI_API_KEY=sk-your-openai-api-key
```

## HH.ru OAuth (работодатель)
Рекомендуется хранить в `config/settings.yaml` (секция `hh_api`), но для CI/CD допустим экспорт через окружение и последующая запись в YAML.
```bash
HH_CLIENT_ID=your_hh_client_id
HH_CLIENT_SECRET=your_hh_client_secret
# При наличии пользовательских токенов:
HH_ACCESS_TOKEN=...
HH_REFRESH_TOKEN=...
```

## Streamlit (опционально)
```bash
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
```

## Прокси (опционально)
Используйте только при необходимости. Не храните реальные креды в репозитории.
```bash
PROXY_HOST=
PROXY_PORT=
PROXY_USERNAME=
PROXY_PASSWORD=
PROXY_PROTOCOL=http
```

## Примечания безопасности
- Не коммитьте реальные ключи/пароли. Используйте секреты CI/CD или локальные `.env.local` (в `.gitignore`).
- В проде храните секреты в секрет‑менеджере, а не в YAML.
- Внутри Docker Compose переменные передаются через `environment:` соответствующего сервиса.