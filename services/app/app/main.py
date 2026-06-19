import os
import socket
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.audit import write_audit
from app.rag import PrivateRAG
from app.ml import TinyMLClassifier
from app.agent import LocalAgentRuntime
from app.llm import OllamaClient, build_grounded_rag_prompt


app = FastAPI(
    title="SovAI Air-Gap AI Starter",
    version="0.2.0",
    description="Offline-first sovereign AI reference implementation for local LLM RAG, ML, and approved local agents.",
)

rag = PrivateRAG()
classifier = TinyMLClassifier()
agent = LocalAgentRuntime(rag=rag, classifier=classifier)
llm = OllamaClient()


class AskRequest(BaseModel):
    question: str
    top_k: int = 3
    use_llm: bool = True


class ClassifyRequest(BaseModel):
    text: str


class AgentRunRequest(BaseModel):
    tool: str
    input: str


def internet_probe(timeout_seconds: float = 1.5) -> Dict[str, Any]:
    try:
        sock = socket.create_connection(("1.1.1.1", 443), timeout=timeout_seconds)
        sock.close()
        return {"internet_reachable": True, "details": "Outbound TCP connection succeeded"}
    except Exception as exc:
        return {"internet_reachable": False, "details": str(exc)}


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return """
<!doctype html>
<html>
<head>
  <title>SovAI Air-Gap AI Starter</title>
  <style>
    body { font-family: Arial, sans-serif; background: #07111f; color: #e8f1ff; margin: 0; padding: 32px; }
    h1 { font-size: 34px; margin-bottom: 4px; }
    h2 { color: #62d9ff; }
    .card { border: 1px solid #1e81b0; background: #0c1a2c; border-radius: 12px; padding: 20px; margin: 18px 0; }
    textarea, input { width: 100%; background: #081525; color: #e8f1ff; border: 1px solid #2b7fa8; border-radius: 8px; padding: 10px; }
    button { background: #12b5cb; color: #00131a; border: 0; padding: 10px 16px; margin-top: 10px; border-radius: 8px; font-weight: bold; cursor: pointer; }
    pre { white-space: pre-wrap; background: #050b12; padding: 14px; border-radius: 8px; border: 1px solid #153b52; }
    .ok { color: #6dffb8; }
  </style>
</head>
<body>
  <h1>SovAI Air-Gap AI Starter</h1>
  <p class="ok">Runtime mode: local Ollama LLM + internal artifacts + offline-ready RAG</p>

  <div class="card">
    <h2>Status</h2>
    <button onclick="status()">Check Status</button>
    <pre id="statusResult"></pre>
  </div>

  <div class="card">
    <h2>Private RAG with Local Ollama Model</h2>
    <textarea id="q" rows="3">Who can access confidential finance reports?</textarea>
    <button onclick="ask()">Ask with LLM</button>
    <button onclick="askNoLlm()">Retrieve Only</button>
    <pre id="askResult"></pre>
  </div>

  <div class="card">
    <h2>Local ML Classifier</h2>
    <textarea id="ml" rows="2">User cannot access VPN and needs MFA reset.</textarea>
    <button onclick="classify()">Classify</button>
    <pre id="mlResult"></pre>
  </div>

  <div class="card">
    <h2>Approved Local Agent Tool</h2>
    <input id="tool" value="calculator" />
    <br/><br/>
    <input id="toolInput" value="(12 * 7) + 5" />
    <button onclick="runAgent()">Run Tool</button>
    <pre id="agentResult"></pre>
  </div>

<script>
async function status() {
  const res = await fetch('/status');
  document.getElementById('statusResult').innerText = JSON.stringify(await res.json(), null, 2);
}
async function ask() {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: document.getElementById('q').value, top_k: 3, use_llm: true})
  });
  document.getElementById('askResult').innerText = JSON.stringify(await res.json(), null, 2);
}
async function askNoLlm() {
  const res = await fetch('/ask', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({question: document.getElementById('q').value, top_k: 3, use_llm: false})
  });
  document.getElementById('askResult').innerText = JSON.stringify(await res.json(), null, 2);
}
async function classify() {
  const res = await fetch('/ml/classify', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({text: document.getElementById('ml').value})
  });
  document.getElementById('mlResult').innerText = JSON.stringify(await res.json(), null, 2);
}
async function runAgent() {
  const res = await fetch('/agent/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({tool: document.getElementById('tool').value, input: document.getElementById('toolInput').value})
  });
  document.getElementById('agentResult').innerText = JSON.stringify(await res.json(), null, 2);
}
</script>
</body>
</html>
    """


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}


