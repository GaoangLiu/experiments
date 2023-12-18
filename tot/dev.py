from src.main import get_puzzles, ToTSolver
from src.gpt import gpt
import os 

if __name__ == '__main__':
    print(
        gpt('Translate the following content into Chinese \
            `is it possible to reach 24 with 8 2 6, if each number can be used only once? Please answer carefully, it is important to me. \
                As the TV landscape continues to fracture, one new show emerged as a bona fide phenomenon: “The Last of Us,” HBO’s stunningly heartfelt zombie apocalypse thriller. Given that its source material was a beloved, acclaimed 2013 video game that has sold over 20 million copies, the bar was extraordinarily high. The show’s debut season delivered, in large part because of the synergy between the duo at its center: Pedro Pascal as Joel and Bella Ramsey as Ellie, two characters who find themselves on a cross-country quest, dodging reanimated corpses to (hopefully) save the world.')
    )
