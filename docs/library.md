# Podcast Generator — Libreria Python

## Installazione

```bash
pip install -r requirements.txt
# oppure, se pubblicato:
# pip install podcast-generator
```

Dipendenze opzionali per provider LLM:

```bash
pip install openai              # Provider OpenAI
pip install anthropic           # Provider Anthropic
# Ollama funziona via HTTP (httpx, già in requirements.txt)
```

## Configurazione

### Con file `.env`

Crea un `.env` nella directory di lavoro:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-key
NEWSLETTER_URL=https://example.com
```

Poi:

```python
from podcast_generator.config import Settings

cfg = Settings()  # Legge automaticamente da .env
cfg.validate()    # Verifica campi obbligatori
```

### Senza file `.env`

```python
cfg = Settings(
    llm_provider="openai",
    openai_api_key="sk-...",
    openai_model="gpt-4o",
    newsletter_url="https://newsletter.example.com",
)
```

### Tutte le opzioni di configurazione

```python
cfg = Settings(
    # ── LLM ──
    llm_provider="gemini",       # gemini | openai | anthropic | ollama
    gemini_api_key="...",
    gemini_model="gemini-2.0-flash",
    openai_api_key="...",
    openai_model="gpt-4o-mini",
    anthropic_api_key="...",
    anthropic_model="claude-3-5-haiku-latest",
    ollama_base_url="http://localhost:11434",
    ollama_model="llama3",

    # ── TTS ──
    tts_provider="edge",         # edge | elevenlabs
    tts_voice="it-IT-GiuseppeNeural",
    elevenlabs_api_key="...",
    elevenlabs_voice="...",

    # ── Sorgente ──
    source_name="My Newsletter",
    newsletter_url="https://newsletter.example.com",
    archive_url="https://newsletter.example.com/archive",

    # ── Scraping ──
    load_more_selector="button:has-text('Load More')",
    link_pattern="/p/",

    # ── Audio ──
    max_episode_minutes=60,
    output_dir=Path("./output"),
    use_web_search=False,
    intro_path=Path("./intro.mp3"),
    outro_path=Path("./outro.mp3"),
)
```

## API Pubblica — `PodcastGenerator`

La classe principale. Accetta una configurazione opzionale.

```python
from podcast_generator import PodcastGenerator, Settings

gen = PodcastGenerator()                          # Config da .env
gen = PodcastGenerator(Settings(...))             # Config personalizzata
```

### Fetching

#### `fetch_articles(url=None) -> list[ArticleSummary]`

Estrae la lista degli articoli da una pagina archive di newsletter.

```python
articles = await gen.fetch_articles("https://newsletter.example.com")
for a in articles:
    print(f"{a.text} — {a.href}")
# Output:
# AI Framework XYZ 5.0 — https://.../p/ai-framework-xyz
# OpenAI GPT-5 — https://.../p/openai-gpt5
```

### Generazione episodi

#### `fetch_and_build_latest() -> Episode`

Scarica l'ultima newsletter e genera l'episodio.

```python
ep = await gen.fetch_and_build_latest()
print(f"Audio: {ep.audio_path}")
print(f"Durata: {ep.duration_minutes} min")
print(f"Script salvato in: {ep.script_path}")
```

#### `build_daily(newsletter: Newsletter) -> Episode`

Genera un episodio da un oggetto Newsletter già ottenuto.

```python
nl = Newsletter(title="...", url="...", date=datetime.now(), content="...")
ep = await gen.build_daily(nl)
```

#### `build_from_urls(urls: list[str]) -> Episode`

Accetta una lista di URL di articoli. Se un solo URL → episodio giornaliero.
Se multipli → episodio settimanale (compilation).

```python
ep = await gen.build_from_urls([
    "https://example.com/p/article-1",
    "https://example.com/p/article-2",
])
```

#### `fetch_and_build_weekly(days=7) -> Episode`

Scarica le ultime N newsletter e le unisce in un episodio settimanale.

```python
ep = await gen.fetch_and_build_weekly(days=14)  # ultime 14
```

#### `build_weekly(newsletters: list[Newsletter]) -> Episode`

```python
newsletters = await gen.fetch_newsletters(...)
ep = await gen.build_weekly(newsletters)
```

#### `process_backlog(limit=None) -> dict`

Scarica **tutte** le newsletter non ancora processate e genera episodi.

```python
result = await gen.process_backlog(limit=10)
print(f"Generate: {len(result['daily'])} daily, {len(result['weekly'])} weekly")
```

## Multi-LLM: Configurazione per provider

### Gemini (default, gratuito)

```bash
LLM_PROVIDER=gemini
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.0-flash       # o gemini-1.5-flash, gemini-2.5-pro
```

```python
cfg = Settings(llm_provider="gemini", gemini_api_key="AIza...")
```

### OpenAI

```bash
pip install openai
```

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-...
OPENAI_MODEL=gpt-4o-mini            # o gpt-4o, gpt-4-turbo, gpt-3.5-turbo
```

### Anthropic

```bash
pip install anthropic
```

```env
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-haiku-latest   # o claude-3-opus, claude-3-sonnet
```

### Ollama (locale)

