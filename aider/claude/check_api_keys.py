import os
from dotenv import load_dotenv

load_dotenv()


def check_api_keys():
    """
    Check the validity of API keys.

    This function checks the validity of API keys required for accessing external services.
    It first retrieves the values of the environment variables 'OPENAI_API_KEY' and 'ANTHROPIC_API_KEY'.
    If the 'OPENAI_API_KEY' environment variable is set it return False
    If the 'ANTHROPIC_API_KEY' environment variable is set it returns True
    If neither of the environment variables are set, it returns False.

    Parameters:
    - None

    Returns:
    - False: If neither 'OPENAI_API_KEY' nor 'ANTHROPIC_API_KEY' environment variables are set.

    Note:
    - This function assumes that the required environment variables are properly set before running this function.
    You can load them into an .env file in the format 'OPENAI_API_KEY=your_api_key' and 'ANTHROPIC_API_KEY=your_api_key'.
    Also sets the value of the 'has_dot_env' variable's truthy value.
    """
    openai_api_key = os.getenv("OPENAI_API_KEY")
    anthropic_api_key = os.environ["ANTHROPIC_API_KEY"]
    if openai_api_key:
        return False
    if anthropic_api_key:
        return anthropic_api_key
    else:
        return False
