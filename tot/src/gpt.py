import os

import codefast as cf
import joblib
import numpy as np
import pandas as pd
from catgpt.model import GPT
from dotenv import load_dotenv
from rich import print

load_dotenv()


def chatgpt():
    api_key = os.getenv("GPT_API_KEY")
    url = os.getenv("GPT_API_URL")
    return GPT(url,
              model='gpt-3.5-turbo',
              history_path=None,
              history_length=0,
              openai_key=None,
              bearer_token=api_key,
              proxy=None)

def gpt(prompt_str)->str:
    response= cf.net.post('http://192.243.126.170:18080', json={'prompt': prompt_str})
    return response.json()['response']
    