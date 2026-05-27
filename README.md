# Podcast Generator

Pipeline automatica che trasforma newsletter in episodi podcast in **italiano**, pronti da ascoltare.

La sorgente delle news è completamente configurabile via `.env`: puoi usare qualsiasi newsletter ospitata su **Beehiiv** (o adattare lo scraper ad altre piattaforme modificando i selettori CSS).

## Architettura

```
Newsletter (sorgente configurabile)
       │
       ▼
  ┌───────────┐
  │  Fetcher  │  Playwright → estrae titolo + contenuto dalla pagina archive
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │ Translator│  Google Gemini → traduce e riscrive in italiano come script podcast
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │    TTS    │  Edge-TTS (Microsoft) → genera audio MP3 con voci neurali italiane
  └─────┬─────┘
        │
        ▼
  ┌───────────┐
  │  Audio    │  pydub → verifica durata, aggiunge sigle, unisce file
  └───────────┘
```

Il progetto è strutturato su tre livelli:

1. **Servizi** (`src/fetcher.py`, `translator.py`, `tts.py`, `audio.py`, `tracker.py`) — moduli puri, ognuno con una sola responsabilità
2. **Builder** (`src/builder.py`) — layer async che orchesta i servizi, senza dipendenze CLI. Importabile da web app o altri frontend
3. **Pipeline CLI** (`src/pipeline.py` + `main.py`) — thin wrapper con progress bar Rich, chiama il builder

## Requisiti

