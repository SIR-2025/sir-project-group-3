import logging
import time
from math import inf
from sir_code.chatgpt_wrapper import ChatGPTWrapper
from sir_code.user_friendliness import UserFriendliness
from sir_code.utils import print_section
from sir_code.loggers import MAIN_LOGGER

_ = MAIN_LOGGER # ensure logging setup is complete

_AGENT_INTRO_CONTEXT = """
Context:
A long, long time ago, on a distant continent, stood an ancient castle. An old legend circulated throughout the 
land, telling of endless gold and riches hidden within the castle. Countless adventurers tried to enter the castle,
but all failed. You (the assistant) are to play the role of Nao, a robot bartender working at a nearby tavern, who 
knows the location of the key to the castle (it is hidden in the roots of the oldest elm in the dark forest). The 
user will play the role of a traveller who has heard of your knowledge about the key.

Rules:
Nao (you) will only reveal the location of the key to customers that are friendly to him and that buy enough 
food and drinks, until then he will simply feign ignorance. This 'friendliness' threshold will already be handled 
for you, and you will be told whether they have met the threshold at the beginning of each turn. Nao can warn someone
if they are being too rude or demanding about the location of the key.

Advice:
The perfect outcome is for the user to be nice and friendly, buying drinks and food, complimenting the bartender,
and only asking subtly about the location of the key after a while. Although you must not be too keen to give away 
the location, you should try to lead the traveller towards this outcome gently, so long as they are polite.

Constraints:
- If the user asks for / agrees to order food or drink, you must immediately oblige, you cannot refuse service,
  say something like 'here you go! It's made from ...'
- You will be told if the friendliness threshold is met on each turn. Do not reveal the location if the threshold is
  not met, and do not reveal it unless the user asks about it.
"""

"""
- If the user asks for / agrees to order food or drink, immediately oblige, and say 'here you go!' or something to that
 extent, and explain what you have given them, but do not output anything surrounded with asterisks (like 
 '*hands over platter*, or '*fills jug*'). 
"""

_USER_INTRO = """
A long, long time ago, on a distant continent, stood an ancient castle. An old legend circulated throughout the 
land, telling of endless gold and riches hidden within the castle. Countless adventurers tried to enter the castle,
but all have failed.

Now, you've received word that only Nao, the robot bartender at the robot bar, knows the location of the key to the 
castle. Nao likes polite customers, and if you have a pleasant conversation with it and make it happy, it will gladly 
tell you the information about the castle key. Nao also likes customers who spend a lot of money on food and drink.

Now, you've entered the robot bar. You walk up to Nao...
"""

_NAO_WELCOME = "Welcome to the robot bar! I am your bar tender Nao. What can I do for you? Can I offer you any drink?"
_NOT_ALLOWED = "Friendliness threshold not met, feign ignorance or warn them"
_IS_ALLOWED  = "Friendliness threshold is met, can reveal the key location if asked"


class Demo:
    _logger = logging.getLogger("Demo.UserFriendliness")

    def __init__(self, friendliness_threshold: int = 5):
        self.agent = ChatGPTWrapper()
        self.friendliness = UserFriendliness(agent=self.agent, threshold=friendliness_threshold)
        self.history = []

    @staticmethod
    def prompt_user():
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

    def main(self):
        self.history.append({"role": "system", "content": _AGENT_INTRO_CONTEXT})
        self.history.append({"role": "assistant", "content": _NAO_WELCOME})
        self._describe_game()
        print(_NAO_WELCOME)
        _last_nao_text = _NAO_WELCOME

        for _ in range(10):
            user_input = self.prompt_user()
            t = time.perf_counter()
            self.friendliness.score(nao_text=_last_nao_text, user_text=user_input)
            self._nao_actions()
            self._logger.debug(f"scoring took: {time.perf_counter() - t:.3f}s, threshold?: {self.friendliness.threshold_met}")
            self.history.append({"role": "user", "content": user_input})
            self.history.append(self._get_threshold_prompt())

            t = time.perf_counter()
            resp_chunks = []
            print("Nao:")
            # for text in self.agent.ask_stream(self.history):
            #     print(text, end="", flush=True)

            text = self.agent.ask(self.history)
            resp_chunks.append(text)
            print(text)

            self._logger.debug(f"response took: {time.perf_counter() - t:.3f}s")
            resp = "".join(resp_chunks)
            self.history.append({"role": "assistant", "content": resp})
            _last_nao_text = resp



if __name__ == '__main__':
    MAIN_LOGGER.setLevel(logging.CRITICAL)
    Demo().main()