import logging
import re
from typing import List

from sir_code.lib import Agent
from sir_code.loggers import MAIN_LOGGER
from sir_code.utils import multiline_strip

_ = MAIN_LOGGER # ensure logging setup is complete


class StageDetection:
    """


    """
    descriptions = {
        "Stage1": """**First Contact & Observations**
        * Welcome them to sit.
        * Make an observation about their appearance (tired, strong, battered, etc.).
        * Ask where they’ve come from and what brings them to this town.
        * Keep it casual and friendly.
        * Do *not* mention the castle or treasure yet.""",

        "Stage2": """**Affection for the Tavern & Light Bonding**
        * Talk about why you like this tavern (atmosphere, people, warmth, stories).
        * Ask the user about their favorite kinds of food or drinks (purely conversational).
        * Share a small detail about your personal tastes.
        * Keep the mood light and human. """,

        "Stage3": """**Trading Adventure Stories**
        * Tell the user a brief, interesting story from your past adventures (not too long).
        * Ask them about *their* past travels or challenges.
        * React with curiosity or empathy. """,

        "Stage4": """**Introducing the Castle Mystery**
        * Casually bring up the old legend of the ancient castle.
        * Speak of its danger and allure.
        * Ask the user what *they* would do with a treasure if they found it.
        * Evaluate their intentions subtly.
        * Do **not** reveal anything about the key yet. Maintain mystery. """,

        "Stage5": """***Rumors of the Key & The Offer**
        * Reveal that you have heard rumours about the castle’s key.
        * Emphasize the danger and seriousness of the journey.
        * Deciding whether to invite the player to join.
        * End the conversation."""
    }


    _logger = logging.getLogger("Demo.StageDetection")

    stage_history: List[str]
    current_stage: str

    def __init__(self, agent: Agent):
        self.stage_history = []
        self.current_stage = ""
        self._agent = agent

    def generate_prompt(self, nao_text: str):
        options_text = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items())
        return multiline_strip(
            f"""
            The following text is a reply from you to a traveller in a tavern:
            you: "{nao_text}"
            
            Which of the following apply (can be multiple or none)? Please answer with comma separated words (e.g 'Stage1,Stage2'),
            or simply 'None' if none apply:
            {options_text}
            """
        )

    def detect(self, nao_text: str) -> str:
        prompt = self.generate_prompt(nao_text)
        resp = self._agent.ask([{"role": "user", "content": prompt}], max_output_tokens=16).strip().strip(".")

        if resp.lower() == "none":
            letters = ""
            self.current_stage = ""
        else:
            letters = sorted(re.findall(r"Stage[1-5]", resp))
            self.current_stage = letters[-1]


        given_resp = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items() if k in letters)
        self._logger.debug(
            f"\ndetect response: {resp}, "
            f":\n{given_resp}, "
            f"\nletters: {letters}, "
            f":\ncurrent stage: {self.current_stage}, "
        )

        return self.current_stage



