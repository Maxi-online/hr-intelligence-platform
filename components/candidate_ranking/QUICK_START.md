# 🚀 Быстрый старт — CandidateRanking

CandidateRanking строит ТОП кандидатов по ссылке на вакансию hh.ru: загружает отклики, тянет резюме, делает мульти‑агентный AI‑анализ и ранжирует.

## 1) Подготовка
```bash
cp config/settings.yaml.template config/settings.yaml
# Вставьте ключи в config/settings.yaml:
# - ai_analysis.openai_api_key
# - hh_api.client_id / client_secret (OAuth работодателя)
# - hh_api.user_tokens.access_token / refresh_token (если уже есть)
```

## 2) Запуск (Docker Compose)
```bash
docker-compose up -d --build
```

## 3) Проверка
- Frontend: http://localhost:8501
- Gateway API: http://localhost:8088/docs

## 4) Получить ТОП по вакансии
1. Откройте Frontend
2. Вставьте ссылку вида `https://hh.ru/vacancy/<id>`
3. Нажмите «Построить ТОП по откликам»

Альтернатива через API (через gateway):
```bash
curl -X POST http://localhost:8088/vacancy/top \
  -H 'Content-Type: application/json' \
  -d '{"vacancy_url":"https://hh.ru/vacancy/123456789","limit":10}'
```

## Состав сервисов и порты
- frontend: 8501
- gateway: 8088
- search: 8001
- ranking: 8002
- hh_api: 8003
- ai_analysis: 8005
- clickhouse: 8123 (http), 9000 (native)

## Тонкости HH.ru
- Для списка откликов используются «переговоры работодателя» (`/employer_negotiations`), требуется OAuth работодателя и права.
- При 401/403 — проверьте `client_id/client_secret` и выдачу прав в кабинете.
- При 429 — срабатывают повторы с задержкой, подождите окно лимитов.

## Тонкости AI
- Ключ OpenAI берётся из `config/settings.yaml` (или `OPENAI_API_KEY`).
- Анализ идёт батчем через `/multi-agent/batch`.

## Обновление
```bash
docker-compose down && git pull && docker-compose up -d --build
```