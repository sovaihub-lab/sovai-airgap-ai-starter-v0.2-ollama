import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List

LLM_ENABLED = os.getenv("LLM_ENABLED", "true").lower() == "true"
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://host.docker.internal:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")


class OllamaClient:
    def __init__(self, base_url: str = LLM_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    def health(self, timeout_seconds: float = 2.0) -> Dict[str, Any]:
        try:
            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            model_names = [m.get("name") for m in body.get("models", [])]
            return {
                "enabled": LLM_ENABLED,
                "reachable": True,
                "base_url": self.base_url,
                "configured_model": self.model,
                "available_models": model_names,
                "model_available": self.model in model_names,
            }
        except Exception as exc:
            return {
                "enabled": LLM_ENABLED,
                "reachable": False,
                "base_url": self.base_url,
                "configured_model": self.model,
                "available_models": [],
                "model_available": False,
                "error": str(exc),
            }

    def generate(self, prompt: str, timeout_seconds: float = 120.0) -> Dict[str, Any]:
        if not LLM_ENABLED:
            return {"used_llm": False, "error": "LLM is disabled by configuration.", "response": ""}

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.1,
                "top_p": 0.9,
                "num_ctx": 4096,
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            return {
                "used_llm": True,
                "model": self.model,
                "base_url": self.base_url,
                "response": body.get("response", "").strip(),
                "done": body.get("done"),
                "eval_count": body.get("eval_count"),
                "prompt_eval_count": body.get("prompt_eval_count"),
            }
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            return {
                "used_llm": False,
                "model": self.model,
                "base_url": self.base_url,
                "error": f"HTTP {exc.code}: {error_body}",
                "response": "",
            }
        except Exception as exc:
            return {
                "used_llm": False,
                "model": self.model,
                "base_url": self.base_url,
                "error": str(exc),
                "response": "",
            }


def build_grounded_rag_prompt(question: str, retrieved_chunks: List[Dict[str, Any]]) -> str:
    context_blocks = []
    for idx, item in enumerate(retrieved_chunks, start=1):
        context_blocks.append(
            f"""[Source {idx}]
Citation: {item["citation"]}
Document: {item["title"]}
Chunk ID: {item["chunk_id"]}
Text:
{item["text"]}
"""
        )

    context = "\n\n".join(context_blocks)

    return f"""
You are SovAI Private RAG Assistant running in an offline sovereign AI environment.

You must answer using ONLY the approved internal document context below.

Rules:
1. Do not use outside knowledge.
2. Do not guess.
3. If the answer is not supported by the context, say: "The approved internal documents do not contain enough information to answer this question."
4. Include citations using the provided Citation values.
5. Keep the answer concise and business-friendly.

Approved internal context:
{context}

User question:
{question}

Grounded answer with citations:
""".strip()
