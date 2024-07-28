from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Response:
    message: str
    options: Optional[List[str]] = None