- Python 3.10+
- [Playwright browsers](https://playwright.dev/python/docs/installation) (`playwright install firefox`)
- Chiave API **Google Gemini** ([AI Studio](https://aistudio.google.com/)) — gratuita, generosissima
- **Edge-TTS** non richiede chiave API (gratuito, nessun limite di token)

## Installazione

```bash
# Clona il repository
git clone <url> && cd podcast-generator

# Crea ambiente virtuale
python3 -m venv .venv && source .venv/bin/activate

# Installa dipendenze
pip install -r requirements.txt

# Installa il browser Playwright (Firefox)
playwright install firefox

# Configura le API key
cp .env.example .env
# modifica .env con la tua GEMINI_API_KEY e la sorgente newsletter
```

### File `.env`

```
# === API ===
GEMINI_API_KEY=your_gemini_api_key_here
# TTS non richiede API key: viene usato Edge-TTS (gratuito)

# === Sorgente newsletter (almeno NEWSLETTER_URL o ARCHIVE_URL) ===
SOURCE_NAME=There's An AI For That
NEWSLETTER_URL=https://newsletter.theresanaiforthat.com
# ARCHIVE_URL=https://newsletter.theresanaiforthat.com/archive

# === Selettori scraping (default Beehiiv) ===
LOAD_MORE_SELECTOR=button:has-text('Load More'), a:has-text('Load More')
LINK_PATTERN=/p/

# === Opzionali ===
TTS_VOICE=it-IT-GiuseppeNeural  # voci italiane: it-IT-GiuseppeNeural (maschile), it-IT-ElsaNeural (femminile)
GEMINI_MODEL=gemini-3.5-flash
MAX_EPISODE_MINUTES=60
OUTPUT_DIR=./output
```

### Configurazione della sorgente

| Variabile | Obbligatoria | Default | Descrizione |
|-----------|:---:|:-------:|-------------|
| `SOURCE_NAME` | No | `newsletter` | Nome visualizzato della fonte |
| `NEWSLETTER_URL` | No* | — | URL base della newsletter |
| `ARCHIVE_URL` | No* | `{NEWSLETTER_URL}/archive` | URL completo della pagina archive |
| `LOAD_MORE_SELECTOR` | No | `button:has-text('Load More'), a:has-text('Load More')` | Selettore CSS per il pulsante "Load More" |
| `LINK_PATTERN` | No | `/p/` | Pattern URL per filtrare i link ai singoli post |

\* Almeno uno tra `NEWSLETTER_URL` e `ARCHIVE_URL` deve essere impostato.

> **Nota:** Lo scraper è ottimizzato per **Beehiiv**. Per altre piattaforme, modifica `LOAD_MORE_SELECTOR` e `LINK_PATTERN`.

## Utilizzo

```bash
# Episodio giornaliero: ultima newsletter → traduzione → audio
python3 main.py daily

# Episodio settimanale: aggrega N newsletter in una compilation
python3 main.py weekly                    # ultime 7
python3 main.py weekly --days 14          # personalizza

# BACKFILL: scarica TUTTE le newsletter passate non ancora processate
python3 main.py fetch-all
python3 main.py fetch-all --limit 10      # prime 10 nuove

# Verifica lo stato del tracker
python3 main.py status
```

## Struttura del progetto

```
├── main.py                  # CLI (Typer) — entrypoint, chiama asyncio.run()
├── src/
│   ├── __init__.py          # Esporta classi e funzioni principali
│   ├── config.py            # Config dataclass, validazione, .env
│   ├── models.py            # Dataclass condivisi (Newsletter, Episode)
│   ├── fetcher.py           # Scraping della newsletter con Playwright
│   ├── translator.py        # Traduzione/riscrittura con Gemini
│   ├── tts.py               # Text-to-Speech con Edge-TTS (Microsoft)
│   ├── audio.py             # Utilità audio (durata, intro/outro, merge)
│   ├── tracker.py           # Tracker JSON per evitare duplicati
│   ├── builder.py           # Async orchestration layer (no CLI deps)
│   └── pipeline.py          # Thin wrapper CLI con Rich progress bar
├── output/
│   ├── daily/               # Puntate giornaliere (MP3 + script TXT)
│   │   ├── 2026-01-15_titolo.mp3
│   │   └── ...
│   ├── weekly/              # Compilation settimanali
│   │   ├── 2026-W03.mp3
│   │   └── ...
│   └── .processed.json      # Tracker (non modificare manualmente)
├── .env
├── .env.example
├── requirements.txt
└── README.md
```

## Dettaglio moduli

### `src/models.py`
Dataclass condivise (`Newsletter`, `Episode`) usate da tutti i moduli.

### `src/fetcher.py`
Usa **Playwright** (Firefox headless) per navigare la pagina archive, estrarre link e contenuto testuale.

### `src/translator.py`
Invia il testo a **Google Gemini** con system prompt per riscrittura in stile podcast italiano.

### `src/tts.py`
Usa **Edge-TTS** (voci neurali Microsoft, gratuite, nessun limite). Voci italiane: `it-IT-GiuseppeNeural` (maschile), `it-IT-ElsaNeural` (femminile).

### `src/builder.py`
Layer async che combina i servizi in operazioni complete. **Senza dipendenze CLI/Typer/Rich** — utilizzabile direttamente da una web app:

```python
from src.config import Config
from src.builder import fetch_and_build_latest

cfg = Config()
episode = await fetch_and_build_latest(cfg)
print(episode.audio_path)  # → output/daily/2026-01-15_titolo.mp3
```

### `src/pipeline.py`
Thin orchestrator CLI: aggiunge progress bar Rich attorno alle funzioni del builder. Tutte le funzioni sono async.

### `src/tracker.py`
Persiste lo stato di elaborazione in `output/.processed.json` per evitare duplicati.

## Voci Edge-TTS

| Voce | Gender | Qualità |
|------|--------|---------|
| `it-IT-GiuseppeNeural` (default) | Maschile | Eccellente per news/podcast |
| `it-IT-ElsaNeural` | Femminile | Naturale e fluida |

## Modelli Gemini

| Modello | Costo |
|---------|-------|
| `gemini-3.5-flash` (default) | Gratuito (free tier) |
| `gemini-3.1-flash-lite` | Gratuito |
| `gemini-2.5-flash` | Gratuito |

## Automazione (cron)

```cron
# Ogni lunedì alle 8:00
0 8 * * 1 cd /home/utente/podcast-generator && .venv/bin/python3 main.py weekly >> cron.log 2>&1
```

## Stack

| Componente | Tecnologia | Costo |
|------------|-----------|-------|
| Scraping | Playwright (Firefox) | Gratuito |
| LLM | Google Gemini | Gratuito |
| TTS | Edge-TTS (Microsoft) | Gratuito, nessun limite |
| Audio | pydub + FFmpeg | Gratuito |
| CLI | Typer + Rich | Gratuito |
