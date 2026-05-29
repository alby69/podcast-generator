# Podcast Generator — Web App

Web app per generare podcast da newsletter con interfaccia visuale e API REST.

> [!WARNING]
> **Versione 3.0 (In Sviluppo):** L'interfaccia web attuale interagisce con un database SQLite locale. Stiamo migrando verso una UI decentralizzata che interroga i relay **Nostr** e recupera audio da **IPFS**.

## Avvio rapido

```bash
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
2. Scegli la sorgente:
   - **Web**: incolla URL newsletter (es. `https://newsletter.theresanaiforthat.com`) e clicca **Analizza**
   - **Email**: vai su **Impostazioni**, configura IMAP (host, utente, password, cartella), torna alla home e clicca **Analizza**
3. Vedrai la lista degli articoli con checkbox
4. Seleziona uno o più articoli
5. Clicca **"Genera Podcast"**
6. Attendi la generazione (polling HTMX mostra il progresso)
7. Scarica l'MP3 o ascolta dal player embedded

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

### OAuth (Google / GitHub)

Il metodo consigliato. Crea un OAuth Client ID in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
o [GitHub Settings](https://github.com/settings/developers) e imposta nel `.env`:

```env
OAUTH_GOOGLE_CLIENT_ID=xxx.apps.googleusercontent.com
OAUTH_GOOGLE_CLIENT_SECRET=GOCSPX-...
# OAUTH_GITHUB_CLIENT_ID=xxx
# OAUTH_GITHUB_CLIENT_SECRET=xxx
JWT_SECRET=una-chiave-casuale-di-almeno-32-caratteri
```

**URI di callback da registrare:** `http://localhost:8000/auth/callback`

### Password condivisa (fallback)

Se non configuri OAuth, puoi usare una password singola:

```env
WEB_PASSWORD=mia-password-sicura
```

La pagina di login mostrerà il form password. Il cookie `session` scade dopo 7 giorni.

### Modalità sviluppo

Se non configuri né OAuth né `WEB_PASSWORD`, l'accesso è libero (utile in sviluppo).

### REST API (Bearer token)

```env
API_TOKEN=il-mio-token-api
```

Tutti gli endpoint `/api/v1/*` richiedono ora:

```bash
curl -H "Authorization: Bearer il-mio-token-api" http://localhost:8000/api/v1/episodes
```

Se `API_TOKEN` è vuoto (default), le API sono pubbliche.

### Riepilogo variabili auth

| Variabile | Default | Ruolo |
|---|---|---|
| `OAUTH_GOOGLE_CLIENT_ID` | — | Client ID Google OAuth |
| `OAUTH_GOOGLE_CLIENT_SECRET` | — | Client Secret Google OAuth |
| `OAUTH_GITHUB_CLIENT_ID` | — | Client ID GitHub OAuth |
| `OAUTH_GITHUB_CLIENT_SECRET` | — | Client Secret GitHub OAuth |
| `JWT_SECRET` | `change-me` | Chiave HMAC per firma JWT sessioni |
| `WEB_PASSWORD` | — | Password fallback Web UI |
| `API_TOKEN` | — | Token REST API (vuoto = pubblico) |

## Endpoint API

### Web UI

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| GET | `/` | Sessione | Home page |
| GET | `/login` | — | Pagina login (OAuth + password) |
| POST | `/login` | — | Login con password |
| GET | `/logout` | — | Logout |
| GET | `/auth/google` | — | Redirect Google OAuth |
| GET | `/auth/github` | — | Redirect GitHub OAuth |
| GET | `/auth/callback` | — | Callback OAuth |
| POST | `/fetch-articles` | Sessione | Estrai articoli da URL/email |
| POST | `/fetch-more-emails` | Sessione | Carica più email IMAP |
| POST | `/article` | Sessione | Dettaglio articolo |
| POST | `/generate` | Sessione | Avvia generazione podcast |
| GET | `/check-status/{job_id}` | Sessione | Polling stato generazione |
| GET | `/settings` | Sessione | Pagina impostazioni |
| POST | `/save-settings` | Sessione | Salva impostazioni |
| GET | `/imap-folders` | Sessione | Elenca cartelle IMAP |
| POST | `/imap-debug` | Sessione | Debug label Gmail |
| GET | `/download/{folder}/{file}` | Pubblico | Download MP3 |
| GET | `/rss` | Pubblico | Feed RSS episodi |

### REST API (tutte `/api/v1/*`)

| Metodo | Path | Auth | Descrizione |
|---|---|---|---|
| POST | `/api/v1/generate` | Bearer | Avvia generazione podcast |
| GET | `/api/v1/status/{job_id}` | Bearer | Stato generazione |
| GET | `/api/v1/episodes` | Bearer | Lista episodi (`?limit=20`) |
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

Con Docker Compose:

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
        proxy_read_timeout 600s;
    }
}
```

## Sorgente Email (IMAP)

Configurabile dalla pagina **Impostazioni** (`/settings`) o via `.env`.

### Gmail

Per usare Gmail serve una **App Password**:

1. Attiva la [verifica in due passaggi](https://myaccount.google.com/security)
2. Genera una [App Password](https://myaccount.google.com/apppasswords) per "Posta"
3. Inserisci i dati:
   - **Host**: `imap.gmail.com`
   - **Utente**: `tua.email@gmail.com`
   - **Password**: la App Password generata
   - **Cartella**: `INBOX` o una label Gmail (es. `Newsletter/TAAFT`)

### IMAP via Web UI

1. Vai su **Impostazioni** (in alto a destra)
2. Compila i campi IMAP
3. Clicca **"Elenca cartelle disponibili"** per esplorare le label
4. Seleziona una cartella e salva
5. Torna alla home e clicca **"Analizza"**

### Comportamento

- **100 email** per batch (configurabile 1-1000 via `IMAP_MAX_EMAILS`)
- Pulsante **"Carica più email"** carica il batch successivo
- Soggetti decodificati RFC 2047
- Vista dettaglio con contenuto HTML della newsletter

## Consigli di sicurezza per produzione

1. **Configura OAuth** (Google/GitHub) invece di `WEB_PASSWORD`
2. **Cambia `JWT_SECRET`** con una chiave casuale (almeno 32 caratteri)
3. **Imposta `API_TOKEN`** per proteggere le REST API
4. **Usa HTTPS** behind nginx/Caddy/Traefik con Let's Encrypt
5. **Usa `--reload` solo in sviluppo** — in produzione avvia senza

## Architettura

```
┌──────────┐      ┌──────────────────────────────────────────┐
│ Browser  │─────▶│  FastAPI /podcast_generator/web/          │
│ (HTMX)   │      │                                          │
└──────────┘      │  Web UI: /, /settings, /fetch-articles   │
                  │  Auth:   /auth/google, /auth/callback     │
                  │  REST:   /api/v1/generate, /episodes      │
                  │  Files:  /download/{folder}/{file}        │
                  │  Feed:   /rss                             │
                  │  IMAP:   /fetch-more-emails, /imap-folders│
                  │                                          │
                  │  Background task → PodcastGenerator       │
                  │  (builder.py)                             │
                  └──────────────────┬───────────────────────┘
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
| 302 | Redirect (non autenticato → `/login`) |
| 303 | Redirect post-login / post-logout |
| 400 | Input mancante o invalido |
| 401 | Token/password non valido |
| 404 | Episodio/file non trovato |

## Note tecniche

- La generazione podcast avviene in **background** tramite `asyncio.create_task`
- I job sono in **memoria** (dict) — un restart del server cancella i job in corso
- Le email via IMAP supportano **Gmail X-GM-LABELS**
- 5 strategie di fallback per risoluzione UID email
- Soggetti email decodificati RFC 2047
- File MP3 generati **persistenti** in `output/`
- Cronologia episodi in **SQLite** (`podcast.db`) — persistente tra restart
- Le sessioni utente usano **JWT firmato** (cookie `session`, 7 giorni)
- Il callback OAuth scambia il codice manualmente con `httpx` (affidabile anche con `--reload`)
