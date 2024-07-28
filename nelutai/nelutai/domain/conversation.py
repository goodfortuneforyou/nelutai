import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from .enums import State


@dataclass(kw_only=True)
class Conversation:
    state: State
    start: Optional[datetime]
    location: Optional[str]
    category: Optional[str]
    message_ids: List[str]
    message_history: List[Tuple[str, str]]
    user_id: str

    def reset(self):
        self.state = State.WELCOME
        self.message_history = []
        self.start = datetime.now(timezone.utc)

    def to_json(self) -> str:
        return json.dumps(self.__dict__, default=str)

    def from_json(encoded: str | bytes) -> 'Conversation':
        parsed = json.loads(encoded)
        parsed['state'] = State(parsed['state'])
        return Conversation(**parsed)
