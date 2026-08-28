# TeleShelf

TeleShelf indexes documents from Telegram forum topics and gives chat members a personal web reader. Reading progress is saved, so a document reopens at the last viewed page.

The project is a single Python application that runs both the Telegram bot and the FastAPI reader service. PostgreSQL stores the catalogue and persistent reading positions; Redis stores reader sessions and temporary state.

## Features

- indexes documents from Telegram forum topics;
- limits catalogue access to members of the source chat;
- paginated topic and file selection in the bot;
- streams PDFs directly from Telegram, with no separate file storage;
- saves reading progress in Redis and periodically persists it to PostgreSQL;
- Docker Compose deployment with automatic database migrations.

## Requirements

- Docker Engine and Docker Compose v2 (recommended);
- a public HTTPS domain that routes to port `8000` of the application;
- a local PDF.js distribution in `static/pdfjs` (it is not committed to Git; see below);
- a Telegram bot created with [@BotFather](https://t.me/BotFather);
- a Telegram application `api_id` and `api_hash` from [my.telegram.org](https://my.telegram.org/apps);
- a Telegram supergroup with forum topics enabled.

The bot must be made an administrator of the forum group. It needs access to message history and the member list when updating the collection.

## PDF.js

The web reader uses the static [Mozilla PDF.js 6.1.200](https://github.com/mozilla/pdf.js/releases/tag/v6.1.200) distribution. The `/static/pdfjs` directory is deliberately ignored by Git, so download it **before** building the Docker image or starting the application.

Download and unpack the distribution into `static/pdfjs`:

```bash
mkdir -p static/pdfjs
curl -fL -o /tmp/pdfjs-6.1.200-dist.zip \
  https://github.com/mozilla/pdf.js/releases/download/v6.1.200/pdfjs-6.1.200-dist.zip
unzip -q /tmp/pdfjs-6.1.200-dist.zip -d static/pdfjs
test -f static/pdfjs/web/viewer.html
```

The resulting directory must contain at least `static/pdfjs/web/viewer.html` and `static/pdfjs/build/`. FastAPI serves these assets at `/pdfjs`, and the client loads `/pdfjs/web/viewer.html` in an iframe.

The version is pinned to keep builds reproducible. When upgrading PDF.js, update this README and verify that a PDF opens correctly in Telegram Web Apps.

## Quick start with Docker

1. Copy the environment template and replace every placeholder secret. Set `POSTGRES_HOST=db` and `REDIS_HOST=redis` for containers.

   ```bash
   cp .env.example .env.docker
   ```

2. Set `API_DOMAIN` to the public reader URL, including the scheme, for example `https://reader.example.com/`. The bot sends this URL to users.
3. Install PDF.js as described above.
4. Build and start the services:

   ```bash
   docker compose --profile bot up -d --build
   ```

5. Check the services and application logs:

   ```bash
   docker compose --profile bot ps
   docker compose --profile bot logs -f app
   ```

Compose runs the one-off `migration` container before starting `app`. PostgreSQL and Redis data are kept in `postgres_debug/` and `redis_data/` at the repository root.

To stop the stack:

```bash
docker compose --profile bot down
```

An optional Adminer instance for database debugging can be started separately:

```bash
docker compose --profile dev up -d adminer
```

It is available at `http://localhost:8080`.

## Configuration

| Variable | Description | Default |
| --- | --- | --- |
| `BOT_TOKEN` | BotFather token for the Telegram bot | — |
| `TELEGRAM_API_ID` | Telegram application ID | `0` |
| `TELEGRAM_API_HASH` | Telegram application hash | — |
| `API_DOMAIN` | Public reader URL, including `https://` | — |
| `POSTGRES_HOST` | PostgreSQL host (`db` in Docker) | — |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | PostgreSQL database name | — |
| `POSTGRES_USER` | PostgreSQL user | — |
| `POSTGRES_PASSWORD` | PostgreSQL password | — |
| `POSTGRES_POOL_SIZE` | SQLAlchemy connection pool size | `10` |
| `POSTGRES_MAX_OVERFLOW` | Extra SQLAlchemy connections permitted | `20` |
| `REDIS_HOST` | Redis host (`redis` in Docker) | — |
| `REDIS_PORT` | Redis port | `6379` |
| `REDIS_DB` | Redis database number | `0` |
| `REDIS_SESSION_TTL` | Reader session TTL in seconds | `3600` |
| `REDIS_MAX_CONNECTIONS` | Redis connection limit | `10` |
| `FSM_DATA_TTL_SECONDS` | Bot FSM data lifetime | `1800` |
| `FSM_STATE_TTL_SECONDS` | Bot FSM state lifetime | `1800` |
| `TRANSFER_JOB_INTERVAL_MINUTES` | Interval for persisting positions from Redis | `2` |
| `TRANSFER_JOB_SCHEDULER_MAX_INSTANCES` | Maximum concurrent persistence jobs | `1` |
| `LOG_LEVEL` | Python logging level | — |
| `LOG_FORMAT` | Python logging format | — |

Never commit environment files or secrets. The local application reads `.env`; Docker Compose passes application settings from `.env.docker`.

## Local development

Start PostgreSQL and Redis by any preferred method, then create `.env` from the template and fill in the secrets. The template already uses `localhost` for the local database and Redis hosts.

```bash
cp .env.example .env
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000
```

The reader home page is available at `http://localhost:8000/`; FastAPI's interactive API documentation is available at `http://localhost:8000/docs`.

## Using the bot

1. Add PDF documents to one or more topics in the forum group.
2. Send `/update` in that group. The bot must be an administrator.
3. The bot reads messages from the beginning of the chat through the `/update` message, then updates topics, files, and group members.
4. A group member sends `/start` to the bot, selects a topic and document, and opens the reader link.

Run `/update` again whenever files or chat membership change. Send the command after all documents that must be included, otherwise newer messages will not be indexed.

## HTTP routes

| Route | Purpose |
| --- | --- |
| `GET /?session_id=…` | Reader page; add `mode=fullscreen` for fullscreen mode |
| `GET /api/pdf/{session_id}` | Streams a PDF document from Telegram |
| `POST /api/pdf/update_position/{session_id}` | Saves the page number; JSON body: `{"page": 12}` |

The bot creates reader sessions, which expire after `REDIS_SESSION_TTL`. Do not publish document links publicly.

## Database migrations

Migrations are in `database/migrations` and run automatically in Docker. To apply them manually:

```bash
alembic upgrade head
```
