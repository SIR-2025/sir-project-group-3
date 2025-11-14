from pathlib import Path
from typing import List, Dict, Optional

from openai import OpenAI

from sir_code.lib import Agent


class ChatGPTWrapper(Agent):
    def __init__(self, model: str = "gpt-4o-mini"):
        key_file = Path(__file__).parent / "conf" / ".openai-key"
        assert key_file.exists(), f"OpenAI key not found, file '{key_file}' does not exist"
        self._client = OpenAI(api_key=key_file.read_text())
        self._model = model

    def ask(self, __input: List[Dict[str, str]], /, max_output_tokens: Optional[int] = None):
        kw = dict(model=self._model, input=__input, store=False)
        if max_output_tokens is not None:
            assert max_output_tokens > 0
            kw["max_output_tokens"] = max_output_tokens

        return self._client.responses.create(**kw).output_text

    def ask_stream(self, __input: List[Dict[str, str]], /, max_output_tokens: Optional[int] = None):
        kw = dict(model=self._model, input=__input, store=False, stream=True)
        if max_output_tokens is not None:
            assert max_output_tokens > 0
            kw["max_output_tokens"] = max_output_tokens
        stream = self._client.responses.create(**kw)
        for event in stream:
            if event.type == 'response.output_text.delta':
                yield event.delta


