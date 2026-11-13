# 🔐 Настройка OAuth для CandidateRanking

## Что нужно для работы системы

CandidateRanking требует **OAuth токены HH API** для доступа к откликам на ваши вакансии и **OpenAI API ключ** для AI-анализа.

## 📋 Пошаговая настройка HH API

### 1. Создание приложения на hh.ru

1. Зайдите на https://dev.hh.ru/admin
2. Создайте новое приложение:
   - **Название**: CandidateRanking
   - **Описание**: Система анализа откликов на вакансии
   - **Redirect URI**: `http://localhost:8088/oauth/callback`
3. Сохраните **Client ID** и **Client Secret**

### 2. Получение токенов

1. Откройте URL авторизации:
   ```
   https://hh.ru/oauth/authorize?response_type=code&client_id=ВАШ_CLIENT_ID&redirect_uri=http://localhost:8088/oauth/callback
   ```
2. Авторизуйтесь как **работодатель** (не соискатель!)
3. Разрешите доступ к данным
4. Из URL перенаправления скопируйте `code=...`
5. Обменяйте код на токен:
   ```bash
   curl -X POST https://hh.ru/oauth/token \
     -d "grant_type=authorization_code" \
     -d "client_id=ВАШ_CLIENT_ID" \
     -d "client_secret=ВАШ_CLIENT_SECRET" \
     -d "code=ПОЛУЧЕННЫЙ_КОД" \
     -d "redirect_uri=http://localhost:8088/oauth/callback"
   ```

### 3. Настройка конфигурации

Отредактируйте `config/settings.yaml`:

```yaml
hh_api:
  client_id: "ВАШ_CLIENT_ID"
  client_secret: "ВАШ_CLIENT_SECRET"
  user_agent: "CandidateRanking/1.0 (ваш_email@domain.com)"
  user_tokens:
    access_token: "ПОЛУЧЕННЫЙ_ACCESS_TOKEN"
    refresh_token: "ПОЛУЧЕННЫЙ_REFRESH_TOKEN"

ai_analysis:
  openai_api_key: "sk-ВАШ_OPENAI_КЛЮЧ"
```

## 🤖 Получение OpenAI API ключа

1. Зайдите на https://platform.openai.com/api-keys
2. Создайте новый API ключ
3. Добавьте его в конфигурацию

## 🚀 Запуск системы

```bash
# Пересобрать и запустить
docker-compose down --remove-orphans
docker-compose up -d --build

# Проверить статус
docker-compose ps
```

## ⚠️ Важные ограничения

- **Только ваши вакансии**: Система может получить отклики только на вакансии, размещенные с вашего работодательского аккаунта
- **Права работодателя**: Токен должен быть получен от аккаунта с правами работодателя
- **Лимиты API**: HH.ru ограничивает количество запросов в минуту

## 🔍 Проверка работы

1. Откройте http://localhost:8501
2. Вставьте ссылку на ВАШУ вакансию (размещенную с этого аккаунта)
3. Нажмите "Построить ТОП по откликам"

## 🐛 Решение проблем

- **401 Ошибка авторизации**: Проверьте токены в конфигурации
- **403 Доступ запрещен**: Убедитесь, что вакансия принадлежит вам
- **404 Не найдено**: Вакансия не существует или недоступна
- **429 Лимит превышен**: Подождите перед следующим запросом
