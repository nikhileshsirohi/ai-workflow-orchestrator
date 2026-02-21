from __future__ import annotations

from typing import Any, Callable, Dict, Tuple


# Tool function signature:
#   tool(input: dict) -> (output: dict, error: str|None)
ToolFn = Callable[[Dict[str, Any]], Tuple[Dict[str, Any], str | None]]


def tool_echo(inp: Dict[str, Any]) -> tuple[Dict[str, Any], str | None]:
    """
    Simple starter tool: returns what you send.
    We'll replace/add tools later (summarize, report, etc.)
    """
    return {"echo": inp}, None


TOOLS: dict[str, ToolFn] = {
    "echo": tool_echo,
}


def get_tool(name: str) -> ToolFn | None:
    return TOOLS.get(name)