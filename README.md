# Podcast Generator

Pipeline automatica che trasforma newsletter in episodi podcast in **italiano**, pronti da ascoltare.

## Quick Start

```bash
git clone <url> && cd podcast-generator
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox
cp .env.example .env
# modifica .env con la tua GEMINI_API_KEY e la sorgente newsletter

# CLI
python main.py daily

# Web App
uvicorn podcast_generator.web.app:app --reload
```

## Documentazione

| Documento | Contenuto |
|---|---|
| `docs/library.md` | Usare come libreria Python (API completa, configurazione, esempi) |
| `docs/web-app.md` | Usare come web app (newsletter esempio, REST API, auth, deploy) |
| `ROADMAP.md` | Stato attuale e funzioni future |

## Architettura

```
Newsletter (Web / RSS / Email IMAP)
       │
       ▼
  ┌───────────┐
  │  Fetcher  │  Playwright / feedparser / IMAP → articoli
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │ Translator│  LLM (Gemini / OpenAI / Anthropic / Ollama)
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │    TTS    │  Edge-TTS (gratuito) o ElevenLabs
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │  Audio    │  pydub → verifica durata, aggiunge sigle, unisce file
  └───────────┘
```

## Installazione

### Da sorgente

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
playwright install firefox
cp .env.example .env
```

### Docker

```bash
docker build -t podcast-generator .
docker run -p 8000:8000 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/output:/app/output \
  podcast-generator
```

## Configurazione

### Multi-LLM

| Variabile | Default | Provider |
|---|---|---|
| `LLM_PROVIDER` | `gemini` | `gemini`, `openai`, `anthropic`, `ollama` |
| `GEMINI_API_KEY` | — | Google Gemini |
| `GEMINI_MODEL` | `gemini-2.0-flash` | Google Gemini |
| `OPENAI_API_KEY` | — | OpenAI |
| `OPENAI_MODEL` | `gpt-4o-mini` | OpenAI |
| `ANTHROPIC_API_KEY` | — | Anthropic |
| `ANTHROPIC_MODEL` | `claude-3-5-haiku-latest` | Anthropic |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama |
| `OLLAMA_MODEL` | `llama3` | Ollama |

### TTS

| Variabile | Default | Provider |
|---|---|---|
| `TTS_PROVIDER` | `edge` | `edge`, `elevenlabs` |
| `TTS_VOICE` | `it-IT-GiuseppeNeural` | Voci Edge-TTS italiane |
| `ELEVENLABS_API_KEY` | — | ElevenLabs |
| `ELEVENLABS_VOICE` | — | ElevenLabs voice ID |

### Newsletter / Scraping

| Variabile | Obbligatoria | Default |
|---|---|---|
| `NEWSLETTER_URL` | No* | — |
| `ARCHIVE_URL` | No* | `{NEWSLETTER_URL}/archive` |
| `LOAD_MORE_SELECTOR` | No | `button:has-text('Load More')...` |
| `LINK_PATTERN` | No | `/p/` |

\* Almeno uno tra `NEWSLETTER_URL` e `ARCHIVE_URL` deve essere impostato.

### Web App

| Variabile | Default | Ruolo |
|---|---|---|
| `WEB_PASSWORD` | — | Password per accesso Web UI |
| `API_TOKEN` | — | Token per autenticazione REST API |
| `WEB_PORT` | `8000` | Porta di ascolto |
| `WEB_HOST` | `0.0.0.0` | Indirizzo di ascolto |

### IMAP (Email)

| Variabile | Default | Ruolo |
|---|---|---|
| `IMAP_HOST` | — | Server IMAP (es. `imap.gmail.com`) |
| `IMAP_USER` | — | Indirizzo email |
| `IMAP_PASSWORD` | — | App password (Gmail) |
| `IMAP_FOLDER` | `INBOX` | Cartella IMAP o label Gmail |
| `IMAP_MAX_EMAILS` | `100` | Email massime per batch (1-1000) |

## Utilizzo

### CLI

```bash
python main.py daily                               # Episodio giornaliero
python main.py weekly                              # Compilation settimanale
python main.py weekly --days 14                    # Personalizza giorni
python main.py fetch-all                           # Backfill newsletter passate
python main.py fetch-all --limit 10                # Prime 10 nuove
python main.py status                              # Stato tracker
```

### Python Library

```python
import asyncio
from podcast_generator import PodcastGenerator, Settings

