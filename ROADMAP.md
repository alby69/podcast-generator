# Roadmap — Web App Podcast Generator

## Visione

Interfaccia web dove l'utente incolla l'URL di una newsletter, vede l'elenco degli articoli con descrizione, seleziona quelli che vuole e genera file audio MP3 con un click.

```
Incolla URL newsletter
        │
        ▼
┌──────────────────────────────┐
│  Elenco articoli trovati:    │
│                              │
│  ☑ AI Framework XYZ lancia  │
│     nuova versione 5.0       │
│  ☑ OpenAI annuncia GPT-5    │
│  ☑ Nuovo tool per MLops     │
│     ...                      │
│                              │
│  [Seleziona tutti]  [Genera] │
└──────────────────────────────┘
        │
        ▼
   Download MP3 pronto
```

## Stack consigliato

### Backend: **FastAPI** (Python)
- Stesso linguaggio del progetto, riusa `src/builder.py` e tutti i moduli esistenti
- Async nativo (compatibile con `edge-tts`, `playwright`)
- Documentazione automatica OpenAPI
- Built-in validazione Pydantic (compatibile con le dataclass esistenti)

### Database: **SQLite + SQLModel**
- Zero configurazione, file-based, perfetto per deploy singolo utente
- SQLModel = Pydantic + SQLAlchemy, typing forte
- Per salvare: cronologia episodi, preferenze utente, newsletter processate
- In futuro si scala a PostgreSQL se serve multi-utente

### Frontend: **FastHTML** (consigliato) **oppure** HTMX + Jinja2

**Opzione A — FastHTML (Answer.AI)**
- Framework Python puro per HTML reattivo
- Server-side rendering, niente JavaScript
- Unico file Python per tutta la UI
- Perfetto per app monouso/small team

**Opzione B — HTMX + Jinja2 + Tailwind** (più flessibile)
- HTMX per interattività senza scrivere JS
- Jinja2 template (già incluso in FastAPI)
- Tailwind CSS per UI accattivante
- Più controllabile se l'app cresce

### Per iniziare subito: **Gradio**
- Ancora più veloce: una griglia di checkbox + pulsante
- Componenti UI già pronti, stile Hugging Face
- Meno bello esteticamente, ma funzionale in 20 righe

## Architettura Web

```
┌──────────┐     ┌──────────────────────────────────────┐
│  Browser │────▶│  FastAPI /src/web/                    │
│  (HTMX)  │     │                                      │
└──────────┘     │  GET / → form inserimento URL        │
                 │  POST /fetch → estrai articoli        │
                 │  POST /generate → seleziona + genera  │
                 │  GET /download/{id} → scarica MP3    │
                 │                                      │
                 │  /src/builder.py (riusato!)           │
                 │  /src/fetcher.py                      │
                 │  /src/translator.py                   │
                 │  /src/tts.py                          │
                 │  /src/tracker.py                      │
                 │  /src/audio.py                        │
                 └──────────────────────────────────────┘
                              │
                     ┌───────▼────────┐
                     │  podcast.db    │
                     │  SQLite        │
                     └────────────────┘
```

## Tabella di marcia

### Fase 1 — Setup web (settimana 1)
- [ ] Installare FastAPI + uvicorn + SQLModel
- [ ] Creare `src/web/` con struttura base
- [ ] Spostare logica di estrazione articoli (oggi `fetcher.py` prende tutto il body, serve estrarre singoli articoli con titolo e descrizione)
- [ ] Esporre endpoint `POST /fetch-articles` che accetta URL, estrae lista articoli
- [ ] Template HTML minimale: form URL + lista risultati

### Fase 2 — Selezione e generazione (settimana 2)
- [ ] Endpoint `POST /generate` che accetta URL articolo + voce TTS
- [ ] Feedback progresso (SSE o polling)
- [ ] Download file MP3 generato
- [ ] Salvataggio cronologia in SQLite

### Fase 3 — UX accattivante (settimana 3)
- [ ] Tailwind CSS per UI moderna
- [ ] Preview testo tradotto prima di generare audio
- [ ] Player audio embedded per ascoltare prima di scaricare
- [ ] Stato "in elaborazione" con spinner

### Fase 4 — Selezione multipla e playlist (settimana 4)
- [ ] Seleziona/deseleziona articoli individuali
- [ ] Selzione "tutti" / "nessuno"
- [ ] Generazione audio multipla in batch
- [ ] Unione playlist → singolo MP3 (riusa `merge_audio_files`)

### Fase 5 — Polish (futuro)
- [ ] Autenticazione base (password single-user)
- [ ] Deploy Docker
- [ ] Supporto multi-lingua (altre voci Edge-TTS)
- [ ] Ricerca e filtro cronologia
- [ ] Esportazione RSS per podcast player (Apple/Spotify)

## Cambiamenti necessari al codice esistente

1. **`src/fetcher.py`** — Aggiungere funzione che estrae singoli articoli (titolo + descrizione breve) dalla pagina archive, non solo il body completo. Attualmente prende tutto il contenuto di un post. Serve una modalità "summary" che estragga una lista di titoli/descrizioni.

2. **`src/builder.py`** — Aggiungere funzione `fetch_article_list(url, ...) -> list[ArticleItem]` che restituisce articoli senza tradurre

3. **Audio** — Il servizio audio già supporta merge, va bene

## Esempio di nuova struttura `src/web/`

```
src/web/
├── __init__.py
├── app.py              # FastAPI app, routes, startup
├── db.py               # SQLModel models + session
├── templates/
│   ├── base.html       # Layout Tailwind
│   ├── index.html      # Form URL
│   ├── articles.html   # Lista articoli con checkbox
│   ├── progress.html   # Stato generazione
│   └── history.html    # Cronologia
└── static/
    └── style.css
```

## Perché FastAPI + HTMX (non React/Next.js)

| Criterio | FastAPI + HTMX | React / Next.js |
|----------|---------------|-----------------|
| Stessa lingua del progetto | ✅ Python | ❌ JavaScript |
| Riuso codice esistente | Diretto (import builder) | Richiede API layer |
| Complessità setup | Bassa | Alta (node, build, routing) |
| Bundle size | Minimo (HTML + CSS) | Centinaia di KB JS |
| Tempo per MVP | Giorni | Settimane |
| SEO | ✅ server-side | ❌ client-side |
| Manutenzione unica persona | ✅ | ❌ (due codebase) |
