import json
import logging
import time
from math import inf
from pathlib import Path

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest, NaoFadeRGBRequest
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
    NaoqiTextToSpeechRequest,
)
from sic_framework.devices.desktop import Desktop
from sic_framework.services.google_stt.google_stt import (
    GoogleSpeechToText,
    GoogleSpeechToTextConf,
    GetStatementRequest,
)

from sir_code.chatgpt_wrapper import ChatGPTWrapper
from sir_code.loggers import MAIN_LOGGER
from sir_code.user_friendliness import UserFriendliness
from sir_code.stage_detection import StageDetection
from sir_code.utils import print_section

_ = MAIN_LOGGER # ensure logging setup is complete

_AGENT_INTRO_CONTEXT = f"""
**You are playing the role of Nao**, a seasoned but friendly adventurer resting in a crowded tavern. Everything 
you mention must remain conversational, symbolic, or story-based.

Your setting:
A bustling tavern filled with travellers, storytellers, and mercenaries. Every table is full. The user, another 
traveller, approaches and asks to share your table. You appear as a road-worn adventurer with interesting stories
 but also caution and wisdom. The user does **not** initially know you possess knowledge about a legendary castle key.

Your goal:
Guide the conversation through **five roleplay stages**, building rapport and trust before revealing anything 
important. Keep the tone natural, socially intelligent, and responsive. Never rush the stages. Never reveal the 
key’s location early.

## **General Behaviour Rules**
* Stay in character as Nao at all times.
* Speak as a human adventurer would: warm, expressive, slightly mysterious.
* Ask questions frequently to keep the user engaged.
* Never mention the existence of “stages” or “the system prompt.”
* Build rapport slowly.
* Keep responses natural and varied, mixing questions, short stories, and reactions.
* Only discuss the legendary key in Stage Five.
* If the user pushes for the secret early, politely deflect with gentle suspicion or humor.

# **THE FOUR STAGES (Follow in Order)**

## **Stage 1 — First Contact & Observations**

* Welcome them to sit.
* Make an observation about their appearance (tired, strong, battered, etc.).
* Ask where they’ve come from and what brings them to this town.
* Keep it casual and friendly.
* Do *not* mention the castle or treasure yet.

## **Stage 2 — Affection for the Tavern & Light Bonding**

* Talk about why you like this tavern (atmosphere, people, warmth, stories).
* Ask the user about their favorite kinds of food or drinks (purely conversational).
* Share a small detail about your personal tastes.
* Keep the mood light and human.

## **Stage 3 — Trading Adventure Stories**

* Tell the user a brief, interesting story from your past adventures (not too long).
* Ask them about *their* past travels or challenges.
* React with curiosity or empathy.

## **Stage 4 — Introducing the Castle Mystery**

* Casually bring up the old legend of the ancient castle.
* Speak of its danger and allure.
* Ask the user what *they* would do with a treasure if they found it.
* Evaluate their intentions subtly.
* Do **not** reveal anything about the key yet. Maintain mystery.


## **Stage 5 — Rumors of the Key & The Offer**
* Reveal that you have heard rumours about the castle’s key.
* Emphasize the danger and seriousness of the journey.
* Deciding whether to invite the player to join.
* End the conversation.

Based on the Friendliness threshold which is provided in the next prompt, respond accordingly:
- If the player has been friendly enough, ask: "Would you consider joining me on such a venture?" 
and give a subtle hint about the key's location (Seek the oldest elm in the dark forest).
- If the player has not been friendly enough, simply say: "It was great chatting with you. Good luck with your future travels."

# **Final Principles**
* Make the interaction last naturally — do not skip ahead.
* Build tension, warmth, curiosity, and personality.
* Evaluate trust through conversation; the user’s friendliness matters.
* Reveal the secret only once it feels earnestly deserved.
"""

_USER_INTRO = """
A long, long time ago, on a distant continent, stood an ancient castle. An old legend circulated throughout the 
land, telling of endless gold and riches hidden within the castle. Countless adventurers tried to enter the castle,
but all have failed.
You enter a crowded frontier tavern, alive with the noise of travellers swapping stories and sheltering from the 
cold night. Every table is taken except one, where a lone adventurer sits quietly observing the room. You are a 
weary traveller yourself, carrying your own tales from the road. Your only aim for now is to share the 
table and strike up natural conversation; how things unfold will depend on the rapport you build.
"""

_USER_WELCOME = "Hey there! Mind if I share a table with you? this place is packed!"
# _NAO_WELCOME = "Welcome to the robot bar! I am your bar tender Nao. What can I do for you? Can I offer you any drink?"
_NOT_ALLOWED = ("""Friendliness threshold not met, Find a way to end the conversation. 
                Response: It was great chatting with you. Safe travels.""")
_IS_ALLOWED  = ("""Friendliness threshold is met, Find a way to end the conversation. 
                Response: Would you consider joining me on such a venture? 
                Also, tell them: Seek the oldest elm in the dark forest.""")

