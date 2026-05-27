# Podcast Generator — Web App

Web app per generare podcast da newsletter con interfaccia visuale e API REST.

## Avvio rapido

```bash
# Attiva ambiente virtuale
source .venv/bin/activate

# Avvia il server
uvicorn podcast_generator.web.app:app --reload

# Oppure con parametri custom
uvicorn podcast_generator.web.app:app --host 0.0.0.0 --port 8080 --reload
```

Apri http://localhost:8000

## Esempio: Newsletter Beehiiv

### 1. Configura `.env`

```env
GEMINI_API_KEY=AIza...
TTS_VOICE=it-IT-ElsaNeural

# Non serve configurare NEWSLETTER_URL qui —
# lo inserirai direttamente dalla web UI
```

### 2. Avvia il server

```bash
uvicorn podcast_generator.web.app:app --reload
```

### 3. Usa la Web UI

1. Apri http://localhost:8000
2. Incolla l'URL della newsletter:
   ```
   https://newsletter.theresanaiforthat.com
   ```
3. Clicca **"Analizza"**
4. Vedrai la lista degli articoli con checkbox
5. Seleziona uno o più articoli
6. Clicca **"Genera Podcast"**
7. Attendi la generazione (lo spinner HTMX mostra il progresso)
8. Scarica l'MP3 o ascolta dal player embedded

### 4. Usa la REST API

```bash
# 1. Ottieni la lista articoli
curl -X POST http://localhost:8000/api/v1/fetch-articles \
  -H "Content-Type: application/json" \
  -d '{"url": "https://newsletter.theresanaiforthat.com"}'

# 2. Avvia generazione
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://newsletter.theresanaiforthat.com/p/article-1"]}'
# → {"job_id": "abc123", "status": "processing", "status_url": "/api/v1/status/abc123"}

# 3. Controlla stato
curl http://localhost:8000/api/v1/status/abc123
# → {"job_id": "abc123", "status": "completed", "download_url": "/download/daily/...mp3", ...}

# 4. Scarica
curl -O http://localhost:8000/api/v1/episodes/1/audio
```

## Autenticazione

### Web UI (password)

Imposta nel `.env`:

```env
WEB_PASSWORD=mia-password-sicura
```

Riavvia il server. Ora http://localhost:8000 reindirizza a `/login`.
Inserisci la password per accedere. Il cookie `auth_token` scade dopo 7 giorni.

Per disabilitare la protezione, rimuovi `WEB_PASSWORD`.

### REST API (Bearer token)

Imposta nel `.env`:

```env
API_TOKEN=il-mio-token-api
```

Tutti gli endpoint `/api/v1/*` richiedono ora:

```bash
curl -H "Authorization: Bearer il-mio-token-api" http://localhost:8000/api/v1/episodes
```

Se `API_TOKEN` è vuoto (default), le API sono pubbliche.

## Endpoint API

### Web UI

| Metodo | Path | Descrizione |
|---|---|---|
| GET | `/` | Home page (form URL + cronologia) |
| POST | `/fetch-articles` | Estrai articoli da URL (HTMX) |
| POST | `/generate` | Avvia generazione (HTMX) |
| GET | `/check-status/{job_id}` | Polling stato generazione |
| GET | `/download/{folder}/{file}` | Download MP3 |
| GET | `/login` | Pagina login |
| POST | `/login` | Autenticazione |
| GET | `/logout` | Logout |
| GET | `/rss` | Feed RSS episodi |

### REST API (tutte `/api/v1/*`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| POST | `/api/v1/generate` | Bearer | Avvia generazione podcast |
| GET | `/api/v1/status/{job_id}` | Bearer | Stato generazione |
| GET | `/api/v1/episodes` | Bearer | Lista episodi (query: `?limit=20`) |
| GET | `/api/v1/episodes/{id}` | Bearer | Dettaglio episodio |
| GET | `/api/v1/episodes/{id}/audio` | Bearer | Download file MP3 |
| POST | `/api/v1/fetch-articles` | Bearer | Lista articoli da URL |

## Riferimento API dettagliato

### `POST /api/v1/generate`

Request:
```json
{
    "urls": ["https://example.com/p/articolo-1", "https://example.com/p/articolo-2"]
}
```

