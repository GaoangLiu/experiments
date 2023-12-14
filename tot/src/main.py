# --------------------------------------------
import enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import codefast as cf
import pandas as pd
from codefast.utils import retry

from .db import rdcli
from .gpt import gpt
from .prompts import (cot_prompt, io_prompt, propose_prompt,
                      value_last_step_prompt, value_prompt)

# from rich import print

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
def solve(
    puzzles: list,
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
            prompt_str = prompt_template.format(puzzle)
            response = gpt(prompt_str)
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


class PuzzleSolver(object):
    pass


def get_lefts(s: str) -> str:
    # 4 * 5 = 20 (left: 20 6 10) -> 20 6 10
    lefts = s.split('left: ')[-1].split(')')[0]
    return lefts


class ToTSolver(PuzzleSolver):
    def __init__(self, puzzle: str, steps: int, sample_size: int = 1):
        super().__init__()
        self.steps = steps
        self.sample_size = sample_size
        self.states = [puzzle]
        self.score_map = {'sure': 10, 'likely': 5, 'impossible': 1}

    def step_forward(self):
        new_states = []
        for s in self.states:
            s_new = get_lefts(s)
            if s_new == '24':  # The last step
                xs = s.split('\n')
                input_s = cot_prompt.format(xs[0]).rstrip()
                prompt_str = '\n'.join([input_s, 'Steps:'] + xs[1:])
                response = gpt(prompt_str)
                new_states.append(s + '\n' + response)
            else:
                prompt_str = propose_prompt.format(s_new)
                response = gpt(prompt_str)
                for r in response.split('\n'):
                    new_states.append(s + '\n' + r)
        return new_states

    def score(self, states: List[str], step: int) -> List[float]:
        for s in states:
            if 'answer' in s.lower():
                input_s = s.split('\n')[0]
                answer_s = s.split('\n')[-1].lower().replace('answer: ', '')
                prompt_str = value_last_step_prompt.format(input_s, answer_s)
                response = gpt(prompt_str)
                cf.info({'numbers': input_s, 'response': response})
                value_str = response.split('\n')[-1].lower()
                score = self.score_map.get(value_str, 0)
                yield score
            else:
                s_ = get_lefts(s)
                len_s = len(s_.split(' '))
                if len_s + step + 1 != 4:
                    yield 0  # Get rid of hallucination steps
                else:
                    prompt_str = value_prompt.format(s_)
                    response = gpt(prompt_str)
                    cf.info({'numbers': s_, 'response': response})
                    value_str = response.split('\n')[-1].lower()
                    score = self.score_map.get(value_str, 0)
                    yield score

    def solve(self):
        for step in range(self.steps):
            cf.info(f'At step {step}')
            new_states = self.step_forward()
            scores = list(self.score(new_states, step))
            pairs = list(zip(new_states, scores))
            pairs.sort(key=lambda x: x[1], reverse=True)
            self.states = [_[0] for _ in pairs[:self.sample_size]]
            print(self.states)
            print(pairs)


def tot_solve(puzzles: list):
    pass


if __name__ == '__main__':
    puzzles = get_puzzles()
    # cot_solve(puzzles)
    puzzle = '4 5 6 10\n10 - 4 = 6 (left: 5 6 6)\n5 * 6 = 30 (left: 30 6)\n30 - 6 = 24 (left: 24)'
    totsolver = ToTSolver(puzzle, 1)
    totsolver.solve()
