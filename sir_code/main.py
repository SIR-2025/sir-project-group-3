import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor as TPool
from math import inf
from pathlib import Path

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest, NaoFadeRGBRequest
from sic_framework.devices.common_naoqi.naoqi_motion_recorder import NaoqiMotionRecording, PlayRecording
from sic_framework.devices.common_naoqi.naoqi_stiffness import Stiffness
from sic_framework.devices.common_naoqi.naoqi_text_to_speech import (
    NaoqiTextToSpeechRequest,
)
from sic_framework.devices.desktop import Desktop
from sic_framework.services.google_stt.google_stt import (
    GoogleSpeechToText,
    GoogleSpeechToTextConf,
    GetStatementRequest,
)

from sir_code.action import Action
from sir_code.chatgpt_wrapper import ChatGPTWrapper
from sir_code.loggers import MAIN_LOGGER
from sir_code.stage_detection import StageDetection
from sir_code.user_friendliness import UserFriendliness
from sir_code.utils import print_section
from sir_code.saver import Saver

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
_NOT_ALLOWED = ("""Friendliness threshold not met, Find a way to end the conversation. 
                Response: It was great chatting with you. Safe travels.""")
_IS_ALLOWED  = ("""Friendliness threshold is met, Find a way to end the conversation. 
                Response: Would you consider joining me on such a venture? 
                Also, tell them: Seek the oldest elm in the dark forest.""")

_DYNAMIC_SPEECH = """
Generate dialogue **for a NAO robot** using its TTS control tags to create natural, expressive speech.

## **TTS TAGS**

**Pitch:** \\vct=value\\

* Range: **50–100**
* Slight upward pitch for questions; slight variations for expressiveness.

**Speaking rate:** \\rspd=value\\

* Range: **50–400**
* Slow for emphasis; slightly faster for enthusiasm or light energy.

**Pause:** \\pau=value\\

* Value = milliseconds
* Short pauses for breathing; longer for dramatic effect.

**Volume:** \\vol=value\\

* Range: **80-100**
* Small changes only; softer for calm moments.

**Reset:** \\rst\\

* Returns all settings to default when needed.

---

## **STYLE GUIDELINES**

* Aim for **natural conversational flow**, not robotic monotony.
* Vary pitch, speed, and volume **subtly**.
* Add pauses (100–1000 ms) to simulate breathing, thinking, or transitions.
* Use slight pitch lifts at the end of questions.
* Use volume or speed changes only for emphasis.* Output text should be have tags intact.
* **It is extremely important that all TTS tags ALWAYS use double backslashes before and after, exactly like this: \\tag=value\\**
* Always remember to add \\rst\\ where the effect should end.

---

## **EXAMPLE SENTENCE**

I’ll start softly \\vol=40\\like this.\\rst\\ Now I’ll slow down \\rspd=70\\for a moment.\\rst\\ Then I’ll raise my pitch \\vct=150\\right here?\\rst\\ \\pau=600\\And now we continue.

"""

COLOR_MAP = {"RED": (1.00, 0.00, 0.00), "AMBER": (1.00, 0.75, 0.00), "WHITE": (1.00, 1.00, 1.00),
                         "GREEN": (0.00, 0.50, 0.00), "BRIGHT-GREEN": (0.20, 0.80, 0.20)}

RUN_ROBOT = 1

