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
    import google.generativeai as genai
    genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
    model = genai.GenerativeModel('gemini-pro')
    return model.generate_content(prompt_str).text
    