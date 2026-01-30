from __future__ import annotations

from typing import Any, Dict, List, Optional

from .rules.base import NormalizedPrompt


def normalize_messages(
    messages: List[Dict[str, str]],
    context_chunks: Optional[List[Dict[str, Any]]] = None,
) -> NormalizedPrompt:
    msgs = []
    for m in messages or []:
        role = (m.get("role") or "user").strip().lower()
        content = (m.get("content") or "").strip()
        msgs.append({"role": role, "content": content})

    context_text = ""
    if context_chunks:
        context_text = "\n\n".join(
            (c.get("text") or "").strip()
            for c in context_chunks
            if (c.get("text") or "").strip()
        ).strip()

    system_text = "\n".join(m["content"] for m in msgs if m["role"] == "system").strip()
    user_text = "\n".join(m["content"] for m in msgs if m["role"] == "user").strip()
    joined_text = "\n".join(m["content"] for m in msgs).strip()

    return NormalizedPrompt(
        messages=msgs,
        joined_text=joined_text,
        user_text=user_text,
        system_text=system_text,
        context_text=context_text,
    )