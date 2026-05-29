# Piano di Integrazione: `agentstr-sdk`, MCP & Marketplace

Questo documento definisce il piano d'azione per integrare `agentstr-sdk`, abilitando la compatibilità con il Model Context Protocol (MCP) e l'economia Agent-to-Agent (A2A).

## Stato di Avanzamento

| Task | Stato | Note |
| :--- | :---: | :--- |
| **Identità Nostr via `agentstr`** | 🏗️ | In fase di refactoring in `NetworkAgent`. |
| **MCPServer Implementation** | 📅 | Definizione dei tool per `ContentAgent`. |
| **A2A Protocol** | 📅 | Definizione schema eventi per delegazione task. |
| **Lightning/Cashu Wallet** | 📅 | Configurazione provider (LNbits/Phoenixd). |
| **Discovery Registry** | 📅 | Implementazione NIP per Service Announcement. |

---

## Dettaglio Task

### 1. Refactoring BaseAgent
Sostituire la gestione manuale dei relay Nostr con l'astrazione fornita da `agentstr.Agent`.

### 2. Implementazione Tools MCP
Ogni agente AgentMesh deve agire come un server MCP, esponendo le proprie capacità.
- **PodcastGen Tool**: `generate_episode(urls: list)`
- **Search Tool**: `search_web(query: str)`

### 3. Economia A2A (Bidding & Payment)
Abilitare il flusso di "Assunzione" tra agenti (es. `TravelAgent` che paga `WeatherAgent`).
1. **Request**: L'agente A pubblica un task su Nostr.
2. **Offer**: Gli agenti B, C rispondono con un preventivo (sats).
3. **Escrow/Payment**: L'agente A seleziona B e invia un token Cashu o paga un'invoice LN.
4. **Delivery**: L'agente B consegna il risultato (CID su IPFS).

### 4. Discovery Marketplace (Routstr-style)
Creare una directory dinamica per scoprire i servizi disponibili sul mesh interrogando i relay Nostr.
