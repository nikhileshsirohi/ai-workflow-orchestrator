from __future__ import annotations

import random
import time
from typing import Any, Callable, Dict, Tuple


# Tool function signature:
#   tool(input: dict) -> (output: dict, error: str|None)
ToolFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str | None]]


def tool_echo(inp: Dict[str, Any]) -> tuple[Dict[str, Any], str | None]:
    """Returns what you send."""
    return {"echo": inp}, None


def tool_unstable(inp: Dict[str, Any]) -> tuple[Dict[str, Any], str | None]:
    """
    A deliberately flaky tool for testing retries/timeouts.

    Input options:
      - sleep_sec: float (default 0.2)
      - fail_prob: float in [0,1] (default 0.4)
    Behavior:
      - sleeps for sleep_sec
      - fails with probability fail_prob
    """
    sleep_sec = float(inp.get("sleep_sec", 0.2))
    fail_prob = float(inp.get("fail_prob", 0.4))

    time.sleep(sleep_sec)

    if random.random() < fail_prob:
        return {}, f"unstable tool failed (fail_prob={fail_prob})"

    return {"ok": True, "slept": sleep_sec, "fail_prob": fail_prob}, None


TOOLS: dict[str, ToolFn] = {
    "echo": tool_echo,
    "unstable": tool_unstable,
}


def get_tool(name: str) -> ToolFn | None:
    return TOOLS.get(name)