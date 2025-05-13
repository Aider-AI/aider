import os
import shelve
import json
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
import datetime
import time
import logging # Import logging for logger checks

# Assuming the script is run from the project root or PYTHONPATH is set
# This import path assumes the test script is in tests/local_analytics/
try:
    from local_analytics.local_analytics_collector import LocalAnalyticsCollector
except ImportError:
    # Fallback import path if the script is run from a different location
    # This might require adjusting PYTHONPATH or running from the project root
    print("Could not import LocalAnalyticsCollector directly. Ensure PYTHONPATH is set or run from project root.")
    print("Attempting import assuming script is in tests/local_analytics/")
    try:
        # Adjust path for potential different execution contexts
        import sys
        sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
        from local_analytics.local_analytics_collector import LocalAnalyticsCollector
        sys.path.pop(0) # Clean up sys.path
    except ImportError as e:
        print(f"Failed to import LocalAnalyticsCollector even with path adjustment: {e}")
        # Exit or raise error if import fails
        raise


# Dummy IO class to satisfy the collector's __init__
class DummyIO:
    def tool_output(self, *args, **kwargs):
        pass
    def tool_warning(self, *args, **kwargs):
        pass
    def tool_error(self, *args, **kwargs):
        pass
    def confirm_ask(self, *args, **kwargs):
        return 'y' # Default to yes for confirmations
    def print(self, *args, **kwargs):
        pass
    def append_chat_history(self, *args, **kwargs):
        pass


