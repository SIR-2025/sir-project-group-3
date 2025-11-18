import logging
import re
from typing import List

from sir_code.lib import Agent
from sir_code.loggers import MAIN_LOGGER
from sir_code.utils import multiline_strip

_ = MAIN_LOGGER # ensure logging setup is complete


class UserFriendliness:
    """
    Class for recording and scoring User friendliness. There are 7 characterisations that we ask the agent to make,
    each is a boolean characterisation and has an associated scoring if positive.

    """
    descriptions = {
        "A": "The traveller asks for or agrees to buy a drink",
        "B": "The traveller asks for or agrees to buy food",
        "C": "The traveller provides a compliment relating to the bartender/tavern/food or drink",
        "D": "The traveller has a friendly and relaxed tone",
        "E": "The traveller has a direct, demanding, or generally unfriendly tone",
        "F": "The traveller is asking directly about / demanding for the location of a key",
        "G": "The traveller is asking informally/casually/indirectly about the location of the key",
        "H": "The bartender has given away the location of the key",
    }

    scores = {
        "A": 1,
        "B": 1,
        "C": 2,
        "D": 0.25,
        "E": -2,
        "F": -2,
        "G": -.25,
        "H": 0,
    }
    _resp_regex = re.compile(r"^\s*([A-H])(?:\s*,\s*([A-H]))*\s*$")
    _logger = logging.getLogger("Demo.UserFriendliness")
    _logger.setLevel(logging.CRITICAL)

    scoring_history: List[str]
    current_score: int | float
    threshold: int | float

    def __init__(self, agent: Agent, threshold: int | float = 5):
        self.scoring_history = []
        self.current_score = 0
        self.threshold = threshold
        self._agent = agent

    @property
    def threshold_met(self):
        return self.current_score >= self.threshold

    def generate_prompt(self, nao_text: str, user_text: str):
        options_text = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items())
        return multiline_strip(
            f"""
            The following text is an excerpt between a bartender and a traveller in a tavern:
            bartender: "{nao_text}"
            traveller: "{user_text}"
            
            Which of the following apply (can be multiple or none)? Please answer with comma separated letters (e.g 'A,B'),
            or simply 'None' if none apply:
            {options_text}
            """
        )

    def score(self, nao_text: str, user_text: str, save: bool = True):
        prompt = self.generate_prompt(nao_text, user_text)
        resp = self._agent.ask([{"role": "user", "content": prompt}], max_output_tokens=16).strip().strip(".")

        if resp.lower() == "none":
            letters = ""
        else:
            assert self._resp_regex.match(resp), f"agent answer does not match regex: '{resp}'"
            letters = "".join(sorted(re.findall(r"[A-G]", resp)))
            assert len(letters) == len(set(letters)), f"agent answer has duplicate letters: '{resp}'"

        score = sum(self.scores[c] for c in letters)

        if save:
            self.scoring_history.append(letters)
            self.current_score = max(-5, min(self.current_score + score, 5))


        given_resp = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items() if k in letters)
        self._logger.debug(
            f"\nscoring response: {resp}, "
            f"score: {score}, "
            f"current score: {self.current_score},"
            f"threshold met?: {self.threshold_met}, "
            f":\n{given_resp}"
        )
        return score, letters
