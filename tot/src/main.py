# --------------------------------------------
import enum

import codefast as cf
import pandas as pd
from codefast.utils import retry
# from rich import print

from .db import rdcli
from .gpt import chatgpt
from .prompts import cot_prompt, io_prompt


INFINITY = float('inf')


class PromptType(enum.Enum):
    IO = 'io'
    COT = 'cot'


def evaluate(response: str, prompt_type: PromptType = PromptType.IO) -> float:
    try:
        if prompt_type == PromptType.IO:
            expr = response.split('=')[0].strip()
        elif prompt_type == PromptType.COT:
            expr = response.split('Answer:')[1].split('=')[0].strip()
        return eval(expr)
    except:
        return INFINITY


def get_puzzles() -> list:
    csv_path = 'https://raw.githubusercontent.com/princeton-nlp/tree-of-thought-llm/master/src/tot/data/24/24.csv'
    df = pd.read_csv(csv_path)
    df = df[(df['Rank'] >= 901) & (df['Rank'] <= 1000)]
    puzzles = df['Puzzles'].tolist()
    return puzzles


@retry(3)
def solve(puzzles: list,
          prompt_template: str,
          redis_prefix: str = 'ioprompt',
          prompt_type: PromptType = PromptType.IO,
          ) -> tuple:
    """ Solve with prompting,
    :param puzzles: list of puzzles
    :param prompt_template: prompt template
    :param redis_prefix: redis prefix
    :param prompt_type: prompt type
    """
    correct, wrong = 0, 0
    for i, puzzle in enumerate(puzzles):
        key = '{}:{}'.format(redis_prefix, puzzle)
        if rdcli.exists(key):
            response = rdcli.get(key).decode()
            # rdcli.expire(key, 1)
            msg = {
                'input': puzzle,
                'response': response,
                'from': 'redis',
                'index': i
            }
        else:
            gpt = chatgpt()
            prompt_str = prompt_template.format(puzzle)
            response = gpt.get_response(prompt_str)
            rdcli.set(key, response, ex=86400)
            msg = {
                'input': puzzle,
                'response': response,
                'from': 'openai',
                'index': i
            }

        value = evaluate(response, prompt_type)
        if value == 24:
            correct += 1
        else:
            wrong += 1
        if value == INFINITY:
            rdcli.expire(key, 0)
        cf.info(msg)
    cf.info({
        'correct': correct,
        'wrong': wrong,
        'accuracy': correct / (correct + wrong)
    })
    return correct, wrong


def naive_solve(puzzles: list):
    return solve(puzzles,
                 prompt_template=io_prompt,
                 redis_prefix='ioprompt',
                 prompt_type=PromptType.IO)


def cot_solve(puzzles: list):
    return solve(puzzles,
                 prompt_template=cot_prompt,
                 redis_prefix='cotprompt',
                 prompt_type=PromptType.COT)


if __name__ == '__main__':
    puzzles = get_puzzles()
    cot_solve(puzzles)
