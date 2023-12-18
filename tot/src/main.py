# --------------------------------------------
import enum
import re
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


def get_puzzles(start_index: int, end_index: int) -> list:
    csv_path = 'data/24.csv'
    df = pd.read_csv(csv_path)
    df = df[(df['Rank'] >= start_index) & (df['Rank'] <= end_index)]
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

        final_state = self.states[0]
        if 'answer' not in final_state.lower():
            return 0
        else:
            answer_s = final_state.split('\n')[-1].lower().replace(
                'answer: ', '')
            formula = answer_s.split('=')[0].strip()
            input_str = final_state.split('\n')[0]
            input_numbers = sorted(re.findall(r'\d+', input_str))
            output_numbers = sorted(re.findall(r'\d+', formula))
            cf.info({
                'input': input_numbers,
                'output': output_numbers,
                'formula': formula
            })
            if input_numbers != output_numbers:
                return 0
            else:
                try:
                    return 1 if eval(formula) == 24 else 0
                except Exception as e:
                    cf.warning(e)
                    return 0


def tot_solve(puzzles: list):
    results = []
    for puzzle in puzzles:
        totsolver = ToTSolver(puzzle, 4,sample_size=5)
        result = totsolver.solve()
        results.append(result)
        cf.info('Accuracy: {}'.format(sum(results) / len(results)))
    return results


if __name__ == '__main__':
    puzzles = get_puzzles(901, 1000)
    tot_solve(puzzles)