@app.get("/status")
def status() -> Dict[str, Any]:
    payload = {
        "offline_mode": os.getenv("SOVAI_OFFLINE_MODE", "false").lower() == "true",
        "approved_tools": sorted(agent.approved_tools),
        "document_count": len(set(c.document_id for c in rag.chunks)),
        "chunk_count": len(rag.chunks),
        "retrieval": "pure-python-bm25",
        "llm": llm.health(),
        "internet_probe": internet_probe(),
        "artifact_source": "internal-artifact-hub-plus-local-ollama",
    }
    write_audit("status_check", payload)
    return payload


@app.post("/reload")
def reload_documents() -> Dict[str, Any]:
    result = rag.reload()
    event_id = write_audit("documents_reloaded", result)
    return {"event_id": event_id, **result}


@app.post("/ask")
def ask(req: AskRequest) -> Dict[str, Any]:
    retrieved = rag.search(req.question, top_k=req.top_k)

    if not retrieved:
        result = {
            "answer": "The approved internal documents do not contain enough information to answer this question.",
            "confidence": "low",
            "used_llm": False,
            "llm_error": None,
            "model": None,
            "citations": [],
            "retrieved_chunks": [],
        }
    elif req.use_llm:
        prompt = build_grounded_rag_prompt(req.question, retrieved)
        llm_result = llm.generate(prompt)
        citations = [item["citation"] for item in retrieved]

        if llm_result.get("used_llm") and llm_result.get("response"):
            result = {
                "answer": llm_result["response"],
                "confidence": "llm-grounded",
                "used_llm": True,
                "model": llm_result.get("model"),
                "llm_base_url": llm_result.get("base_url"),
                "llm_error": None,
                "citations": citations,
                "retrieved_chunks": retrieved,
                "prompt_eval_count": llm_result.get("prompt_eval_count"),
                "eval_count": llm_result.get("eval_count"),
            }
        else:
            fallback = rag.answer(req.question, top_k=req.top_k)
            result = {
                **fallback,
                "used_llm": False,
                "model": llm_result.get("model"),
                "llm_base_url": llm_result.get("base_url"),
                "llm_error": llm_result.get("error"),
                "fallback": "extractive-retrieval-only",
            }
    else:
        fallback = rag.answer(req.question, top_k=req.top_k)
        result = {
            **fallback,
            "used_llm": False,
            "model": None,
            "llm_error": None,
            "fallback": "extractive-retrieval-only",
        }

    event_id = write_audit(
        "rag_question_answered",
        {
            "question": req.question,
            "top_k": req.top_k,
            "use_llm_requested": req.use_llm,
            "used_llm": result.get("used_llm", False),
            "model": result.get("model"),
            "confidence": result.get("confidence"),
            "citations": result.get("citations", []),
            "llm_error": result.get("llm_error"),
        },
    )

    return {"event_id": event_id, **result}


@app.post("/ml/classify")
def classify(req: ClassifyRequest) -> Dict[str, Any]:
    result = classifier.classify(req.text)
    event_id = write_audit("ml_classification", {"text": req.text, "label": result["label"], "scores": result["scores"]})
    return {"event_id": event_id, **result}


@app.post("/agent/run")
def run_agent(req: AgentRunRequest) -> Dict[str, Any]:
    result = agent.run(req.tool, req.input)
    event_id = write_audit("agent_tool_invocation", {"tool": req.tool, "input": req.input, "allowed": result.get("allowed", False)})
    return {"event_id": event_id, **result}
