

# SovAIHub ([SovAIHub.com](https://SovAIHub.com))

# SovAI Air-Gap AI Starter v0.2
Open-source laptop MVP for demonstrating an air-gap-ready Sovereign AI pattern using Docker Desktop and local Ollama.

## Phase 2: Local LLM RAG Demo

### Short Description

The Local LLM RAG Demo extends the offline runtime foundation by adding a local language model through Ollama. This phase turns the document retrieval demo into a true private RAG workflow: documents are retrieved locally, a grounded prompt is created, the local LLM generates an answer, and citations are returned with the response.

The model runs on the user's laptop through Ollama using `llama3.2:1b`. No external LLM API is required at runtime.

## What This Phase Proves

- Private RAG can run with a local model.
- Enterprise documents stay local.
- The application retrieves approved document chunks.
- The prompt is grounded in retrieved internal context.
- Ollama generates the final answer locally.
- The answer includes citations.
- Audit logs capture the question, model usage, citations, and runtime decision.
- No OpenAI, Azure OpenAI, Anthropic, or public API call is required.

## Repository

```bash
git clone <your-github-repo-url>
cd sovai-airgap-ai-starter-v0.2-ollama
```

## Prerequisites

- Download and Install OLLAMA using https://ollama.com/download/[windows/mac/linux]
- Docker Desktop (or any Container)
- Ollama installed
- `llama3.2:1b` pulled before going offline

Pull the model while internet is available:

```bash
ollama pull llama3.2:1b
```

Confirm the model is available:

```bash
ollama list
```

Confirm Ollama API is working:

```bash
curl http://127.0.0.1:11434/api/tags
```

## Setup: Connected Preparation Phase

Run while internet is available:

```bash
chmod +x scripts/*.sh
./scripts/prepare-online.sh
```

This script:

1. Checks Docker
2. Checks that `llama3.2:1b` exists locally
3. Builds the application Docker image
4. Saves the image as an offline artifact
5. Downloads Python wheels into `artifact-hub/wheelhouse`
6. Creates checksums
7. Creates a portable artifact bundle

Generated artifacts include:

```text
artifact-hub/images/sovai-airgap-app-v0.2.tar
artifact-hub/wheelhouse/
artifact-hub/checksums.sha256
sovai-airgap-artifact-bundle-v0.2.tar.gz
```

## Setup: Offline Runtime Phase

Disconnect internet:

```text
Turn off Wi-Fi, unplug network, or disable VPN.
```

Keep Ollama running locally.

Then start the platform:

```bash
./scripts/bootstrap-offline.sh
```

Open the UI:

```text
http://127.0.0.1:8080
```

## Configuration

Main configuration file:

```text
docker-compose.yml
```

Important environment variables:

```text
SOVAI_OFFLINE_MODE: "true"
LLM_ENABLED: "true"
LLM_BASE_URL: "http://host.docker.internal:11434"
OLLAMA_MODEL: "llama3.2:1b"
APPROVED_TOOLS: "calculator,document_search,ticket_classifier"
DOCUMENTS_DIR: "/app/data/documents"
AUDIT_LOG_PATH: "/app/data/audit/audit-log.jsonl"
```

The Docker container reaches host Ollama using:

```text
http://host.docker.internal:11434
```

## How RAG Works

```text
User question
  -> Local BM25 document retrieval
  -> Relevant chunks selected from data/documents
  -> Grounded prompt created
  -> Prompt sent to local Ollama llama3.2:1b
  -> Answer generated locally
  -> Citations attached
  -> Audit log written
```

## Test Commands

Check status:

```bash
curl -s http://127.0.0.1:8080/status
```

Expected LLM section:

```json
"llm": {
  "reachable": true,
  "configured_model": "llama3.2:1b",
  "model_available": true
}
```

Ask with local LLM:

```bash
curl -s http://127.0.0.1:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Who can access confidential finance reports?","top_k":3,"use_llm":true}'
```

Run retrieve-only fallback:

```bash
curl -s http://127.0.0.1:8080/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Who can access confidential finance reports?","top_k":3,"use_llm":false}'
```

## Troubleshooting

### Problem: Ollama model not found

Check:

```bash
ollama list
```

If `llama3.2:1b` is missing, run while connected:

```bash
ollama pull llama3.2:1b
```

### Problem: Docker app cannot reach Ollama

Check from host:

```bash
curl http://127.0.0.1:11434/api/tags
```

If this works but `/status` shows Ollama unreachable from the container, set Ollama to listen on all interfaces.

On Windows PowerShell:

```powershell
setx OLLAMA_HOST "0.0.0.0:11434"
```

Then restart Ollama from the system tray or restart the machine.

### Problem: Browser cannot open the app

Use:

```text
http://127.0.0.1:8080
```

Check container status:

```bash
docker compose ps
docker logs sovai-airgap-app
```

### Problem: Port not published

Check:

```bash
docker port sovai-airgap-app
```

Expected:

```text
8080/tcp -> 0.0.0.0:8080
```

If empty:

```bash
docker compose down --remove-orphans
docker rm -f sovai-airgap-app >/dev/null || true
docker compose up -d --no-build --force-recreate
```

### Problem: Docker network too restrictive

For laptop testing, use:

```yaml
networks:
  sovai_internal:
    driver: bridge
```

Avoid `internal: true` in the first working demo because the app needs to reach host Ollama.

### Problem: Internet check fails because the internet is still available

The offline bootstrap intentionally checks that the internet is disconnected.

Disconnect Wi-Fi, unplug Ethernet, or disable VPN, then rerun:

```bash
./scripts/bootstrap-offline.sh
```

## Positioning

This phase is a working local LLM RAG reference implementation. It is not a full enterprise TL4 deployment, but it demonstrates the core architecture pattern:

- Local documents.
- Local model.
- Local runtime.
- Approved tools.
- Audit logging.
- No external LLM API.


## Contributor

- Rana Kumar - [LinkedIn](https://www.linkedin.com/in/rana-kumar-333b56127/) - SovAIHub ([SovAIHub.com](https://SovAIHub.com))
