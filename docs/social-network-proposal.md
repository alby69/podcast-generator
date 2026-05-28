# Proposta: Evoluzione Social Network del Podcast Generator

> [!TIP]
> **Versione 3.0 Update:** Molte delle funzionalità social qui descritte verranno implementate tramite il protocollo **Nostr** (Social Agent), garantendo una rete social realmente decentralizzata e senza server centrali.

Questo documento delinea il piano tecnico per trasformare Podcast Generator in una piattaforma social multi-utente per la creazione, condivisione e discussione di podcast basati su newsletter.

## 1. Architettura Chat: Interna vs API Esterne

### Analisi Comparativa

| Funzionalità | Chat Interna (WebSockets) | Telegram Bot API | WhatsApp Business API |
| :--- | :--- | :--- | :--- |
| **Costo** | Gratuito (solo costo server) | Gratuito | Pagamento per conversazione |
| **Privacy** | Massima (dati su tuo server) | Media (dati su server Telegram) | Bassa (proprietà Meta) |
| **Sviluppo** | Complesso (da zero) | Semplice (API ricche) | Complesso (approvazioni Meta) |
| **Notifiche** | Solo web (o Push API) | Native su mobile | Native su mobile |
| **Integrazione** | Totale nella Web UI | Tramite Bot/Link esterni | Limitata |

### Raccomandazione: Il modello "Comunità Sovrana"
**Soluzione Ibrida focalizzata sulla Privacy:**
1.  **Motore di Chat Interno (FastAPI + WebSockets + HTMX):** Per gestire discussioni, gruppi e commenti direttamente sulla piattaforma. Questo garantisce che i dati degli utenti e i contenuti audio non escano mai dal sistema protetto.
2.  **Integrazione Telegram (Opzionale):** Usare Telegram esclusivamente come *canale di distribuzione e notifica*. Gli utenti possono collegare il proprio account Telegram per ricevere un avviso (e il file audio) quando un nuovo podcast viene generato nel loro gruppo, ma la "verità" dei dati risiede sul server interno.
3.  **WhatsApp (Scartato):** Troppo restrittivo, costoso e con policy sui dati incompatibili con una piattaforma libera e gratuita.

---

## 2. Gestione Archiviazione e Deduplicazione

Per evitare di sprecare spazio e risorse (specialmente per il TTS che può essere costoso), utilizzeremo un sistema di **Content Addressable Storage (CAS)**.

### Strategia di Deduplicazione (Content Hashing)
1.  **Identificazione Univoca:** Ogni podcast viene identificato da un hash SHA-256 calcolato sulla "ricetta" della generazione per massimizzare il risparmio:
    *   `hash_input = sha256(sorted_urls + voice_id + language + custom_prompt_options)`
2.  **Verifica Pre-Generazione:**
    *   Prima di chiamare l'LLM, controlliamo se esiste già un `script_hash` per quell'`hash_input`.
    *   Se lo script esiste, controlliamo se esiste già il file audio corrispondente.
3.  **Archiviazione Fisica:** I file audio vengono salvati in una struttura a cartelle basata sull'hash per evitare limiti di file per directory:
    *   `storage/audio/ab/cd/ef123456...mp3`
4.  **Referenziazione:** Se User B genera lo stesso contenuto di User A, il database creerà un nuovo record in `user_episodes` che punta allo stesso `audio_file_id`, senza duplicare il file.

---

## 3. Schema Database Multi-utente (Dettagliato)

L'attuale schema SQLite verrà esteso per supportare le funzionalità social e la multi-tenancy:

### Tabelle Core
*   **`users`**: `id, email, password_hash, name, avatar_url, telegram_id, created_at`
*   **`audio_files`**: `id, content_hash (SHA256), file_path, duration, size_bytes, created_at`
*   **`episodes`**: `id, audio_file_id, title, description, script_text, is_public, created_at`
*   **`user_episodes`**: `user_id, episode_id, added_at` (Libreria personale)

### Tabelle Social
*   **`groups`**: `id, owner_id, name, description, invite_code, is_private, created_at`
*   **`group_members`**: `group_id, user_id, role (admin/member), joined_at`
*   **`group_posts`**: `id, group_id, user_id, episode_id (optional), content_text, created_at`
*   **`comments`**: `id, post_id (or episode_id), user_id, text, created_at`
*   **`rss_subscriptions`**: `id, user_id (or group_id), rss_url, last_fetched`

---

## 4. Piano di Implementazione Passo-Passo

### Fase 1: Multi-tenancy e Deduplicazione
*   Migrazione del database per supportare la proprietà degli episodi.
*   Implementazione della logica di hashing per i file audio.
*   Refactoring del `builder.py` per controllare la cache degli hash prima di generare.

### Fase 2: Motore Social & Commenti
*   Creazione delle API per gruppi e commenti.
*   Interfaccia HTMX per postare commenti sotto ogni podcast senza ricaricare la pagina.
*   Sistema di "Condivisione" (generazione di un link univoco per un podcast esistente).

### Fase 3: Chat in Tempo Reale
*   Implementazione di WebSockets in FastAPI per una chat di gruppo "live".
*   Integrazione opzionale del Bot Telegram per ricevere il file MP3 direttamente sul telefono.

## 5. Considerazioni su Privacy e Dati
*   **No Pubblicità:** Il sistema è self-hosted o gestito privatamente, garantendo l'assenza di tracker pubblicitari.
*   **Open Source:** Il codice rimane trasparente e verificabile.
*   **Diritti:** I file audio generati rimangono di proprietà dell'istanza dell'utente, senza cessione di dati a terzi (tranne i provider LLM/TTS scelti, come Google o OpenAI, secondo i loro termini API).
