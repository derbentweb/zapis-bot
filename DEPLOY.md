# Как сделать бота доступным 24/7 (ноут можно выключать)

Бот уедет в облако Render — бесплатно, без карты. Домашний прокси там не нужен:
облако само видит Telegram.

## Быстрый путь — один скрипт

`deploy.ps1` сам создаст репозиторий, зальёт код, поднимет сервис Render и включит
пинг через GitHub Actions. Тебе остаётся только получить два ключа (без них никак —
нужны твоя почта и согласие с условиями сервисов):

1. **GitHub token:** github.com → аватар → Settings → Developer settings →
   Personal access tokens → **Tokens (classic)** → Generate new token →
   поставить галочку `repo` → сгенерировать и скопировать.
2. **Render token:** render.com → аватар → Account Settings → **API Keys** →
   Create API Key → скопировать.

Дальше:

```
copy deploy-keys.example.txt deploy-keys.txt
notepad deploy-keys.txt
```

Вставь два ключа, сохрани, затем:

```
powershell -ExecutionPolicy Bypass -File deploy.ps1
```

В конце скрипт напечатает адрес бота. Через 10–15 минут открой его — должно быть `OK`.

**Ниже — ручной путь, если скрипт не сработал.**

## 1. GitHub

1. Зарегистрируйся на github.com.
2. Создай новый репозиторий: кнопка **New repository** → имя `zapis-bot` → **Create repository**.
3. Залей файлы через веб: **Add file → Upload files**. Выбери всё из папки проекта,
   **кроме `.env`, `error.log`, `bot/bookings.json` и папки `__pycache__`.**
   Эти файлы содержат токен и данные клиентов — в интернет они попадать не должны.
4. **Commit changes**.

## 2. Render

1. Зайди на render.com → **Sign up with GitHub**.
2. **New → Web Service** → выбери репозиторий `zapis-bot` → **Connect**.
3. Настройки:
   - **Name:** любое, например `zapis-bot`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python bot/main.py`
   - **Instance Type:** Free
4. Ниже **Environment Variables** → **Add Environment Variable**, добавь две:
   - `BOT_TOKEN` = токен от @BotFather
   - `ADMIN_IDS` = твой ID от @userinfobot

   Файл `.env` на Render не нужен — он читает эти переменные напрямую.
5. **Create Web Service**. Дождись статуса **Live** (5–10 минут).
6. Открой выданный Render-адрес в браузере — должно быть просто `OK`.
   Напиши боту `/start` — он должен ответить.

## 3. Не дай Render уснуть

Бесплатный сервис засыпает после 15 минут без входящих запросов. Пингуем его:

1. Зарегистрируйся на cron-job.org.
2. **Add cronjob** → URL = адрес твоего Render-сервиса → интервал **каждые 10 минут** → включи.
3. Всё. Сервис не будет засыпать.

## Важное

- `bot/bookings.json` в облаке временный — при перезапуске очищается. Но каждая заявка
  **сразу приходит тебе в Telegram**, так что данные не теряются; `/bookings` показывает
  заявки с последнего перезапуска.
- После любого изменения кода: залей файлы на GitHub → Render сам перезапустит бота.
- Никогда не заливай `.env` на GitHub — в нём токен от твоего бота.
- Бесплатный лимит Render — 750 часов в месяц, а в месяц примерно 730. Впритык, но хватает.
