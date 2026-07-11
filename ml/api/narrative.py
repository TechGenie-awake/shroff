"""Optional LLM narrative — env-gated, NEVER on the decision path.

If LLM_API_KEY is set, one call to an OpenAI-compatible chat endpoint (base URL
LLM_BASE_URL, model LLM_MODEL) prose-ifies the already-computed reasons. Uses stdlib
urllib so there is no extra dependency; any failure silently falls back to the template
reasons (the default path). Nothing generative ever computes a number.
"""
from __future__ import annotations

import json
import os
import urllib.request

DEFAULT_BASE_URL = "https://api.openai.com/v1/chat/completions"
DEFAULT_MODEL = "gpt-4o-mini"


def maybe_narrative(payload: dict) -> str | None:
    key = os.environ.get("LLM_API_KEY")
    if not key:
        return None
    base_url = os.environ.get("LLM_BASE_URL", DEFAULT_BASE_URL)
    model = os.environ.get("LLM_MODEL", DEFAULT_MODEL)
    try:
        facts = {
            "name": payload["name"], "score": payload["score"], "band": payload["band"],
            "pd_12m": payload["pd_12m"], "decision": payload["decision"],
            "reasons": payload["reasons"],
            "early_warning": payload["overlays"]["early_warning"],
            "phoenix_flag": payload["overlays"]["screening"]["phoenix_flag"],
        }
        prompt = (
            "You are a bank credit analyst. Write a 3-4 sentence plain-English narrative of "
            "this MSME credit assessment for a loan officer. Use ONLY the facts given — do "
            "not invent numbers or change any figure. Facts:\n"
            + json.dumps(facts, ensure_ascii=False)
        )
        body = json.dumps({
            "model": model,
            "max_tokens": 300,
            "messages": [{"role": "user", "content": prompt}],
        }).encode()
        req = urllib.request.Request(
            base_url,
            data=body,
            headers={"content-type": "application/json",
                     "authorization": f"Bearer {key}"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        return data.get("choices", [{}])[0].get("message", {}).get("content") or None
    except Exception:
        return None  # template reasons are the default path and must always work
