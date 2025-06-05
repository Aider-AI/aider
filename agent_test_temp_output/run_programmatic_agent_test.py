import sys
import os

# Ensure the main aider directory is in the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from aider.coders.agent_coder import AgentCoder
from aider.models import Model
from aider.io import InputOutput

def main():
    io = InputOutput(pretty=True, yes=True, encoding="utf-8")
    main_model = Model("deepseek/deepseek-chat")
    
    # Core user request
    core_task = "Create a Python file named `agent_test_temp_output/programmatic_generated_file.py` with a function `subtract(a: int, b: int) -> int` that returns `a - b`. Also, create a test file `agent_test_temp_output/test_programmatic_generated_file.py` for this function."

    # Minimal arguments for AgentCoder
    # Other arguments will use their defaults in AgentCoder.__init__ or Coder.__init__
    agent = AgentCoder(
        main_model=main_model,
        io=io,
        repo=None, # No git repo for this simple test
        from_coder=None, # No previous coder
        initial_task=core_task,
        stream=False, # <--- Add this to bypass mdstream usage via show_send_output_stream
        # args=None, # Base Coder __init__ handles args=None by default.
                      # AgentCoder checks `if self.args:` so None is fine.
        # The following are agent-specific and have defaults or are popped in AgentCoder.__init__
        # planner_mode=False, # Default
        # debugger_mode=False, # Default
        # coder_mode=False, # Default
        # auto_apply_patches=True, # Default
        # run_tests_on_change=True, # Default (but no test_command specified here)
        # confirm_cmds=False, # Default (allows auto-execution if execute_cmds is True)
        # execute_cmds=True # Default
    )
    agent.verbose = True # Enable verbose LLM I/O logging

    try:
        io.tool_output(f"Programmatic Agent initialized with task: {core_task}")
        # AgentCoder.run() does not take with_message for the first call if task is set
        agent.run() 
        print("Programmatic Agent run completed.")
    except Exception as e:
        print(f"An error occurred during programmatic agent execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set TOKENIZERS_PARALLELISM to false to avoid warnings in forked processes
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    main() 