class TestLocalAnalyticsCollectorStandalone(unittest.TestCase):

    def setUp(self):
        # Create a temporary directory for test files
        self.temp_dir = tempfile.mkdtemp()
        self.project_name = os.path.basename(self.temp_dir)
        # Define file paths relative to the temporary project root
        self.analytics_dir = os.path.join(self.temp_dir, "local_analytics")
        self.data_file = os.path.join(self.analytics_dir, "aider_analytics_data.shelve")
        self.session_jsonl_file = os.path.join(self.analytics_dir, "session.jsonl")
        self.dashboard_output_file = os.path.join(self.analytics_dir, "dashboard.html")
        self.log_file = os.path.join(self.analytics_dir, "local_analytics_collector.logs")

        # Ensure the local_analytics directory exists within the temp dir
        os.makedirs(self.analytics_dir, exist_ok=True)

        # Mock the generate_dashboard function
        # Patch the function where it's *used* in local_analytics_collector.py
        self.patcher_generate_dashboard = patch('local_analytics.local_analytics_collector.generate_dashboard')
        self.mock_generate_dashboard = self.patcher_generate_dashboard.start()

        # Mock litellm.completion_cost as it might be called internally
        self.patcher_litellm_cost = patch('litellm.completion_cost')
        self.mock_litellm_cost = self.patcher_litellm_cost.start()
        self.mock_litellm_cost.return_value = 0.03 # Return a fixed cost for testing

        # Mock litellm.success_callback list to control it during the test
        # The collector appends its callback to this list in __init__
        self.patcher_litellm_success_callback_list = patch('litellm.success_callback', new_callable=list)
        self.mock_litellm_success_callback_list = self.patcher_litellm_success_callback_list.start()

        # Create a dummy IO object
        self.dummy_io = DummyIO()

    def tearDown(self):
        # Stop all patches
        self.patcher_generate_dashboard.stop()
        self.patcher_litellm_cost.stop()
        self.patcher_litellm_success_callback_list.stop()

        # Clean up the temporary directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_analytics_collection_and_output(self):
        """
        Tests that analytics data is collected, saved to shelve,
        written to session.jsonl, and the dashboard generator is called
        with the correct shelve file path.
        """
        # 1. Initialize collector
        # Pass the temporary directory as the git_root
        collector = LocalAnalyticsCollector(self.dummy_io, git_root=self.temp_dir, enabled=True)

        # Verify the collector's callback was added to the litellm list
        self.assertIn(collector._litellm_success_callback, self.mock_litellm_success_callback_list)

        # 2. Simulate an interaction
        query = "Test query for analytics collection"
        modified_files = ["test_file1.py", "docs/test_doc.md"]
        collector.start_interaction(query, modified_files_in_chat=modified_files)

        # Simulate an LLM call within the interaction
        mock_completion_response = MagicMock()
        mock_completion_response.usage.prompt_tokens = 100
        mock_completion_response.usage.completion_tokens = 200
        mock_completion_response.id = "chatcmpl-test-id-12345"
        mock_completion_response.choices = [MagicMock()]
        mock_completion_response.choices[0].finish_reason = "stop"

        llm_call_kwargs = {"model": "gpt-4o", "messages": [{"role": "user", "content": "..."}]}
        start_time = datetime.datetime.now()
        # Simulate some duration
        time.sleep(0.01)
        end_time = datetime.datetime.now()

        # Manually call the internal success callback to simulate a completed LLM call
        collector._litellm_success_callback(llm_call_kwargs, mock_completion_response, start_time, end_time)

        # Simulate a commit
        commit_hash = "abcdef1234567890"
        commit_message = "feat: added test analytics data"
        collector.log_commit(commit_hash, commit_message)

        # End the interaction
        collector.end_interaction()

        # 3. End the session (triggers saving to shelve and writing to jsonl)
        collector.end_session()

        # 4. Assertions

        # Check if shelve file exists and contains data
        # Shelve creates multiple files, check for the base name
        self.assertTrue(any(f.startswith(os.path.basename(self.data_file)) for f in os.listdir(self.analytics_dir)),
                        "Shelve data files should exist")
        try:
            # Use the base path for shelve.open
            with shelve.open(self.data_file, 'r') as db:
                self.assertIn("interactions", db, "Shelve should contain 'interactions' key")
                interactions = db["interactions"]
                self.assertIsInstance(interactions, list, "'interactions' in shelve should be a list")
                self.assertEqual(len(interactions), 1, "Shelve should contain exactly one interaction")

                interaction_data = interactions[0]
                self.assertEqual(interaction_data.get("query"), query)
                self.assertEqual(interaction_data.get("modified_files_in_chat"), modified_files)
                self.assertGreater(interaction_data.get("interaction_duration_seconds", 0), 0)

                self.assertIn("llm_calls_details", interaction_data)
                self.assertEqual(len(interaction_data["llm_calls_details"]), 1)
                llm_call_detail = interaction_data["llm_calls_details"][0]
                self.assertEqual(llm_call_detail.get("model"), "gpt-4o")
                self.assertEqual(llm_call_detail.get("prompt_tokens"), 100)
                self.assertEqual(llm_call_detail.get("completion_tokens"), 200)
                self.assertEqual(llm_call_detail.get("cost"), 0.03)
                # Check timestamp format (isoformat)
                self.assertIsInstance(llm_call_detail.get("timestamp"), str)
                try:
                    datetime.datetime.fromisoformat(llm_call_detail["timestamp"])
                except ValueError:
                    self.fail("LLM call timestamp is not in ISO format")


                self.assertIn("commits_made_this_interaction", interaction_data)
                self.assertEqual(len(interaction_data["commits_made_this_interaction"]), 1)
                self.assertEqual(interaction_data["commits_made_this_interaction"][0].get("hash"), commit_hash)
                self.assertEqual(interaction_data["commits_made_this_interaction"][0].get("message"), commit_message)

                # Check token summary
                token_summary = interaction_data.get("token_summary", {})
                self.assertEqual(token_summary.get("prompt_tokens"), 100)
                self.assertEqual(token_summary.get("completion_tokens"), 200)
                self.assertEqual(token_summary.get("total_tokens"), 300)
                self.assertEqual(token_summary.get("estimated_cost"), 0.03)


        except Exception as e:
            self.fail(f"Error reading shelve file: {e}")

        # Check if session.jsonl file exists and contains data
        self.assertTrue(os.path.exists(self.session_jsonl_file), "session.jsonl file should exist")
        try:
            with open(self.session_jsonl_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                self.assertEqual(len(lines), 1, "session.jsonl should contain exactly one line")
                json_data = json.loads(lines[0])

                # Verify content matches the interaction data saved in shelve
                # Note: JSON serialization/deserialization might change types slightly (e.g., datetime becomes string)
                # We already verified the shelve data structure above, just check some key values
                self.assertIsInstance(json_data, dict)
                self.assertEqual(json_data.get("query"), query)
                self.assertEqual(json_data.get("modified_files_in_chat"), modified_files)
                self.assertIn("llm_calls_details", json_data)
                self.assertEqual(len(json_data["llm_calls_details"]), 1)
                self.assertIn("commits_made_this_interaction", json_data)
                self.assertEqual(len(json_data["commits_made_this_interaction"]), 1)
                self.assertEqual(json_data.get("token_summary", {}).get("total_tokens"), 300)


        except Exception as e:
            self.fail(f"Error reading or parsing session.jsonl: {e}")


        # Check if generate_dashboard was called with correct arguments
        self.mock_generate_dashboard.assert_called_once()
        # Check arguments: project_name, shelve_file_path, dashboard_output_path, logger
        called_args, called_kwargs = self.mock_generate_dashboard.call_args
        self.assertEqual(called_args[0], self.project_name)
        self.assertEqual(called_args[1], self.data_file) # Verify shelve file path is passed
        self.assertEqual(called_args[2], self.dashboard_output_file)
        # Optionally check the logger argument type
        self.assertIsInstance(called_args[3], logging.LoggerAdapter)


# This allows running the test directly from the command line
if __name__ == '__main__':
    # Add a basic handler for unittest output if run directly
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

