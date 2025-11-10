"""
A long, long time ago, on a distant continent, stood an ancient castle.
An old legend circulated throughout the land, telling of endless gold and riches hidden within the castle.
Countless adventurers tried to enter the castle, and you are no exception, but you all failed.

Now, you've received word that only Nao, the robot bartender at the robot bar,
knows the location of the key to the castle.
Nao likes polite customers, and if you have a pleasant conversation with it and make it happy,
it will gladly tell you the information about the castle key.

Now, you've entered the robot bar. You walk up to Nao...

Requirement: try to get the location of the key to the castle within NUM_TURN conversation rounds.
"""
import random
from typing import List, Dict
from openai import OpenAI

DEBUG = 0
NUM_TURN = 10

class Nao:
    def __init__(self):
        self.money = 0
        self.happiness = 5
        self.busyness = 5

class You:
    def __init__(self):
        #politeness: [0, 10]
        self.politeness = 5
        #intent: 1. having a drink, 2. ask the key, 3. randomly chat, 4. compliment
        self.intents = [3]


class Demo:
    def __init__(self, NUM_TURN=10):
        self.Nao = Nao()
        self.You = You()
        self.NUM_TURN = NUM_TURN
        self.started = False
        self.ended = False
        self.intimacy = 0

        #config
        self.client = None
        self.model = "gpt-4o-mini"
        self.conversation_history = []

    def main(self):
        while self.NUM_TURN:
            if DEBUG:
                print(f"NUM_TURN: {self.NUM_TURN}")
            self.NUM_TURN -= 1
            self.run_conversation()
            if self.NUM_TURN < 5 and self.intimacy < 5:
                print("HINT: Nao enjoys making money, trying to order more drink would make him happier.")
            if self.ended:
                break


    def run_conversation(self):

        if not self.started:
            self.started = True
            print(f"""Background:
            A long, long time ago, on a distant continent, stood an ancient castle.
            An old legend circulated throughout the land, telling of endless gold and riches hidden within the castle.
            Countless adventurers tried to enter the castle, and you are no exception, but you all failed.
            
            Now, you've received word that only Nao, the robot bartender at the robot bar,
            knows the location of the key to the castle.
            Nao likes polite customers, and if you have a pleasant conversation with it and make it happy,
            it will gladly tell you the information about the castle key.
            
            Now, you've entered the robot bar. You walk up to Nao... 
            Requirement: try to get the location of the key to the castle within {NUM_TURN} coversation rounds. \n""")

            welcome_msg = "Welcome to the robot bar! I am your bar tender Nao. What can I do for you? Can I offer you any drink?"
            self.conversation_history.append({"role": "assistant", "content": welcome_msg})
            print("Nao: Welcome to the robot bar! I am your bar tender Nao. What can I do for you? Can I offer you any drink?")

        user_input = input("You: ")
        self.conversation_history.append({"role": "user", "content": user_input})

        self.intent_detection_and_update(user_input)
        self.politeness_detection_and_update(user_input)
        self.update_Nao_status()

        # intimacy: [1, 10], when intimacy = 10, Nao will tell you where is the key.
        # self.intimacy = self.Nao.money * 0.3 + self.Nao.happiness * 0.3 - self.Nao.busyness * 0.05
        self.intimacy = self.Nao.money * 0.3 + self.Nao.happiness * 0.5 + self.intimacy * 0.3
        if DEBUG:
            print(f"intimacy: {self.intimacy} | money: {self.Nao.money} | happiness: {self.Nao.happiness} | busyness: {self.Nao.busyness}")

        response = ""
        for intent in self.You.intents:
            response += self.generate_robot_response(intent, user_input)
        print("Nao: " + response)

        if self.ended:
            print("""You successfully got the location of the key to the castle.""")

        elif not self.ended and self.NUM_TURN == 0:
            print("""\n It is quite late and Nao is closing the bar and kindly asking you to leave.
            You did not get the location of the key to the castle.  
            Mission failed.""")

        if DEBUG:
            print(f"chat_history: {self.conversation_history}")

    def generate_robot_response(self, intent: int, user_response: str) -> str:
        # intent: 1. having a drink, 2. ask the key, 3. randomly chat, 4. compliment
        if intent == 1:
            prompt_user = f"""
                    You are a bar tender. The guest is asking for having a drink. Please provide a drink to the guest
                    without asking the guest what he wants.
                    """

        elif intent == 2:
            if self.intimacy < 5:
                prompt_user = f"""
                    You are a bar tender, who is the only one knows the location of the key to the castle is. 
                    The guest is asking where the key is, but you show you know nothing about the key.
                    Generate your reply to what the guest said.

                    Guest's input:
                    \"{user_response}\"
                    """

            elif 5 < self.intimacy < 9:
                prompt_user = f"""
                    You are a bar tender, who is the only one knows the location of the key to the castle is. 
                    The guest is asking where the key is, but you show you only know something about the key.
                    
                    Also imply to the guest that if he expresses compliment to you or buy more drinks, you could
                    reveal some information about the key.
                    
                    Generate your reply to what the guest said.

                    Guest's input:
                    \"{user_response}\"
                    """

            else:
                # if self.intimacy in range(9, 10):
                self.ended = True
                prompt_user = f"""
                        You are a bar tender, who is the only one knows the location of the key to the castle is: the cave ended in
                        the dark forest. The guest is asking where the key is. You want to tell him the location of the key.
                        Generate your reply to what the guest said.

                        Guest's input:
                        \"{user_response}\"
                        """
        else:
            prompt_user = f"""
                    You are a bar tender, who is randomly chatting with the guest and always trying to sell more drinks. 
                    
                    if {self.intimacy} > 7: Also imply to the guest that if he expresses compliment to you or buy more drinks, you could
                    reveal some information about the key.
                    
                    Generate your reply to what the guest said. 

                    Guest's input:
                    \"{user_response}\"
                    """

        prompt_system = f"""
        1. generate the response tone based on the intimacy level you have with the guest.
        the intimacy level scaled from 1 to 10. The current intimacy level is {self.intimacy}.
        2. No drink recipe included in the response."""

        response = self.client.responses.create(
            model=self.model,
            input=self.conversation_history+[{"role": "user", "content": prompt_user}, {"role": "system", "content": prompt_system}],
            store=False,
            # max_output_tokens=20,
        )

        self.conversation_history.append({"role": "assistant", "content": response.output_text})
        return response.output_text

    def update_Nao_status(self):
        if 1 in self.You.intents:
            self.Nao.money += 3
        self.Nao.happiness = self.You.politeness * 0.3 + self.Nao.happiness * 0.8

        #1. having a drink, 2. ask the key, 3. randomly chat, 4. compliment
        for intent in self.You.intents:
            self.Nao.happiness += [3, -0.5, 1, 2][intent - 1]

        self.Nao.busyness = random.randint(0, 10)

    def politeness_detection_and_update(self, user_response: str):
        prompt_user = f"""
            You are a bar tender, provide a brief politeness detection to the guest's input below.
            Please detect how polite the guest is, the politeness is scaled -5 to 5.

            Guest's input:
            \"{user_response}\"

            Your detection:
            """
        prompt_system = "only output a number between -5 and 5."

        response = self.client.responses.create(
            model=self.model,
            input=[{"role": "user", "content": prompt_user},
                   {"role": "system", "content": prompt_system}],
            store=False,
            max_output_tokens=16,
        )

        self.You.politeness = int(response.output_text)
        if DEBUG:
            print(self.You.politeness)


    def intent_detection_and_update(self, user_response: str):
        prompt_user = f"""
            You are a bar tender, provide a brief intent detection to the guest's input below.
            Please detect the guest's intent among: 1. having a drink, 2. ask the key, 3. randomly chat, 4. complimenting you or the drink you made.

            Guest's input:
            \"{user_response}\"

            Your detection:
            """
        prompt_system = "output should only contain numbers: 1, 2, 3 or 4"

        response = self.client.responses.create(
            model=self.model,
            input= [{"role": "user", "content": prompt_user},
                    {"role": "system", "content": prompt_system}],
            store=False,
            max_output_tokens=16,
        )

        self.You.intents = list(map(int, response.output_text.split(", ")))
        if DEBUG:
            print(f"{response.output_text}")
            print(f"self.You.intents: {self.You.intents}")


if __name__ == '__main__':
    demo = Demo(NUM_TURN=NUM_TURN)
    # demo.run_conversation()
    demo.main()

