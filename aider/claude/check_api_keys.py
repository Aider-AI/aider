import os
from dotenv import load_dotenv

load_dotenv()


def check_api_keys():
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
    if anthropic_api_key:
        return anthropic_api_key
    if openai_api_key:
        return False
    else:
        return False
