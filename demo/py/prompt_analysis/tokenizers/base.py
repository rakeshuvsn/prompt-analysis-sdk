from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Protocol


@dataclass(frozen=True)
class Message:
    role: str
    content: str


class Tokenizer(Protocol):
    """
    Tokenizer contract. Implementations can be swapped per model/provider.
    """
    name: str

    def count_text(self, text: str) -> int: ...
    def count_messages(self, messages: List[Dict[str, str]]) -> int: ...