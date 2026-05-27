# Roadmap

## v2.0 — Ristrutturazione completa (completata)

### Obiettivo
Trasformare il progetto in una **libreria Python installabile** con API pulita, multi-LLM, web app FastAPI e documentazione.

### Cosa è stato fatto

**Architettura a libreria**
- Nuovo pacchetto `podcast_generator/` installabile via `pip` o `pyproject.toml`
- Classe `PodcastGenerator` come interfaccia pubblica unica
- Separazione netta tra libreria core, CLI, web app

**Configurazione**
- Migrazione a **Pydantic Settings V2**
- Supporto multi-LLM: **Gemini**, **OpenAI**, **Anthropic**, **Ollama**
- Provider TTS: **Edge-TTS** (default, gratuito), **ElevenLabs**

**Web App**
- Riscritta in **FastAPI** con OpenAPI/Swagger docs
- **sqlite3** puro (leggero, zero dipendenze ORM)
- **REST API** completa con Bearer token auth
- **Web UI** protetta da password
- **RSS feed** per podcast player

**Bug fix**
- `get_article_list` passava `browser` invece di `context` (crash)
- Campi duplicati `intro_path`, `outro_path`, `use_web_search` in config
- Funzione `generate_audio` duplicata in `tts.py`
- Chiamate LLM sincrone in contesto async (ora tutte async)

**Documentazione**
- `docs/library.md` — uso come libreria con esempi
- `docs/web-app.md` — web app, newsletter esempio, REST API, deploy
- README aggiornato con Docker, multi-LLM, quick start

---

## Proposte per il futuro

### v3.0 — Qualità audio e produttività

| Funzione | Descrizione |
|---|---|
| **Multi-speaker** | Dialogo tra 2 voci (conduttore + ospite) invece di monologo |
| **Generazione batch** | Processare N newsletter in parallelo (asyncio.gather) |
| **Cache TTS** | Evitare rigenerare audio per script identici |
| **Supporto podcast lungo** | Suddividere episodi >60 min in parti |
| **Scheduling integrato** | Agenda interna (APScheduler) invece di cron esterno |

### v3.1 — Fonte contenuti

| Funzione | Descrizione |
|---|---|
| **YouTube → Podcast** | Estrarre trascrizione YouTube → LLM → TTS |
| **PDF/Articolo singolo** | Accettare URL diretto (non solo archive page) |
| **RSS feed input** |Subscribe a feed RSS come fonte automatica |
| **File upload** | Caricare PDF/TXT/DOCX per generazione podcast |

### v3.2 — Esperienza Web

| Funzione | Descrizione |
|---|---|
| **WebSocket progress** | Stato generazione in tempo reale (invece di polling HTMX) |
| **Preview script** | Mostrare e modificare lo script prima di generare audio |
| **Drag & drop articoli** | Riordinare playlist articoli nell'interfaccia |
| **Storico ricco** | Filtri, ricerca, statistiche di ascolto |
| **Temi chiari/scuri** | Tailwind dark mode |

### v3.3 — API & Integrazione

| Funzione | Descrizione |
|---|---|
| **Webhook callback** | Notifica POST a URL quando generazione completa |
| **API key management** | CRUD per API token via web UI |
| **Rate limiting** | Limite richieste per token/IP (Flask-Limiter pattern) |
| **OpenAPI client SDK** | Generare client Python/JS da spec OpenAPI |
| **GraphQL endpoint** | Alternativa a REST per query complesse |

### v4.0 — Produzione

| Funzione | Descrizione |
|---|---|
| **Multi-utente** | Autenticazione, profili, sorgenti multiple per utente |
| **PostgreSQL support** | Sostituire sqlite3 per deploy multi-utente |
| **Cloud storage** | Upload audio su S3/GCS con download presigned |
| **CDN delivery** | Distribuzione audio via CDN |
| **Monitoring** | Logging strutturato, metriche, alerting |
| **CI/CD** | GitHub Actions: test, lint, build Docker, deploy |

### Idee sperimentali

| Funzione | Descrizione |
|---|---|
| **AI Host Voice Cloning** | Clonare una voce reale (ElevenLabs voice lab) |
| **Summarization Layer** | Riepilogo automatico prima della traduzione per newsletter lunghe |
| **Multilingua** | Generare podcast in EN/FR/ES/DE oltre all'italiano |
| **NotebookLM-style** | Generare "discussion" tra due host invece di monologo |
| **Music background** | Aggiungere musica di sottofondo generata o librerie royalty-free |

---

## Contribuire

Le proposte sono ordinate per priorità percepita. Se vuoi contribuire:

1. Scegli una funzione dalla roadmap
2. Apri una issue per discuterla
3. Implementala con test
4. Apri PR

Ogni nuova funzione dovrebbe:
- Avere test (pytest)
- Essere documentata in `docs/`
- Seguire il pattern del progetto (async first, Pydantic models)
