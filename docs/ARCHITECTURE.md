# AgentMesh: Architettura Tecnica Avanzata

AgentMesh adotta un'architettura a strati (layers) per separare le responsabilità, garantire la massima decentralizzazione e abilitare un'economia agentica autonoma.

## I Layer di AgentMesh

### 1. Network Layer (P2P Mesh)
Il fondamento fisico e logico del sistema.
- **Tecnologia**: Nostr (NIP-01, NIP-04, NIP-94).
- **Ruolo**: Peer discovery, NAT traversal (via relay), trasporto eventi criptati.
- **Evoluzione**: Investigazione di `libp2p` per comunicazioni gossip mesh pure.

### 2. Storage Layer (Distributed Storage)
La memoria a lungo termine del mesh che elimina la necessità di hosting centrale.
- **Tecnologia**: IPFS (InterPlanetary File System).
- **Ruolo**: Archiviazione content-addressed. Ogni file (audio, script, metadati) è identificato da un CID (Content Identifier).

### 3. Coordination & Discovery Layer (Event Bus)
Il sistema nervoso che coordina gli agenti.
- **Tecnologia**: Nostr Events + **Routstr-style Discovery**.
- **Ruolo**: Registry distribuito. Gli agenti pubblicano le proprie "skills", "capabilities", "reputazione" e "prezzi" (es. 5 sats/request) come eventi Nostr.
- **Pattern**: Ispirato a Routstr per il routing decentralizzato delle richieste AI.

### 4. Incentives & Payments Layer (Value Transfer)
Abilita l'economia peer-to-peer (A2A).
- **Tecnologia**: **Lightning Network** + **Cashu** (ecash).
- **Ruolo**: Micropagamenti per inferenza AI, storage pinning, o task completati.

### 5. Knowledge & Structured Memory Layer
Mantiene lo stato e la conoscenza del mesh.
- **Tecnologia**: **OrbitDB** / **Ceramic** (dati strutturati), Vector DB locali (RAG).
- **Ruolo**: "Knowledge Graph" distribuito.

### 6. Agent Execution Layer (Reasoning & Planning)
Il motore cognitivo degli agenti.
- **Tecnologia**: LangGraph, DSPy, Agno, **agentstr-sdk**, **MCP (Model Context Protocol)**.
- **Ruolo**: Orchestrazione dei workflow e delegazione dei task via protocolli Agent-to-Agent.

### 7. Governance & Reputation Layer (Trust)
Il layer sociale e di verifica.
- **Tecnologia**: **Nostr Web of Trust (WoT)**, firme crittografiche.
- **Ruolo**: Gestire la fiducia tra agenti basata sul lavoro svolto.

---

## Componenti del Monorepo

- **Core (`agentmesh-core`)**: Interfacce base e orchestrazione.
- **Relay (`agentmesh-relay`)**: Identità Nostr e P2P.
- **Vault (`agentmesh-vault`)**: Integrità dei dati tramite IPFS.
- **Applications (`apps/`)**: Casi d'uso reali come **PodcastGen**.
