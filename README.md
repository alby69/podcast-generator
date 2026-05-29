# AgentMesh

> **A decentralized coordination mesh for autonomous AI agents.**

AgentMesh is an open-source framework and ecosystem designed to build, deploy, and orchestrate AI agents in a truly decentralized environment. By combining **Nostr** for coordination, **IPFS** for storage, and a **Multi-Agent** architecture, AgentMesh enables a "serverless" future for AI applications.

---

## 🌟 La Visione

AgentMesh non è solo un software, è un'infrastruttura per la sovranità digitale.

- **Senza Server Centrali**: Nessun singolo punto di fallimento. Il sistema vive sui nodi degli utenti.
- **Identità Sovrana**: Ogni agente e utente possiede le proprie chiavi crittografiche (Nostr).
- **Memoria Distribuita**: I dati sono archiviati su IPFS, rendendoli permanenti e indirizzabili per contenuto.
- **Collaborazione Agente-Agente (A2A)**: Gli agenti cooperano via protocolli aperti, non API proprietarie.

---

## 🏗️ Struttura del Progetto

Il repository è organizzato come un monorepo gestito con `uv`.

### Core Packages (`packages/`)
- **[`agentmesh-core`](packages/agentmesh-core)**: Il "cervello" del sistema. Definisce le interfacce base, l'orchestrazione e i provider LLM/TTS.
- **[`agentmesh-relay`](packages/agentmesh-relay)**: Il layer di comunicazione P2P basato sul protocollo **Nostr**.
- **[`agentmesh-vault`](packages/agentmesh-vault)**: Il layer di archiviazione distribuita basato su **IPFS**.
- **[`agentmesh-studio`](packages/agentmesh-studio)**: Strumenti CLI e dashboard per monitorare e gestire il mesh.

### Applications (`apps/`)
- **[`podcast-generator`](apps/podcast-generator)**: Il nostro caso d'uso principale. Una pipeline completa che trasforma newsletter in podcast in modo autonomo e distribuito.

---

## 🎙️ Caso d'Uso: Podcast Generator

**PodcastGen** è la dimostrazione di cosa può fare AgentMesh. Trasforma contenuti testuali in episodi audio, li distribuisce via IPFS e li annuncia sulla rete Nostr.

### Quick Start (PodcastGen)

```bash
# Installa le dipendenze
uv sync
playwright install firefox

# Configura l'ambiente
cp .env.example .env
# Modifica .env con le tue chiavi API (Gemini, OpenAI, etc.)

# Avvia la generazione via CLI
python apps/podcast-generator/main.py daily

# Avvia l'interfaccia Web
PYTHONPATH=apps/podcast-generator uvicorn podcast_generator.web.app:app --reload
```

Consulta la [documentazione di PodcastGen](apps/podcast-generator/README.md) per maggiori dettagli.

---

## 🚀 Verso la v3.0

Stiamo attivamente migrando PodcastGen verso l'architettura AgentMesh v3.0 (Agent-Centric).
I punti chiave della roadmap includono:
- Integrazione nativa con **agentstr-sdk** per compatibilità **MCP** (Model Context Protocol).
- Protocollo di comunicazione **Agent-to-Agent (A2A)** standardizzato.
- Web UI completamente decentralizzata che interroga i relay Nostr.

Consulta [docs/v3-agent-centric-roadmap.md](docs/v3-agent-centric-roadmap.md) per i dettagli tecnici.

---

## 📖 Documentazione

| Documento | Destinatario | Contenuto |
|---|---|---|
| [docs/VISION.md](docs/VISION.md) | Tutti | La filosofia e il "perché" dietro AgentMesh |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Sviluppatori | Dettagli tecnici sui layer del mesh |
| [docs/AGENTSTR_INTEGRATION.md](docs/AGENTSTR_INTEGRATION.md) | Sviluppatori | Piano di integrazione MCP e agentstr-sdk |
| [apps/podcast-generator/README.md](apps/podcast-generator/README.md) | Utenti | Guida completa all'app podcast |

---

## Contribuire

Siamo in una fase di sviluppo intensa. Se vuoi contribuire alla costruzione di un futuro AI decentralizzato, apri una Issue o una Pull Request.

**AgentMesh: The mesh is the message.**