class Demo:
    _logger = logging.getLogger("Demo.main")

    def __init__(self, friendliness_threshold: int = 0):
        self.agent = ChatGPTWrapper()
        self.friendliness = UserFriendliness(agent=self.agent, threshold=friendliness_threshold)
        self.stage = StageDetection(agent=self.agent)
        self.actions = Action(agent=self.agent)
        self.history = []
        self.audio_speed = 90
        self.audio_pitch = 85
        self.saver = Saver("claire.csv")

        if RUN_ROBOT:
            # nao config
            self.nao = Nao(ip="192.168.0.231")
            # input config
            self.desktop = Desktop()
            stt_conf = GoogleSpeechToTextConf(
                keyfile_json=json.load(open(Path(__file__).parent / "conf" / "google-key.json")),
                sample_rate_hertz=44100,
                language="en-US",
                interim_results=False,
            )
            self.stt = GoogleSpeechToText(conf=stt_conf, input_source=self.desktop.mic)

            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
            self.nao.stiffness.request(Stiffness(stiffness=0.3, joints="Body".split()))


    def prompt_user_audio(self):
        input("\nUser speak:\n")
        result = self.stt.request(GetStatementRequest())
        # alternative is a list of possible transcripts, we take the first one which is the most likely
        user_input = result.response.alternatives[0].transcript
        print(f"User: {user_input}\n")
        return user_input

    @staticmethod
    def prompt_user():
        return input("\nUser (enter prompt):\n")

    @staticmethod
    def _describe_game():
        buffer = max(map(len, _USER_INTRO.splitlines()))
        print_section("GAME DESCRIPTION", buffer)
        print(_USER_INTRO)
        print_section("", buffer)

    def _get_threshold_prompt(self):
        return {"role": "system", "content": (_NOT_ALLOWED, _IS_ALLOWED)[self.friendliness.threshold_met]}

    def _nao_actions(self, actions):
        for action in actions:
            self._logger.debug(
            f"\ncurrent_action: {action},"
            )
            self.nao.motion_record.request(PlayRecording(NaoqiMotionRecording.load(f"actions/{action}.motion")))

    def _nao_action_and_eye_color(self, actions):
        happiness = int(self.friendliness.current_score)  # clip to -5, 5 range

        # eye color
        _colors = "RED AMBER WHITE GREEN BRIGHT-GREEN".split()
        _thresholds = [-inf, -2.5, -.5, .5, 5]
        eye_color = [col for col, t in zip(_colors, _thresholds) if happiness >= t][-1]
        print(f"NAO: *eyes are {eye_color}*")
        with TPool(max_workers=2) as executor:
            for action in actions:
                self._logger.debug(
                    f"\ncurrent_action: {action},"
                    f"\ncurrent_time: {time.perf_counter()},"
                )
                executor.submit(self.nao.motion_record.request, PlayRecording(NaoqiMotionRecording.load(f"actions/{action}.motion")))

            self._logger.debug(
                f"\neye_color started time: {time.perf_counter()},"
            )
            executor.submit(self.nao.leds.request, NaoFadeRGBRequest("FaceLeds", *COLOR_MAP[eye_color], 10))
            self._logger.debug(
                f"\neye_color finished time: {time.perf_counter()},"
            )

    def main(self):
        self.history.append({"role": "system", "content": _AGENT_INTRO_CONTEXT})
        self.history.append({"role": "user", "content": _USER_WELCOME})
        self._describe_game()

        if RUN_ROBOT:
            self.history.append({"role": "system", "content": _DYNAMIC_SPEECH})
            nao_welcome = self.agent.ask(self.history)
            self.history.pop()

            self.prompt_user_audio()

            print(f"Nao: {nao_welcome}")
            actions = self.actions.detect(nao_text=nao_welcome)
            self.nao.tts.request(NaoqiTextToSpeechRequest(nao_welcome, speed=self.audio_speed,
                                pitch=self.audio_pitch), block=False)
            self._nao_action_and_eye_color(actions)
        else:
            nao_welcome = self.agent.ask(self.history)
            print(f"User: {_USER_WELCOME}")
            print(f"Nao: {nao_welcome}")

        self.history.append({"role": "assistant", "content": nao_welcome})
        _last_nao_text = nao_welcome
        self.saver.update(_USER_WELCOME, nao_welcome)

        for _ in range(100):
            if RUN_ROBOT:
                user_input = self.prompt_user_audio()
            else:
                user_input = self.prompt_user()

            t = time.perf_counter()
            self.friendliness.score(nao_text=_last_nao_text, user_text=user_input)
            last_stage = self.stage.detect(nao_text=_last_nao_text)

            if last_stage == "Stage5":
                self.history.append(self._get_threshold_prompt())

            self._logger.debug(f"friendliness scoring and stage detection took: {time.perf_counter() - t:.3f}s, "
                               f"threshold?: {self.friendliness.threshold_met}")
            self.history.append({"role": "user", "content": user_input})

            print("Nao:")
            t = time.perf_counter()
            if RUN_ROBOT:
                self.history.append({"role": "system", "content": _DYNAMIC_SPEECH})
                resp = self.agent.ask(self.history)
                self.history.pop()
                print(resp)
                actions = self.actions.detect(nao_text=resp)
                self.nao.tts.request(NaoqiTextToSpeechRequest(resp, speed=self.audio_speed,
                                    pitch=self.audio_pitch), block=False)
                self._nao_action_and_eye_color(actions)
            else:
                resp_chunks = []
                for text in self.agent.ask_stream(self.history):
                    print(text, end="", flush=True)
                    resp_chunks.append(text)
                resp = "".join(resp_chunks)
                self.actions.detect(nao_text=resp)
                self.saver.update(user_input, resp, self.friendliness.scoring_history[-1], time.perf_counter() - t)
                self.saver.save()

            if last_stage == "Stage5":
                break

            self._logger.debug(f"response and actions took: {time.perf_counter() - t:.3f}s")
            self.history.append({"role": "assistant", "content": resp})
            _last_nao_text = resp

if __name__ == '__main__':
    MAIN_LOGGER.setLevel(logging.DEBUG)
    Demo().main()