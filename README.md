# Our Wishlist — Telegram Bot + Mini App

## Развёртывание на Bothost (GitHub → Bothost)

Проект рассчитан на **один сервис Bothost с Custom Dockerfile**: внутри контейнера запускаются Telegram polling-бот, FastAPI API и собранный React Mini App. Mini App и API используют один HTTPS-домен. SQLite хранится в постоянной директории `/app/data`.

1. Залей содержимое репозитория в GitHub (ветка `main`).
2. В Bothost создай Telegram-бота и подключи GitHub-репозиторий.
3. В настройках сборки выбери **Custom Dockerfile** (файл `Dockerfile` в корне репозитория).
4. Укажи порт сервиса **3000**. Приложение читает переменную Bothost `PORT`.
5. В настройках переменных окружения добавь:
   - `BOT_TOKEN` — токен из @BotFather (если Bothost не подставил его автоматически);
   - `BOT_USERNAME` — username бота без `@`;
   - `WEBAPP_URL` — HTTPS-домен сервиса Bothost, без `/` в конце;
   - `PUBLIC_BASE_URL` — тот же HTTPS-домен;
   - `TELEGRAM_OWNER_IDS=8580512680,1973334354`;
   - `DATABASE_PATH=/app/data/wishlist.sqlite3`;
   - `APP_SECRET` — длинная случайная строка.
6. Убедись, что у сервиса включён домен/HTTPS. Дождись сборки и проверь `https://ТВОЙ-ДОМЕН/health` — ожидается `{"status":"ok"}`.
7. В @BotFather открой `/mybots` → выбери бота → **Bot Settings → Menu Button** и укажи `WEBAPP_URL`. Текст кнопки, например, «Открыть вишлист».
8. Проверь `/start` и персональные ссылки `https://t.me/USERNAME?start=8580512680` и `https://t.me/USERNAME?start=1973334354`.

**Важно:** не коммить `.env`, токен бота, SQLite-файл или резервные копии. Bothost хранит постоянные данные в `/app/data`; не меняй `DATABASE_PATH` на папку с исходниками. Если панель не предлагает Custom Dockerfile, проверь доступность этой функции для выбранного типа сервиса в документации/поддержке Bothost.



Полноценный стартовый проект: Telegram-бот на aiogram 3, FastAPI backend, SQLite и React Mini App.

## Возможности

- Публичный просмотр вишлистов по `https://t.me/ВАШ_БОТ?start=8580512680` и `...?start=1973334354`.
- Обычный `/start` не показывает меню и просит открыть персональную ссылку.
- Два режима просмотра: все желания и категории.
- Владельцы могут управлять только собственными списками.
- Добавление и редактирование в Mini App.
- Массовое добавление сообщением боту: одна строка на желание, поля разделяются `|`.
- Создание и удаление пользовательских категорий.
- Удаление всех своих желаний с подтверждением.
- Секретное бронирование: другие посетители видят отметку «Забронировано», владелец — нет.
- SQLite, WAL-режим и скрипт резервного копирования.

## Стек

- Python 3.12+
- aiogram 3
- FastAPI + Uvicorn
- SQLite
- React + TypeScript + Vite

## 1. Создать Telegram-бота

1. Открой `@BotFather` в Telegram и выполни `/newbot`.
2. Сохрани токен. Не публикуй его и не добавляй в Git.
3. В `.env` укажи `BOT_TOKEN`, `BOT_USERNAME` (без `@`) и публичный HTTPS URL Mini App.
4. Для Mini App настрой домен через BotFather (`/setdomain`, если доступно для твоего типа запуска/настроек).
5. Mini App должен открываться по HTTPS. В примере ниже API и фронтенд публикуются одним доменом через reverse proxy.

## 2. Настроить сервер

Нужны Docker и Docker Compose (рекомендуется) либо Python 3.12+ и Node.js 20+.

```bash
cp .env.example .env
nano .env
```

