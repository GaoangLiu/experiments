# --------------------------------------------
import json
import os
import random
import re
import sys
import time
from collections import defaultdict
from functools import reduce
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import codefast as cf
import joblib
import numpy as np
import pandas as pd
from rich import print

from .db import rdcli
from .gpt import gpt
from .prompts import (cot_prompt, io_prompt, propose_prompt,
                      value_last_step_prompt, value_prompt)


def get_puzzles(start_index: int, end_index: int) -> list:
    csv_path = 'https://raw.githubusercontent.com/princeton-nlp/tree-of-thought-llm/master/src/tot/data/24/24.csv'
    df = pd.read_csv(csv_path)
    df = df[(df['Rank'] >= start_index) & (df['Rank'] <= end_index)]
    puzzles = df['Puzzles'].tolist()
    return puzzles


data = cf.io.read('data/thoughts.txt')
results = []
for thought in data:
    print(thought)
    thought = thought.split('left: ')[-1].replace(')', '')
    prompt_str = value_prompt.format(thought)
    response = gpt(prompt_str)
    results.append((thought, response))
cf.io.write(results, 'data/results.txt')
