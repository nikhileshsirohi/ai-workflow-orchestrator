from __future__ import annotations

import json
from typing import Any, Dict, List, Tuple

import requests

from app.config import OLLAMA_URL, OLLAMA_MODEL


SYSTEM_PROMPT = """You are a workflow planner for an AI system.
You must output ONLY valid JSON with this schema:

{
  "steps": [
    {
      "tool_name": "<string>",
      "input": { ... any json ... }
    }
  ]
}

Allowed tool_name values:
- "echo"
- "unstable"

Rules:
- Output JSON only. No markdown. No explanations.
- steps must be a non-empty list.
- Keep the plan short (1 to 4 steps).
"""


def plan_workflow(request_text: str) -> Tuple[List[Dict[str, Any]], str | None]:
    """
    Calls Ollama to generate a workflow plan.
    Returns (steps, error). steps is list of {"tool_name":..., "input":...}
    """
    prompt = f"""
User request: {request_text}

Return ONLY JSON following the schema.
"""

    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.2},
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json().get("response", "").strip()

        # Parse JSON strictly
        obj = json.loads(text)
        steps = obj.get("steps", None)

        if not isinstance(steps, list) or len(steps) == 0:
            return [], "Planner returned invalid or empty steps"

        # Validate tool names quickly
        for s in steps:
            if s.get("tool_name") not in ("echo", "unstable"):
                return [], f"Invalid tool_name from planner: {s.get('tool_name')}"
            if "input" not in s or not isinstance(s["input"], dict):
                return [], "Planner step missing valid input dict"

        return steps, None

    except json.JSONDecodeError:
        return [], f"Planner did not return valid JSON. Raw: {text[:300]}"
    except requests.RequestException as e:
        return [], f"Ollama request failed: {e}"
    except Exception as e:
        return [], f"Planner crashed: {e}"