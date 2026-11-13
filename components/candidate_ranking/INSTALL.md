# CandidateRanking — Установка и запуск

## Описание
CandidateRanking — микросервисная система: по ссылке вакансии hh.ru получает отклики, резюме, делает мульти‑агентный AI‑анализ и строит ТОП кандидатов.

## Требования
- Docker + Docker Compose (рекомендуется)
- Python 3.11+ (для локального запуска без Docker)
- 4GB+ RAM

## Быстрый запуск (Docker)
```bash
git clone <repository-url>
cd CandidateRanking
cp config/settings.yaml.template config/settings.yaml
# заполните ключи в settings.yaml

docker-compose up -d --build
```
Доступ:
- Frontend: http://localhost:8501
- Gateway: http://localhost:8088/docs

## Локальный запуск (необязательно)
```bash
pip install -r requirements.txt
# в отдельных терминалах/процессах
python gateway/main.py
python search/main.py
python ranking/main.py
python hh_api/main.py
python ai_analysis/main.py
streamlit run frontend/app.py --server.port=8501
```

## Структура
```
CandidateRanking/
  frontend/  gateway/  search/  ranking/  hh_api/  ai_analysis/  database/  config/  shared/
```

## Конфигурация
- Файл: `config/settings.yaml` (YAML‑only)
- Ключи:
  - `ai_analysis.openai_api_key`
  - `hh_api.client_id`, `hh_api.client_secret`, `hh_api.user_tokens`

## Использование
- Введите ссылку на вакансию на главной странице фронтенда
- Нажмите «Построить ТОП по откликам»
- Сервис загрузит отклики → резюме → выполнит AI анализ → покажет отсортированный список

## Диагностика
```bash
# Логи всех сервисов
docker-compose logs -f
# Здоровье gateway
curl http://localhost:8088/health
```

## Частые проблемы
- 401/403 при откликах — проверьте OAuth работодателя и права
- 429/503 hh.ru — подождите окно лимитов; уменьшите параллелизм/частоту
- 500 AI — проверьте ключ OpenAI и логи `ai_analysis`

## Обновление
```bash
docker-compose down
git pull
docker-compose up -d --build
```

Лицензия: MIT