```bash
# Installa Ollama: https://ollama.com
ollama pull llama3
```

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
```

Nessuna API key necessaria, tutto in locale.

## TTS: Configurazione per provider

### Edge-TTS (default, gratuito)

Nessuna API key. Voci italiane disponibili:

```env
TTS_PROVIDER=edge
TTS_VOICE=it-IT-GiuseppeNeural    # Maschile (default)
# TTS_VOICE=it-IT-ElsaNeural      # Femminile
# TTS_VOICE=it-IT-DiegoNeural     # Maschile, giovane
# TTS_VOICE=it-IT-IsabellaNeural  # Femminile
```

### ElevenLabs

```bash
# Richiede API key (a pagamento)
ELEVENLABS_API_KEY=your-key
ELEVENLABS_VOICE=your-voice-id    # Dalla dashboard ElevenLabs
TTS_VOICE=it-IT-GiuseppeNeural   # Fallback se ElevenLabs non trova la voce
```

## Error Handling

```python
from podcast_generator.exceptions import (
    PodcastGeneratorError,
    ConfigError,
    FetchError,
    TranslationError,
    TTSError,
    AudioError,
    TrackerError,
    AuthError,
    NotFoundError,
)

try:
    episode = await gen.fetch_and_build_latest()
except FetchError as e:
    print(f"Errore nello scraping: {e}")
except TranslationError as e:
    print(f"Errore LLM: {e}")
except TTSError as e:
    print(f"Errore TTS: {e}")
except ConfigError as e:
    print(f"Configurazione mancante: {e}")
```

## Modelli

### `Newsletter`

```python
from podcast_generator import Newsletter

nl = Newsletter(
    title="AI News",                          # str
    url="https://.../p/article",              # str
    date=datetime.now(),                      # datetime
    content="Contenuto dell'articolo...",     # str
)
```

### `Episode`

```python
ep = Episode(
    audio_path=Path("./output/daily/...mp3"), # Path
    script_path=Path("./output/daily/...txt"),# Path
    script="Ciao a tutti...",                 # str
    date_str="2026-05-27",                    # str
    title="AI News",                          # str
    url="https://...",                        # str
    duration_minutes=15.3,                    # float | None
)
```

### `ArticleSummary`

```python
summary = ArticleSummary(
    href="https://.../p/article",             # str
    text="AI Framework XYZ 5.0",              # str (titolo)
    description="Nuovo framework...",         # str (descrizione breve)
)
```

### `GenerationJob`

Usato internamente dalla web app per tracciare lo stato delle generazioni asincrone.

```python
job = GenerationJob(
    job_id="uuid",                            # str
    status=JobStatus.PROCESSING,              # JobStatus enum
    download_url="/download/daily/...mp3",    # str | None
    title="AI News",                          # str | None
    filename="...mp3",                        # str | None
    error=None,                               # str | None
)
```

## Esempi completi

### Episodio giornaliero automatico

```python
import asyncio
from podcast_generator import PodcastGenerator

async def main():
    gen = PodcastGenerator()
    ep = await gen.fetch_and_build_latest()
    print(f"Episodio creato: {ep.audio_path} ({ep.duration_minutes:.1f} min)")

asyncio.run(main())
```

### Selezione articoli e generazione

```python
import asyncio
from podcast_generator import PodcastGenerator

async def main():
    gen = PodcastGenerator()

    # 1. Carica la lista articoli
    articles = await gen.fetch_articles("https://newsletter.example.com")

    # 2. Prendi i primi 3
    urls = [a.href for a in articles[:3]]

    # 3. Genera (se 1 → daily, se >1 → weekly compilation)
    ep = await gen.build_from_urls(urls)
    print(f"Podcast pronto: {ep.audio_path}")

asyncio.run(main())
```

### Con OpenAI

```python
import asyncio
from podcast_generator import PodcastGenerator, Settings

async def main():
    cfg = Settings(
        llm_provider="openai",
        openai_api_key="sk-...",
        openai_model="gpt-4o",
        newsletter_url="https://newsletter.example.com",
    )
    gen = PodcastGenerator(cfg)
    ep = await gen.fetch_and_build_latest()
    print(f"Fatto! {ep.audio_path}")

asyncio.run(main())
```

### Con Ollama (locale)

```python
cfg = Settings(
    llm_provider="ollama",
    ollama_base_url="http://localhost:11434",
    ollama_model="llama3",
    newsletter_url="https://newsletter.example.com",
)
```

## Integrazione in altri progetti

### Come sottoprocesso

```python
import subprocess, json

result = subprocess.run(
    ["python", "main.py", "daily"],
    cwd="/path/to/podcast-generator",
    capture_output=True, text=True,
)
print(result.stdout)
```

### Come modulo importato

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path("/path/to/podcast-generator")))

from podcast_generator import PodcastGenerator

gen = PodcastGenerator()
```

### Come pacchetto installato

```bash
cd podcast-generator
pip install -e .                # Installazione in sviluppo
# Oppure, dopo aver pubblicato su PyPI:
# pip install podcast-generator
```

Poi da qualsiasi progetto:

```python
from podcast_generator import PodcastGenerator
```
