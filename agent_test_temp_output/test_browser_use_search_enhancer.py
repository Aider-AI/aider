import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Add aider path to sys.path to allow importing SearchEnhancer
# This assumes the test is run from the project root or similar context
# Adjust if necessary based on test execution environment
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
AIDER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..')) # Navigate up to project root
if AIDER_DIR not in sys.path:
    sys.path.insert(0, AIDER_DIR)

try:
    from aider.search_enhancer import SearchEnhancer
except ImportError as e:
    print(f"Error importing SearchEnhancer: {e}")
    print("Ensure the script is run from a context where 'aider' module is discoverable,")
    print("or AIDER_DIR in this script points to the correct project root.")
    sys.exit(1)

# Mock objects for SearchEnhancer dependencies
class MockArgs:
    def __init__(self):
        # Essential for SearchEnhancer initialization
        self.deepseek_api_key = os.getenv("DEEPSEEK_API_KEY") # MUST BE SET IN ENV
        self.deepseek_model_name = "deepseek-chat" # Or your preferred model
        self.browser_use_real_browser_path = None # Set to your Chrome path for real browser, e.g., '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        self.browser_use_headless = True # True for headless, False for UI
        self.browser_use_page_timeout = 30000
        self.browser_use_max_content_length = 20000
        
        # For AgentCoder parts that SearchEnhancer might indirectly expect via self.llm (Coder instance)
        # These are not directly used by SearchEnhancer but help mock the Coder environment.
        self.agent_web_search = "always" # To enable search in tests

class MockIO:
    def tool_output(self, message, log_only=False, bold=False):
        print(f"[IO TOOL OUTPUT] {message}")

    def tool_warning(self, message):
        print(f"[IO TOOL WARNING] {message}")

    def tool_error(self, message):
        print(f"[IO TOOL ERROR] {message}")

    # Mock other methods if SearchEnhancer or its helpers call them
    # For example, if confirm_ask is used:
    def confirm_ask(self, prompt, default="y"):
        print(f"[IO CONFIRM ASK] {prompt} (defaulting to '{default}')")
        return default == "y"


class MockAiderLLM:
    """Mocks the LLM object that SearchEnhancer expects for its internal LLM calls 
       (e.g., generating the browser task instruction).
       This LLM is the one passed from AgentCoder (main_model or planner_llm)."""
    def __init__(self, name="mock-aider-llm"):
        self.name = name
        # Mock attributes that might be accessed by SearchEnhancer's _ask_llm_for_browser_task_instruction
        self.main_model = self # For the self.llm.send(..., model=self.llm.main_model, ...) call
        self.partial_response_content = ""


    def send(self, messages, model, functions, temperature):
        """Simplified mock of Coder.send for non-streaming, single response.
           Yields the response content as a single chunk."""
        print(f"[MockAiderLLM.send CALLED for task generation] messages: {messages}")
        # Based on the prompt in _ask_llm_for_browser_task_instruction
        user_query = "Unknown query"
        if messages and messages[0]['role'] == 'user':
            content = messages[0]['content']
            # Basic extraction of the original_user_query for more dynamic mock response
            start_phrase = "Given the user's information need: \""
            end_phrase = "\"\\n\\nFormulate a concise"
            start_idx = content.find(start_phrase)
            if start_idx != -1:
                start_idx += len(start_phrase)
                end_idx = content.find(end_phrase, start_idx)
                if end_idx != -1:
                    user_query = content[start_idx:end_idx]

        # Simulate generating a task instruction
        mock_task_instruction = f"Find detailed information about '{user_query}' and provide a comprehensive summary of key facts, current status, and implications."
        print(f"[MockAiderLLM.send RETURNING TASK]: {mock_task_instruction}")
        yield mock_task_instruction # Yield it as a single chunk

    def completion(self, messages, temperature): # Fallback path in _ask_llm...
        print(f"[MockAiderLLM.completion CALLED for task generation] messages: {messages}")
        user_query = "Unknown query from completion"
        # Simplified extraction similar to send
        mock_task_instruction = f"Research via completion: '{user_query}' and summarize."
        print(f"[MockAiderLLM.completion RETURNING TASK]: {mock_task_instruction}")
        
        # Mimic litellm completion object structure
        choice = MagicMock()
        choice.message.content = mock_task_instruction
        completion_obj = MagicMock()
        completion_obj.choices = [choice]
        return completion_obj


def main_test():
    print("--- Starting SearchEnhancer Test with Browser-Use ---")
    
    mock_args = MockArgs()
    mock_io = MockIO()
    mock_aider_llm_for_task_generation = MockAiderLLM()

    if not mock_args.deepseek_api_key:
        print("[TEST ERROR] DEEPSEEK_API_KEY environment variable not set. This test requires it.")
        print("Skipping test.")
        return

    print(f"Using DeepSeek API Key: {'********' if mock_args.deepseek_api_key else 'Not Set'}")
    print(f"Browser path: {mock_args.browser_use_real_browser_path or 'Default (Browser-Use managed)'}")
    print(f"Headless: {mock_args.browser_use_headless}")

    search_enhancer = None
    try:
        # Instantiate SearchEnhancer
        # The first LLM arg is for SearchEnhancer to generate the browser task instruction.
        search_enhancer = SearchEnhancer(llm=mock_aider_llm_for_task_generation, io=mock_io, args=mock_args)

        # Test 1: perform_browser_task
        print("\n--- Test 1: perform_browser_task ---")
        test_query = "What are the latest advancements in AI for 2024?"
        print(f"Query: {test_query}")
        browser_task_result = search_enhancer.perform_browser_task(test_query)
        if browser_task_result:
            print(f"Result from perform_browser_task (first 500 chars):\n{browser_task_result[:500]}...")
        else:
            print("perform_browser_task returned no result or an error occurred.")

        # Test 2: fetch_url_content
        print("\n--- Test 2: fetch_url_content --- (using example.com)")
        test_url = "http://example.com"
        print(f"URL: {test_url}")
        fetched_content = search_enhancer.fetch_url_content(test_url)
        if fetched_content:
            print(f"Fetched content from {test_url} (first 500 chars):\n{fetched_content[:500]}...")
        else:
            print(f"fetch_url_content for {test_url} returned no content or an error occurred.")
        
        # Test 3: Another perform_browser_task
        print("\n--- Test 3: perform_browser_task (different query) ---")
        test_query_2 = "Who won the last FIFA world cup?"
        print(f"Query: {test_query_2}")
        browser_task_result_2 = search_enhancer.perform_browser_task(test_query_2)
        if browser_task_result_2:
            print(f"Result from perform_browser_task (first 500 chars):\n{browser_task_result_2[:500]}...")
        else:
            print("perform_browser_task (2) returned no result or an error occurred.")


    except Exception as e:
        print(f"[TEST ERROR] An error occurred during the test: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        if search_enhancer:
            print("\n--- Cleaning up: Closing browser ---")
            search_enhancer.close_browser()

    print("\n--- SearchEnhancer Test Finished ---")

if __name__ == "__main__":
    # This is a basic test script, not a unittest.
    # It requires DEEPSEEK_API_KEY to be set in the environment.
    # It may also require Playwright browsers to be installed (`playwright install`).
    main_test() 