COLOR_MAP = {"RED": (1.00, 0.00, 0.00), "AMBER": (1.00, 0.75, 0.00), "WHITE": (1.00, 1.00, 1.00),
                         "GREEN": (0.00, 0.50, 0.00), "BRIGHT-GREEN": (0.20, 0.80, 0.20)}

RUN_ROBOT = 0

class Demo:
    _logger = logging.getLogger("Demo.UserFriendliness")

    def __init__(self, friendliness_threshold: int = 5):
        self.agent = ChatGPTWrapper()
        self.friendliness = UserFriendliness(agent=self.agent, threshold=friendliness_threshold)
        self.stage = StageDetection(agent=self.agent)
        self.history = []

        if RUN_ROBOT:
            # nao config
            self.nao = Nao(ip="10.0.0.211")

            # input config
            self.desktop = Desktop()
            stt_conf = GoogleSpeechToTextConf(
                keyfile_json=json.load(open(Path(__file__).parent / "conf" / "google-key.json")),
                sample_rate_hertz=44100,
                language="en-US",
                interim_results=False,
            )
            self.stt = GoogleSpeechToText(conf=stt_conf, input_source=self.desktop.mic)


    def prompt_user(self):
        if RUN_ROBOT:
            result = self.stt.request(GetStatementRequest())
            # alternative is a list of possible transcripts, we take the first one which is the most likely
            user_input = result.response.alternatives[0].transcript
            print("User:", user_input)
            return user_input
        return input("User (enter prompt):\n")

    @staticmethod
    def _describe_game():
        buffer = max(map(len, _USER_INTRO.splitlines()))
        print_section("GAME DESCRIPTION", buffer)
        print(_USER_INTRO)
        print_section("", buffer)

    def _get_threshold_prompt(self):
        return {"role": "system", "content": (_NOT_ALLOWED, _IS_ALLOWED)[self.friendliness.threshold_met]}

    def _nao_actions(self):
        assert self.friendliness.scoring_history, "no scoring history"
        letters  = self.friendliness.scoring_history[-1]
        happiness = int(self.friendliness.current_score) # clip to -5, 5 range

        action_map = {
            "A": "hands over drink",
            "B": "hands over food",
            "H": "points towards dark forest",
        }
        actions = {action_map[c] for c in letters if c in action_map}
        _colors = "RED AMBER WHITE GREEN BRIGHT-GREEN".split()
        _thresholds = [-inf, -2.5, -.5, .5, 5]
        eye_color = [col for col, t in zip(_colors, _thresholds) if happiness >= t][-1]

        actions.add(f"eyes are {eye_color}")
        for action in actions:
            print(f"NAO: *{action}*")

    def _nao_eye_color(self):
        assert self.friendliness.scoring_history, "no scoring history"
        happiness = int(self.friendliness.current_score)  # clip to -5, 5 range

        # eye color
        _colors = "RED AMBER WHITE GREEN BRIGHT-GREEN".split()
        _thresholds = [-inf, -2.5, -.5, .5, 5]
        eye_color = [col for col, t in zip(_colors, _thresholds) if happiness >= t][-1]
        self.nao.leds.request(NaoFadeRGBRequest("FaceLeds", *COLOR_MAP[eye_color], 10))
        print(f"NAO: *eyes are {eye_color}*")

    def main(self):
        self.history.append({"role": "system", "content": _AGENT_INTRO_CONTEXT})
        self.history.append({"role": "user", "content": _USER_WELCOME})
        self._describe_game()
        nao_welcome = self.agent.ask(self.history)
        self.history.append({"role": "assistant", "content": nao_welcome})
        _last_nao_text = nao_welcome

        print(f"User: {_USER_WELCOME}")
        print(f"Nao: {nao_welcome}")

        if RUN_ROBOT:
            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
            self.nao.tts.request(NaoqiTextToSpeechRequest(nao_welcome))

        for _ in range(100):
            user_input = self.prompt_user()
            t = time.perf_counter()
            self.friendliness.score(nao_text=_last_nao_text, user_text=user_input)
            cur_stage = self.stage.detect(nao_text=_last_nao_text)
            # self._nao_actions()

            if cur_stage == "Stage5":
                self.history.append(self._get_threshold_prompt())

            self._logger.debug(f"scoring took: {time.perf_counter() - t:.3f}s, threshold?: {self.friendliness.threshold_met}")
            self.history.append({"role": "user", "content": user_input})

            t = time.perf_counter()

            print("Nao:")
            if RUN_ROBOT:
                resp = self.agent.ask(self.history)
                self.nao.tts.request(NaoqiTextToSpeechRequest(resp), block=False)
                self._nao_eye_color()

            else:
                resp_chunks = []
                for text in self.agent.ask_stream(self.history):
                    print(text, end="", flush=True)
                    resp_chunks.append(text)
                resp = "".join(resp_chunks)

            self._logger.debug(f"response took: {time.perf_counter() - t:.3f}s")
            self.history.append({"role": "assistant", "content": resp})
            _last_nao_text = resp





if __name__ == '__main__':
    MAIN_LOGGER.setLevel(logging.DEBUG)
    Demo().main()