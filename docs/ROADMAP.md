# Roadmap AgentMesh

## v2.0 — Fondamenta (Completata)
Trasformazione del progetto in una libreria Python modulare e Web App funzionale.
- [x] Architettura a libreria (`podcast_generator/`)
- [x] Multi-LLM (Gemini, OpenAI, Anthropic, Ollama)
- [x] Multi-TTS (Edge-TTS, ElevenLabs)
- [x] Web UI con FastAPI + HTMX
- [x] Autenticazione OAuth (Google/GitHub) + JWT
- [x] Supporto IMAP per newsletter via email

---

## v3.0 — L'Era Decentralizzata (In Corso) 🚀
Passaggio a un'architettura **Agent-Centric P2P** basata su Nostr e IPFS.

### Fase 1: Infrastruttura Core (In Corso)
- [x] Definizione `BaseAgent` e Orchestratore
- [x] Content Agent (Refactoring logica core)
- [x] Network Agent (PoC Nostr Identity)
- [x] Storage Agent (PoC IPFS Abstraction)

### Fase 2: Integrazione `agentstr-sdk` & MCP (Focus Attuale) 🎯
Integrazione profonda per abilitare l'economia agentica e la compatibilità standard.
- [ ] **Compatibilità MCP**: Implementazione di MCPServer per esporre tool degli agenti.
- [ ] **Agent-to-Agent (A2A)**: Protocollo di delegazione task tra agenti.
- [ ] **Discovery Layer**: Registry degli agenti basato su eventi Nostr (skills/prezzi).
- [ ] **Micropagamenti**: Integrazione Lightning Network / Cashu per task-bidding.

### Fase 3: IPFS & Vault Avanzato
- [ ] Integrazione Pinata/Local Node reale.
- [ ] Deduplicazione nativa basata su CID.
- [ ] Cache LRU per contenuti distribuiti.

### Fase 4: Social Layer & Web UI v3
- [ ] Feed community basato su eventi Nostr (NIP-94).
- [ ] Commenti e Reaction decentralizzate.

---

## Proposte Future
- [ ] Integrazione OrbitDB per stati strutturati.
- [ ] Supporto PostgreSQL per istanze multi-utente massive.
- [ ] Cloud Storage fallback (S3/GCS).
