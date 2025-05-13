# aider/local_analytics_collector.py
import atexit
import datetime
import logging
import os
import platform
import shelve
import sys
import time
import uuid
import json # Import json module
import re # Import re module

import litellm

# Import from the local_analytics package (assuming project_root/local_analytics/dashboard_generator.py)
from local_analytics.dashboard_generator import main

try:
    from aider import __version__ as aider_version_val
except ImportError:
    aider_version_val = "unknown"

# Path constants relative to the project root where Aider is run
DATA_SHELVE_FILE = "local_analytics/aider_analytics_data.shelve"
# Constant for the dashboard HTML file
# REMOVED: DASHBOARD_HTML_FILE = "local_analytics/dashboard.html"
LOG_FILE = "local_analytics/local_analytics_collector.logs"
SESSION_JSONL_FILE = "local_analytics/session.jsonl" # Define the new JSONL file path

class LocalAnalyticsCollector:
    """
    Collects local analytics data for Aider sessions and interactions.

    This class tracks various metrics related to LLM calls, token usage,
    code modifications, and session timings. Data is stored locally using
    the `shelve` module.
    """
    def __init__(self, io, git_root=None, enabled=True):
        """
        Initializes the LocalAnalyticsCollector.

        Args:
            io: An InputOutput object for user interaction (currently unused beyond holding a reference).
            git_root (str, optional): The root directory of the git project.
                                     Defaults to None, in which case the current working directory is used.
            enabled (bool, optional): Whether analytics collection is enabled. Defaults to True.
        """
        self.io = io # Retain for the final user-facing message
        self.enabled = enabled
        if not self.enabled:
            return

        if git_root:
            self.project_name = os.path.basename(os.path.abspath(git_root))
            base_path = git_root
        else:
            self.project_name = os.path.basename(os.getcwd())
            base_path = os.getcwd()

        self.data_file = os.path.join(base_path, DATA_SHELVE_FILE)
        self.log_file = os.path.join(base_path, LOG_FILE)
        # Store the dashboard output file path
        # REMOVED: self.dashboard_output_file = os.path.join(base_path, DASHBOARD_HTML_FILE)
        # Store the session JSONL file path
        self.session_jsonl_file = os.path.join(base_path, SESSION_JSONL_FILE)


        self.session_id = str(uuid.uuid4())
        self.aider_version = aider_version_val
        self.platform_info = platform.platform()
        self.python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        self._current_interaction_data = None
        self._interaction_start_time_monotonic = None

        # <<< START LOGGER SETUP
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        self.logger = logging.getLogger(__name__ + ".LocalAnalyticsCollector") # Or just __name__
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False # Prevent logs from reaching root logger / console

        # Remove existing handlers to prevent duplication if __init__ is called multiple times
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
            handler.close()

        fh = logging.FileHandler(self.log_file, encoding='utf-8')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(session_id)s - %(message)s')
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)

        # Make session_id available to logger formatter
        self._log_adapter = logging.LoggerAdapter(self.logger, {'session_id': self.session_id})

        self._log_adapter.debug(f"--- LocalAnalyticsCollector Initialized ---")
        self._log_adapter.debug(f"Project: {self.project_name}")
        self._log_adapter.debug(f"Data file: {self.data_file}")
        self._log_adapter.debug(f"Log file: {self.log_file}")
        self._log_adapter.debug(f"Session JSONL file: {self.session_jsonl_file}")
        # <<< END LOGGER SETUP

        data_dir = os.path.dirname(self.data_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
        # Ensure directory for dashboard.html and session.jsonl also exists
        # REMOVED: output_dir = os.path.dirname(self.dashboard_output_file) # Assuming dashboard and jsonl are in the same dir
        output_dir = os.path.dirname(self.session_jsonl_file) # Use session_jsonl_file path
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)


        atexit.register(self.end_session)

        self._original_success_callbacks = litellm.success_callback[:]
        self._original_failure_callbacks = litellm.failure_callback[:]
        if self._litellm_success_callback not in litellm.success_callback:
            litellm.success_callback.append(self._litellm_success_callback)




    def start_interaction(self, query, modified_files_in_chat=None):
        """
        Starts tracking a new interaction.

        If a previous interaction was in progress, it will be ended first.

        Args:
            query (str): The user's query for this interaction.
            modified_files_in_chat (list, optional): A list of files modified in the chat context.
                                                    Defaults to None.
        """
        if not self.enabled:
            return
        if self._current_interaction_data:
            self.end_interaction()  # End previous interaction if any

        self._interaction_start_time_monotonic = time.monotonic()
        self._current_interaction_data = {
            "session_id": self.session_id,
            "project_name": self.project_name,
            "interaction_timestamp": datetime.datetime.now().isoformat(),
            "interaction_duration_seconds": 0,
            "query": re.split(r"```diff", query, 1)[0].strip(),
            "aider_version": self.aider_version,
            "platform_info": self.platform_info,
            "python_version": self.python_version,
            "token_summary": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "estimated_cost": 0.0},
            "models_used_summary": [],
            "llm_calls_details": [],
            "modified_files_in_chat": modified_files_in_chat or [],
            "commits_made_this_interaction": []
        }


    def end_interaction(self):
        """
        Ends the current interaction and saves its data.

        Calculates interaction duration, summarizes model usage, and persists
        the interaction data to the shelve database.
        """
        if not self.enabled or not self._current_interaction_data:
            return

        if self._interaction_start_time_monotonic:
            duration = time.monotonic() - self._interaction_start_time_monotonic
            self._current_interaction_data["interaction_duration_seconds"] = duration

        # Summarize model usage from detailed calls
        model_summary_map = {}
        for call in self._current_interaction_data.get("llm_calls_details", []):
            model_name = call.get("model", "unknown_model")
            entry = model_summary_map.setdefault(
                model_name,
                {
                    "name": model_name,
                    "calls": 0,
                    "cost": 0.0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                },
            )
            entry["calls"] += 1
            entry["cost"] += call.get("cost", 0.0)
            entry["prompt_tokens"] += call.get("prompt_tokens", 0)
            entry["completion_tokens"] += call.get("completion_tokens", 0)
        self._current_interaction_data["models_used_summary"] = list(model_summary_map.values())

        try:
            with shelve.open(self.data_file) as db:
                interactions = db.get("interactions", [])
                interactions.append(self._current_interaction_data)
                db["interactions"] = interactions
        except Exception as e:
            self._log_adapter.error(f"Error saving interaction to shelve: {e}")

        self._current_interaction_data = None
        self._interaction_start_time_monotonic = None




    def _litellm_success_callback(self, kwargs, completion_response, start_time, end_time):
        """
        Callback for successful LiteLLM calls.

        This method is registered with LiteLLM to capture details of each
        successful LLM API call, including token usage and cost.

        Args:
            kwargs: Keyword arguments passed to the LiteLLM completion call.
            completion_response: The response object from LiteLLM.
            start_time: Timestamp when the LLM call started.
            end_time: Timestamp when the LLM call ended.
        """
        if not self.enabled or not self._current_interaction_data:
            return

        model_name = kwargs.get("model", "unknown_model")
        usage = getattr(completion_response, "usage", None)
        prompt_tokens = getattr(usage, 'prompt_tokens', 0) if usage else 0
        completion_tokens = getattr(usage, 'completion_tokens', 0) if usage else 0

        cost = 0.0
        try:
            # Ensure cost is float, handle potential errors from litellm.completion_cost
            calculated_cost = litellm.completion_cost(completion_response=completion_response)
            cost = float(calculated_cost) if calculated_cost is not None else 0.0
        except Exception as e: # Broad exception catch if litellm.completion_cost fails
            self._log_adapter.warning(
                f"Analytics: Could not calculate cost for LLM call. Error: {e}"
            )
            cost = 0.0 # Ensure cost is always a float, defaulting to 0.0 on error

        call_detail = {
            "model": model_name,
            "id": getattr(completion_response, "id", None),
            "finish_reason": (
                getattr(completion_response.choices[0], "finish_reason", None)
                if hasattr(completion_response, "choices") and completion_response.choices
                else None
            ),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost": cost,
            "timestamp": start_time.isoformat(),
        }
        self._current_interaction_data["llm_calls_details"].append(call_detail)

        ts = self._current_interaction_data["token_summary"]
        ts["prompt_tokens"] += prompt_tokens
        ts["completion_tokens"] += completion_tokens
        ts["total_tokens"] += prompt_tokens + completion_tokens
        ts["estimated_cost"] += cost




    def log_commit(self, commit_hash, commit_message):
        """
        Logs a git commit made during the current interaction.

        Args:
            commit_hash (str): The hash of the commit.
            commit_message (str): The commit message.
        """
        if not self.enabled or not self._current_interaction_data:
            return
        commit_info = {"hash": commit_hash, "message": commit_message}
        self._current_interaction_data["commits_made_this_interaction"].append(commit_info)




    def end_session(self):
        """
        Ends the analytics collection session.

        Ensures any ongoing interaction is ended, generates the HTML dashboard,
        unregisters the atexit handler, and restores original LiteLLM callbacks.
        """
        if not self.enabled: # If analytics was never enabled or session already ended.
            # Unregister atexit handler early if it was somehow registered without enabling
            # This path should ideally not be hit if __init__ logic is correct.
            try:
                atexit.unregister(self.end_session)
            except TypeError: # pragma: no cover
                pass # Handler was not registered or other issue
            return


        # End any ongoing interaction first
        if self._current_interaction_data:
            self.end_interaction()

        # Write all the `shelve` data to session.jsonl
        if hasattr(self, 'data_file') and hasattr(self, 'session_jsonl_file'):
            try:
                with shelve.open(self.data_file, 'r') as db:
                    interactions = db.get("interactions", [])

                with open(self.session_jsonl_file, 'w', encoding='utf-8') as f:
                    for interaction in interactions:
                        # Ensure data is JSON serializable (e.g., handle datetime objects if any slipped through)
                        # Although datetime is converted to isoformat already, this is a good practice.
                        # Simple approach: convert to string if not serializable, or use a custom encoder.
                        # For now, assuming isoformat is sufficient based on start_interaction.
                        json_line = json.dumps(interaction)
                        f.write(json_line + '\n')
                
                # generate dashboard
                main()

                if hasattr(self, '_log_adapter'):
                    self._log_adapter.info(f"Shelve data written to {self.session_jsonl_file}")

            except Exception as e:
                if hasattr(self, '_log_adapter'):
                    self._log_adapter.error(f"Error writing shelve data to JSONL: {e}")
                else: # pragma: no cover
                    print(f"Error writing shelve data to JSONL: {e}") # Fallback if logger not set


        # Cleanup atexit handler
        try:
            atexit.unregister(self.end_session)
        except TypeError: # pragma: no cover
            pass # Handler was not registered or other issue

        # Restore LiteLLM callbacks
        # Check if _original_success_callbacks exists before assigning
        if hasattr(self, '_original_success_callbacks'):
            litellm.success_callback = self._original_success_callbacks
        # if hasattr(self, '_original_failure_callbacks'): # If failure callbacks were also stored
        #    litellm.failure_callback = self._original_failure_callbacks

        if hasattr(self, '_log_adapter'):
            self._log_adapter.info("LocalAnalyticsCollector session ended.")

        # Ensure logger handlers are closed to release file locks, especially on Windows
        if hasattr(self, 'logger'): # Check if logger was initialized
            for handler in self.logger.handlers[:]:
                handler.close()
                self.logger.removeHandler(handler)
        # Set self.enabled to False after cleanup to prevent re-entry or further use
        self.enabled = False