Response (202):
```json
{
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "status_url": "/api/v1/status/550e8400-e29b-41d4-a716-446655440000"
}
```

### `GET /api/v1/status/{job_id}`

Response:
```json
{
    "job_id": "550e8400-...",
    "status": "completed",
    "download_url": "/download/daily/2026-05-27_titolo_abc123.mp3",
    "title": "AI News",
    "filename": "2026-05-27_titolo_abc123.mp3"
}
```

Stati possibili: `pending`, `processing`, `completed`, `failed`.

### `GET /api/v1/episodes`

Response:
```json
[
    {
        "id": 1,
        "title": "AI News",
        "url": "https://example.com/p/articolo",
        "date": "2026-05-27",
        "audio_path": "/download/daily/2026-05-27_titolo.mp3",
        "script_path": "./output/daily/2026-05-27_titolo.txt",
        "created_at": "2026-05-27T10:00:00"
    }
]
```

### `POST /api/v1/fetch-articles`

Request:
```json
{
    "url": "https://newsletter.theresanaiforthat.com"
}
```

Response:
```json
{
    "articles": [
        {
            "href": "https://.../p/ai-framework-xyz",
            "text": "AI Framework XYZ 5.0",
            "description": "Nuovo framework AI..."
        }
    ]
}
```

## Swagger UI

FastAPI genera automaticamente documentazione interattiva:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## RSS Feed

`GET /rss` produce un feed RSS 2.0 compatibile con Apple Podcast, Spotify, e qualsiasi podcast player.

Puoi usare l'URL diretto:
```
http://localhost:8000/rss
```

Per esporlo pubblicamente, usa un reverse proxy (nginx, Caddy) o un servizio come ngrok.

## Deploy con Docker

```bash
# Build
docker build -t podcast-generator .

# Run
docker run -d \
  --name podcast-gen \
  -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/output:/app/output \
  podcast-generator
```

Con Docker Compose (`docker-compose.yml`):

```yaml
version: "3.8"
services:
  podcast-gen:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./.env:/app/.env
      - ./output:/app/output
    restart: unless-stopped
```

## Deploy con reverse proxy (nginx)

```nginx
server {
    listen 80;
    server_name podcast.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300s;
    }

    location /download/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        # File MP3 grandi, timeout lungo
        proxy_read_timeout 600s;
    }
}
```

## Consigli di sicurezza per produzione

1. **Imposta sempre `WEB_PASSWORD`** — protegge la web UI
2. **Imposta sempre `API_TOKEN`** — protegge le REST API
3. **Cambia `WEB_SECRET_KEY`** — usato per firmare i cookie
4. **Usa HTTPS** — behind nginx/Caddy/Traefik con Let's Encrypt
5. **Limita accesso** — firewall o VPN per l'interfaccia

## Architettura

```
┌──────────┐      ┌──────────────────────────────────────┐
│ Browser  │─────▶│  FastAPI /podcast_generator/web/      │
│ (HTMX)   │      │                                      │
└──────────┘      │  Web UI: /, /login, /fetch-articles  │
                  │  REST:   /api/v1/generate, /episodes  │
                  │  Files:  /download/{folder}/{file}    │
                  │  Feed:   /rss                         │
                  │                                      │
                  │  Background task → PodcastGenerator   │
                  │  (builder.py)                         │
                  └──────────────────┬───────────────────┘
                                     │
                            ┌────────▼────────┐
                            │   podcast.db     │
                            │   (SQLite)       │
                            └─────────────────┘
```

## API Status Codes

| Codice | Significato |
|---|---|
| 200 | OK |
| 202 | Generazione avviata (job_id restituito) |
| 302 | Redirect (non autenticato → /login) |
| 400 | Input mancante o invalido |
| 401 | Token mancante o non valido |
| 404 | Episodio/file non trovato |

## Note tecniche

- La generazione podcast avviene in **background** tramite `BackgroundTasks` di FastAPI
- I job sono in **memoria** (dict) — un restart del server cancella i job in corso
- I file MP3 generati sono **persistenti** in `output/`
- La cronologia episodi è in **SQLite** (`podcast.db`) — persistente tra restart
- Se vuoi supportare più job concorrenti, considera Redis/Celery
