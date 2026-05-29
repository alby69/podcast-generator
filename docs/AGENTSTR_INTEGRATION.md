# Piano di Integrazione: `agentstr-sdk` & MCP

Questo documento descrive la strategia per integrare `agentstr-sdk` all'interno di AgentMesh per abilitare la compatibilità MCP, i micropagamenti e la comunicazione Agent-to-Agent (A2A) avanzata.

## Obiettivi
1.  **Compatibilità MCP**: Rendere gli agenti AgentMesh capaci di usare e offrire "Tools" tramite il Model Context Protocol.
2.  **Identità Nostr Nativa**: Sostituire o potenziare `agentmesh-relay` con le astrazioni di `agentstr`.
3.  **Economia Integrata**: Abilitare pagamenti Lightning/Cashu per l'esecuzione di task.
4.  **Discovery**: Implementare il pattern "Routstr" per la scoperta degli agenti.

---

## Fase 1: Refactoring del Layer Relay
Attualmente, `agentmesh-relay` gestisce Nostr in modo custom. `agentstr-sdk` offre un'interfaccia più orientata agli agenti.

**Task:**
- [ ] Integrare `agentstr.Agent` all'interno di `BaseAgent`.
- [ ] Mappare le chiavi Nostr esistenti nel formato richiesto da `agentstr`.
- [ ] Implementare `agent_discovery.py` per registrare le capacità dell'agente sui relay.

## Fase 2: Supporto MCP (Model Context Protocol)
MCP permette agli agenti di connettersi a sorgenti dati e tool esterni in modo standardizzato.

**Task:**
- [ ] Implementare un `MCPServer` (via `agentstr`) per ogni agente AgentMesh che espone le proprie funzioni core come tool.
- [ ] Esempio: Il `ContentAgent` espone un tool `generate_podcast(url)`.
- [ ] Implementare un `MCPClient` per permettere agli agenti di chiamare tool di altri agenti nel mesh.

## Fase 3: Micropagamenti & Incentivi
Integrazione di Lightning e Cashu per rendere gli agenti economicamente autonomi.

**Task:**
- [ ] Configurazione di un wallet (LNbits o Phoenixd) interfacciato con `agentstr`.
- [ ] Implementazione del flusso di pagamento:
    - Richiesta Task -> Generazione Invoice (Lightning) -> Pagamento -> Esecuzione Task.
- [ ] Supporto per **Cashu tokens** per pagamenti offline/privati tra agenti.

## Fase 4: Routing & Marketplace (Routstr Style)
Creazione di un marketplace decentralizzato dove gli agenti possono "noleggiare" capacità computazionale.

**Task:**
- [ ] Definizione degli eventi Nostr di tipo "Service Announcement" (ispirati a Routstr).
- [ ] Implementazione della logica di "Bidding": l'agente pubblica un task e seleziona il provider con il miglior rapporto qualità/prezzo.

---

## Esempio di Codice (Target)

```python
from agentstr import Agent, MCPServer
from agentmesh.core import BaseAgent

class MyMeshAgent(BaseAgent):
    def __init__(self, ...):
        self.agent = Agent(name="PodcastAgent", use_lightning=True)

    async def start(self):
        # Registra i tool MCP
        server = MCPServer(self.agent)
        server.add_tool(self.fetch_newsletter)
        await server.start()

        # Annuncia la presenza su Nostr
        await self.agent.publish_announcement(
            skills=["podcast", "tts"],
            price_per_use="50 sats"
        )
```

## Prossimi Passi
1. Creare un prototipo in `packages/agentmesh-core/examples/agentstr_poc.py`.
2. Aggiornare `apps/podcast-generator` per usare il nuovo sistema di discovery.
