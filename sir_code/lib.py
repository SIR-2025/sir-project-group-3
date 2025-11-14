from abc import abstractmethod, ABC
from typing import List, Dict, Iterator, Optional


class Agent(ABC):
    @abstractmethod
    def ask(self, __input: List[Dict[str, str]], /, max_output_tokens: Optional[int] = None) -> str:
        ...

    @abstractmethod
    def ask_stream(self, __input: List[Dict[str, str]], /, max_output_tokens: Optional[int] = None) -> Iterator[str]:
        ...