# Multi-LLM: cambia solo la variabile d'ambiente
cfg = Settings(llm_provider="openai", openai_api_key="sk-...")

gen = PodcastGenerator(cfg)

# Episodio giornaliero
episode = await gen.fetch_and_build_latest()

# Da URL specifici
articles = await gen.fetch_articles("https://newsletter.example.com")
episode = await gen.build_from_urls([articles[0].href])

print(f"Audio: {episode.audio_path}, Durata: {episode.duration_minutes} min")
```

### REST API

```bash
curl -X POST http://localhost:8000/api/v1/generate \
  -H "Authorization: Bearer $API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"urls": ["https://newsletter.example.com/p/article"]}'

# Risposta: {"job_id": "...", "status": "processing", "status_url": "..."}

curl http://localhost:8000/api/v1/status/{job_id} \
  -H "Authorization: Bearer $API_TOKEN"
```

Documentazione interattiva: http://localhost:8000/docs

### Web UI

```bash
uvicorn podcast_generator.web.app:app --reload
```

Apri http://localhost:8000.

**Sorgenti supportate:**
- **Web** — incolla URL newsletter (Beehiiv, Substack, etc.)
- **RSS** — feed RSS automatizzato
- **Email** — configura IMAP via Impostazioni per leggere newsletter via Gmail

Seleziona articoli, clicca **Genera Podcast**, attendi la generazione (polling HTMX), scarica l'MP3.

## Struttura del progetto

```
├── podcast_generator/          # Libreria Python
│   ├── config.py               # Pydantic Settings V2 (multi-LLM)
│   ├── models.py               # Pydantic models (Newsletter, Episode, ...)
│   ├── exceptions.py           # Errori custom
│   ├── fetcher.py              # Playwright scraping
│   ├── translator.py           # Multi-LLM (Gemini, OpenAI, Anthropic, Ollama)
│   ├── tts.py                  # Edge-TTS / ElevenLabs
│   ├── audio.py                # pydub utilities
│   ├── tracker.py              # JSON deduplicazione
│   ├── builder.py              # PodcastGenerator class (API pubblica)
│   ├── pipeline.py             # Rich progress CLI wrapper
│   └── web/
│       ├── app.py              # FastAPI (Web UI + REST API)
│       ├── auth.py             # Bearer token + cookie auth
│       ├── db.py               # sqlite3
│       └── templates/          # Jinja2 + HTMX + Tailwind
├── main.py                     # CLI entrypoint (Typer)
├── Dockerfile                  # Deploy containerizzato
├── pyproject.toml              # Metadati pacchetto
├── requirements.txt            # Dipendenze
├── .env.example                # Template configurazione
├── tests/
│   ├── test_core.py
│   └── test_web.py
└── docs/
    ├── library.md              # Documentazione libreria
    └── web-app.md              # Documentazione web app
```

## Automazione (cron)

```cron
# Ogni lunedì alle 8:00
0 8 * * 1 cd /home/utente/podcast-generator && .venv/bin/python3 main.py weekly >> cron.log 2>&1
```

## Stack

| Componente | Tecnologia | Costo |
|---|---|---|
| Scraping | Playwright (Firefox) | Gratuito |
| LLM | Gemini / OpenAI / Anthropic / Ollama | Gratuito (Gemini free tier) |
| TTS | Edge-TTS (Microsoft) | Gratuito, nessun limite |
| Audio | pydub + FFmpeg | Gratuito |
| CLI | Typer + Rich | Gratuito |
| Web | FastAPI + HTMX + Tailwind | Gratuito |