Заполни как минимум:
- `BOT_TOKEN`
- `BOT_USERNAME`
- `WEBAPP_URL`, например `https://wishlist.example.com`
- `PUBLIC_BASE_URL`, тот же публичный URL
- `TELEGRAM_OWNER_IDS=8580512680,1973334354`
- `INIT_DATA_MAX_AGE=86400`

**Важно:** установи длинный случайный `APP_SECRET` (например, `openssl rand -hex 32`). Он используется для служебных задач и не должен попадать в клиентский код.

## 3. Запуск через Docker Compose

```bash
docker compose up --build -d
docker compose logs -f
```

Сервис API будет слушать порт `8000` внутри контейнера. Mini App соберётся отдельно и будет доступен на `4173` внутри compose-сети. Пример reverse proxy для домена находится в `deploy/nginx.conf`.

Если хочешь использовать существующий Nginx на хосте, направь:
- `/api/` → `http://127.0.0.1:8000/api/`
- `/health` → `http://127.0.0.1:8000/health`
- `/` → frontend на `http://127.0.0.1:4173`

После настройки проверь `https://wishlist.example.com/health`.

## 4. Запуск без Docker (для разработки)

Терминал 1 — backend и бот запускаются раздельно:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Терминал 2:

```bash
source .venv/bin/activate
python -m bot.main
```

Терминал 3 — Mini App:

```bash
cd miniapp
npm install
npm run dev -- --host 0.0.0.0
```

Для локального браузера Mini App можно использовать демо-режим только для визуальной разработки, но серверные операции должны проверяться настоящим Telegram `initData`. Не включай демо-авторизацию на публичном сервере.

## 5. Формат массового добавления

Напиши боту `/add`, выбери свой список и отправь строки:

```text
Наушники Sony | Техника | 29990 | https://shop.example/headphones | Чёрные
Худи оверсайз | Одежда | 6500 | https://shop.example/hoodie | Размер L
Набор кофе | Еда и напитки
Книга | Книги
```

Порядок полей:
`Название | Категория | Цена | Ссылка | Описание`

Можно указывать только название или первые два поля. Ссылки и цены необязательны. Пустые поля допустимы. Перед массовой записью бот показывает предварительный просмотр и просит подтвердить импорт. В текущей версии строки сохраняются как отдельные желания.

## 6. API (кратко)

Публичные GET:
- `GET /api/owners`
- `GET /api/wishlist/{owner_id}?mode=all`
- `GET /api/categories/{owner_id}`
- `GET /health`

Запросы изменения требуют заголовок `X-Telegram-Init-Data` с исходным `window.Telegram.WebApp.initData`:
- `POST /api/items`
- `PATCH /api/items/{item_id}`
- `DELETE /api/items/{item_id}`
- `DELETE /api/wishlist/{owner_id}`
- `POST /api/categories`
- `DELETE /api/categories/{category_id}`
- `POST /api/items/{item_id}/reserve`
- `DELETE /api/items/{item_id}/reserve`

Не передавай `initDataUnsafe` как доказательство авторизации. Сервер проверяет криптографическую подпись `initData`.

## 7. Резервные копии

```bash
python scripts/backup.py
```

Создаёт timestamped копию SQLite-файла в `backups/`. Настрой cron/systemd timer для регулярного запуска, например раз в день. Храни копии отдельно от сервера.

## Важные замечания

- Это рабочая базовая версия, но перед публичным запуском протестируй HTTPS, домен, резервные копии и Telegram WebApp.
- SQLite хорошо подходит для небольшого проекта с двумя владельцами. При высокой нагрузке можно мигрировать на PostgreSQL.
- Удаление желания владельцем удаляет также связанные бронирования.
- В текущем варианте секретное бронирование скрывает статус от владельца. Не добавляй владельцу API-эндпоинт с деталями брони, иначе сюрприз будет раскрыт.