import logging
import re

from sir_code.lib import Agent
from sir_code.loggers import MAIN_LOGGER
from sir_code.utils import multiline_strip

_ = MAIN_LOGGER # ensure logging setup is complete


class Action:
    """
    Class for detecting the right actions matching current Nao response.
    There are 6 pre-recorded actions that we ask the agent to make, each is a boolean characterisation.
    """
    descriptions = {
        "A": "Nod your head",
        "B": "Lift one arm to your chest",
        "C": "Open one arm widely",
        "E": "Lift one arm to your chin, pointing to yourself",
        "F": "Place a hand over your heart, show respect",
        "G": "Gently tap your lips or temple to suggest secrecy or whispering",
    }

    _resp_regex = re.compile(r"^\s*([A-H])(?:\s*,\s*([A-H]))*\s*$")
    _logger = logging.getLogger("Demo.Action")
    _logger.setLevel(logging.CRITICAL)


    def __init__(self, agent: Agent):
        self._agent = agent
        self.current_actions = ""


    def generate_prompt(self, nao_text: str):
        options_text = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items())
        return multiline_strip(
            f"""
            The following text is a reply from you to a traveller in a tavern:
            you: "{nao_text}"
            
            Which of the following actions apply while speaking the text(can be multiple or none)? 
            Please answer with comma separated letters (e.g 'A,B'), or simply 'None' if none apply:
            {options_text}
            """
        )

    def detect(self, nao_text: str):
        prompt = self.generate_prompt(nao_text)
        resp = self._agent.ask([{"role": "user", "content": prompt}], max_output_tokens=16).strip().strip(".")

        if resp.lower() == "none":
            actions = ""
        else:
            assert self._resp_regex.match(resp), f"agent answer does not match regex: '{resp}'"
            actions = "".join(sorted(re.findall(r"[A-H]", resp)))
            assert len(actions) == len(set(actions)), f"agent answer has duplicate letters: '{resp}'"

        self.current_actions = actions

        given_resp = "\n".join(f"{k}) {v}" for k, v in self.descriptions.items() if k in actions)
        self._logger.debug(
            f"\nactions response: {resp}, "
            f"\ncurrent_actions: {self.current_actions},"
            f":\n{given_resp}"
        )
        return actions
