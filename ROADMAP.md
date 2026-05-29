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

**Nuove sorgenti**
- Supporto **RSS feed** come input (feedparser)
- Supporto **Email IMAP** (Gmail con App Password)
  - `list_imap_folders()` per esplorare label/folder
  - X-GM-LABELS per etichette Gmail personalizzate
  - 5 strategie di fallback per risoluzione UID
  - Decodifica RFC 2047 per soggetti email
  - Paginazione con offset/limit (max 1000 email)

**Web App**
- Pagina **Impostazioni** (`/settings`) per configurare IMAP, colori UI
- **Vista dettaglio articolo** (`/article`) con contenuto HTML
- **Carica più email** (`/fetch-more-emails`) per batch IMAP successivi
- Debug IMAP (`/imap-debug`, `/imap-folders`)
- Campo `imap_max_emails` configurabile (validato 1-1000)
- Background task con `asyncio.create_task` invece di `BackgroundTasks`

**Bug fix**
- `get_article_list` passava `browser` invece di `context` (crash)
- Campi duplicati `intro_path`, `outro_path`, `use_web_search` in config
- Funzione `generate_audio` duplicata in `tts.py`
- Chiamate LLM sincrone in contesto async (ora tutte async)
- Paginazione duplicata (HTMX swap su `#articles-section` con `outerHTML`)
- `PodcastGenerator()` nel background task usava `.env` invece delle impostazioni web (`_cfg`)
- Status container mancante nella vista dettaglio articolo
- Gmail X-GM-LABELS non funzionava con cartelle annidate (`Newsletter/TAAFT`)

**Documentazione**
- `docs/library.md` — uso come libreria con esempi
- `docs/web-app.md` — web app, newsletter esempio, REST API, deploy, IMAP
- README aggiornato con Docker, multi-LLM, quick start, IMAP config

**Autenticazione OAuth + JWT**
- Login via **Google OAuth** (OpenID Connect) e **GitHub OAuth**
- **JWT HS256** firmato per sessioni (7 giorni)
- Tabella `users` in sqlite3 con profilo (email, nome, avatar)
- `create_session_token` / `decode_session_token` per gestione sessioni
- Fallback a `WEB_PASSWORD` se nessun OAuth configurato
- Modalità sviluppo senza autenticazione se nessuna protezione configurata
- Route `/auth/google`, `/auth/github`, `/auth/callback`, `/logout`
- Avatar e nome utente in navbar
- Scambio codice OAuth manuale con `httpx` (bypassa authlib session state, robusto anche con `--reload`)

**Lingua podcast configurabile**
- Campo `language` in Settings (predefinito: `italiano`)
- Selettore lingua in pagina Impostazioni
- `build_system_prompt(language)` parametrizzato
- Audio (TTS) sempre in italiano indipendentemente dalla lingua di traduzione

---

## Stato Attuale: Sviluppo v3.0 (Agent-Centric & Decentralizzato) 🚀

Stiamo attivamente lavorando alla versione 3.0, che segna il passaggio da un'architettura monolitica a un sistema **P2P Multi-Agente**.

### v3.0 — L'Era Decentralizzata

| Milestone | Stato | Descrizione |
|---|---|---|
| **BaseAgent Framework** | ✅ | Infrastruttura per agenti asincroni disaccoppiati. |
| **Network Agent (Nostr)** | 🏗️ | Gestione identità (chiavi) e comunicazione via protocollo Nostr. |
| **Storage Agent (IPFS)** | 🏗️ | Archiviazione distribuita basata su CID invece di file locali. |
| **Content Agent** | ✅ | Refactoring della logica core in forma di agente. |
| **Social Agent** | 📅 | Interazioni community (commenti, like) su protocollo aperto. |
| **Web UI Decentralizzata** | 📅 | Dashboard che interagisce con i relay Nostr. |

---

## Proposte per il futuro (Aggiornate)

### v3.1 — Qualità audio e produttività

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
