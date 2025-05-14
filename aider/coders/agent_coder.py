from aider.coders.base_coder import Coder
from aider.commands import SwitchCoder # May need to adjust import based on final location
from aider import prompts # Import prompts module
import json # For parsing LLM plan output
import os
import re
import subprocess

from aider.coders.editblock_coder import EditBlockCoder # For parsing edits

class AgentCoder(Coder):
    coder_name = "agent" # For identification, if needed
    announce_after_switch = False # Agent will manage its own announcements

    def __init__(self, main_model, io, repo, from_coder, **kwargs):
        super().__init__(main_model, io, repo, from_coder, **kwargs)
        self.initial_task = kwargs.get("initial_task", "No task provided.")
        self.current_phase = "idle" # Phases: idle, clarification, planning, test_design, approval, execution, reporting
        self.plan = None
        self.tests = None
        self.deliverables = []
        self.current_deliverable_index = 0
        self.from_coder = from_coder # Store reference to switch back
        self.clarification_history = [] # History for this phase

        # Inherit file context from the previous coder
        self.abs_fnames = set(kwargs.get("fnames", []))
        self.abs_read_only_fnames = set(kwargs.get("read_only_fnames", []))

        self.io.tool_output(f"AgentCoder initialized for task: {self.initial_task}")
        self.io.tool_output("Agent Mode: Starting task clarification phase.")
        self.current_phase = "clarification"


    def run(self, with_message=None):
        """
        Main entry point for the AgentCoder after it's switched to.
        This will be called by the main loop in aider/main.py.
        """
        if self.current_phase == "clarification":
            return self.run_clarification_phase(with_message)
        elif self.current_phase == "planning":
            return self.run_planning_phase()
        elif self.current_phase == "test_design":
            return self.run_test_design_phase()
        elif self.current_phase == "approval":
            return self.run_approval_phase()
        elif self.current_phase == "execution":
            return self.run_execution_phase()
        elif self.current_phase == "integration_testing":
            return self.run_integration_testing_phase()
        elif self.current_phase == "reporting":
            return self.run_reporting_phase()
        else:
            self.io.tool_error(f"AgentCoder in unknown phase: {self.current_phase}")
            # Potentially switch back to a default coder or end the session.
            # For now, just indicate an issue.
            return None # Or raise an exception

    # Placeholder methods for each phase - to be fleshed out
    def run_clarification_phase(self, user_input=None):
        """Handles the interactive task clarification phase."""
        if not self.clarification_history:
            # First turn
            self.clarification_history.append({"role": "user", "content": self.initial_task})
            prompt_content = self.initial_task
            system_message = prompts.agent_clarification_system.format(initial_task=self.initial_task)
            messages = [{"role": "system", "content": system_message}]
        else:
            # Subsequent turns
            if user_input:
                self.clarification_history.append({"role": "user", "content": user_input})
            else:
                # This shouldn't happen after the first turn, but handle defensively
                self.io.tool_error("Agent (Clarification): Expected user input but received none.")
                # Potentially switch back or stop
                self.current_phase = "idle"
                return "Agent stopped due to missing input."

            # Use existing system message and history
            messages = [{"role": "system", "content": self.clarification_history[0]['content']}] # Reuse initial system prompt
            messages += self.clarification_history[1:] # Add user/assistant turns

        self.io.tool_output("Agent (Clarification): Thinking...")
        llm_response_content = self._get_llm_response(messages)

        if not llm_response_content:
            self.io.tool_error("Agent (Clarification): Failed to get response from LLM.")
            self.current_phase = "idle"
            return "Agent stopped due to LLM error."

        self.clarification_history.append({"role": "assistant", "content": llm_response_content})

        # Check if LLM indicates completion
        # Using a simple keyword check for now, can be made more robust
        if "[CLARIFICATION_COMPLETE]" in llm_response_content or \
           "Shall I proceed to planning" in llm_response_content:

            final_understanding = llm_response_content.replace("[CLARIFICATION_COMPLETE]", "").strip()
            self.io.tool_output(f"Agent (Clarification): Understanding:\n{final_understanding}")
            self.io.tool_output("Clarification complete. Moving to planning.")
            self.current_phase = "planning"
            # Store the final clarified task (maybe the whole history or just the last summary)
            self.clarified_task = "\n".join([f"{msg['role']}: {msg['content']}" for msg in self.clarification_history])
            return self.run() # Transition to next phase immediately
        else:
            # Ask the user the LLM's question/statement
            self.io.tool_output(f"Agent (Clarification):\n{llm_response_content}")
            # Return None to signal the main loop to get user input
            return None

    def run_planning_phase(self):
        """Handles the plan generation phase."""
        self.io.tool_output("Agent (Planning): Generating plan...")

        if not hasattr(self, 'clarified_task') or not self.clarified_task:
            self.io.tool_error("Agent (Planning): Clarified task is missing. Cannot generate plan.")
            self.current_phase = "idle"
            return "Agent stopped due to missing clarified task."

        system_message = prompts.agent_planning_system.format(clarified_task=self.clarified_task)
        messages = [{"role": "system", "content": system_message}]
        # Optionally, could include self.clarification_history if the prompt needs more context,
        # but agent_planning_system is designed to take the summary.

        llm_response_content = self._get_llm_response(messages, expecting_json=True)

        if not llm_response_content:
            self.io.tool_error("Agent (Planning): Failed to get plan from LLM.")
            self.current_phase = "idle"
            return "Agent stopped due to LLM error during planning."

        try:
            # The prompt asks for JSON list of strings directly.
            # Remove potential markdown fences if LLM adds them
            cleaned_response = llm_response_content.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            parsed_deliverables = json.loads(cleaned_response)
            if not isinstance(parsed_deliverables, list) or not all(isinstance(item, str) for item in parsed_deliverables):
                raise ValueError("Plan is not a list of strings.")
            self.plan = {"deliverables": parsed_deliverables}
            self.deliverables = parsed_deliverables
        except (json.JSONDecodeError, ValueError) as e:
            self.io.tool_error(f"Agent (Planning): Failed to parse plan from LLM response: {e}")
            self.io.tool_output(f"LLM Response was: {llm_response_content}")
            self.current_phase = "idle"
            return "Agent stopped due to plan parsing error."

        self.io.tool_output("Generated Plan:")
        self.io.tool_output(json.dumps(self.plan, indent=2))
        self.current_phase = "test_design"
        return self.run()

    def run_test_design_phase(self):
        """Handles the test design phase."""
        self.io.tool_output("Agent (Test Design): Designing tests...")
        self.tests = {"unit_tests": {}, "integration_tests": []}

        if not self.plan or "deliverables" not in self.plan or not self.plan["deliverables"]:
            self.io.tool_error("Agent (Test Design): Plan with deliverables is missing. Cannot design tests.")
            self.current_phase = "idle" # Or back to planning?
            return "Agent stopped due to missing plan for test design."

        # Design Unit Tests for each deliverable
        for deliverable_description in self.deliverables:
            self.io.tool_output(f"Agent (Test Design): Designing unit tests for: {deliverable_description}")
            system_message = prompts.agent_test_design_unit_system.format(deliverable_description=deliverable_description)
            messages = [{"role": "system", "content": system_message}]
            
            llm_response_content = self._get_llm_response(messages, expecting_json=True)
            if not llm_response_content:
                self.io.tool_error(f"Agent (Test Design): Failed to get unit test ideas for '{deliverable_description}'.")
                # Potentially skip this deliverable's tests or stop
                continue 

            try:
                cleaned_response = llm_response_content.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                unit_test_ideas = json.loads(cleaned_response)
                if not isinstance(unit_test_ideas, list) or not all(isinstance(item, str) for item in unit_test_ideas):
                    raise ValueError("Unit test ideas are not a list of strings.")
                self.tests["unit_tests"][deliverable_description] = unit_test_ideas
            except (json.JSONDecodeError, ValueError) as e:
                self.io.tool_error(f"Agent (Test Design): Failed to parse unit test ideas for '{deliverable_description}': {e}")
                self.io.tool_output(f"LLM Response was: {llm_response_content}")
                # Potentially skip or stop

        # Design Integration Tests for the overall plan
        self.io.tool_output("Agent (Test Design): Designing integration tests...")
        plan_json = json.dumps(self.plan, indent=2)
        system_message = prompts.agent_test_design_integration_system.format(plan_json=plan_json)
        messages = [{"role": "system", "content": system_message}]

        llm_response_content = self._get_llm_response(messages, expecting_json=True)
        if not llm_response_content:
            self.io.tool_error("Agent (Test Design): Failed to get integration test ideas.")
            # Potentially proceed without integration tests or stop
        else:
            try:
                cleaned_response = llm_response_content.strip()
                if cleaned_response.startswith("```json"):
                    cleaned_response = cleaned_response[7:]
                if cleaned_response.endswith("```"):
                    cleaned_response = cleaned_response[:-3]
                integration_test_ideas = json.loads(cleaned_response)
                if not isinstance(integration_test_ideas, list) or not all(isinstance(item, str) for item in integration_test_ideas):
                    raise ValueError("Integration test ideas are not a list of strings.")
                self.tests["integration_tests"] = integration_test_ideas
            except (json.JSONDecodeError, ValueError) as e:
                self.io.tool_error(f"Agent (Test Design): Failed to parse integration test ideas: {e}")
                self.io.tool_output(f"LLM Response was: {llm_response_content}")
                # Potentially proceed without integration tests or stop

        self.io.tool_output("Proposed Test Strategy:")
        self.io.tool_output("Unit Tests:")
        for deliverable, tests_list in self.tests["unit_tests"].items():
            self.io.tool_output(f"  For '{deliverable}':")
            for test_idea in tests_list:
                self.io.tool_output(f"    - {test_idea}")
        self.io.tool_output("Integration Tests:")
        for test_idea in self.tests["integration_tests"]:
            self.io.tool_output(f"  - {test_idea}")
        
        self.current_phase = "approval"
        return self.run()

    def run_approval_phase(self):
        """Handles the user approval phase."""
        self.io.tool_output("Agent (Approval): Seeking user approval...")
        self.io.tool_output("--- Generated Plan ---")
        if self.plan:
            self.io.tool_output(json.dumps(self.plan, indent=2))
        else:
            self.io.tool_output("No plan generated.")
        
        self.io.tool_output("\n--- Proposed Test Strategy ---")
        if self.tests:
            self.io.tool_output("Unit Tests:")
            if self.tests.get("unit_tests"):
                for deliverable, tests_list in self.tests["unit_tests"].items():
                    self.io.tool_output(f"  For '{deliverable}':")
                    for test_idea in tests_list:
                        self.io.tool_output(f"    - {test_idea}")
            else:
                self.io.tool_output("  No unit tests proposed.")
            
            self.io.tool_output("Integration Tests:")
            if self.tests.get("integration_tests"):
                for test_idea in self.tests["integration_tests"]:
                    self.io.tool_output(f"  - {test_idea}")
            else:
                self.io.tool_output("  No integration tests proposed.")
        else:
            self.io.tool_output("No tests designed.")
        self.io.tool_output("-------------------------")

        if self.io.confirm_ask("Approve this plan and test strategy to begin autonomous implementation?"):
            self.io.tool_output("Plan approved by user.")
            self.current_phase = "execution"
            self.current_deliverable_index = 0
        else:
            self.io.tool_output("Plan not approved. Agent stopping.")
            self.current_phase = "idle" # Or some other terminal state
            # TODO: Switch back to the original coder or a default one.
            # For now, agent will become idle.
        return self.run()


    def run_execution_phase(self):
        """Handles the autonomous execution of deliverables."""
        max_coding_retries_per_deliverable = 3 # Max attempts to code + fix a single deliverable

        while self.current_deliverable_index < len(self.deliverables):
            deliverable = self.deliverables[self.current_deliverable_index]
            self.io.tool_output(f"Agent (Execution): Starting deliverable {self.current_deliverable_index + 1}/{len(self.deliverables)}: {deliverable}")

            # 6.1: Context Gathering & Prompt Formulation
            coding_context = ""
            # Prioritize files in self.abs_fnames (added to chat) for context
            # A more advanced agent might search the repo for relevant files based on the deliverable.
            for fname_abs in self.abs_fnames: # Files explicitly in chat
                try:
                    content = self.io.read_text(fname_abs)
                    if content is not None:
                        relative_fname = self.get_rel_fname(fname_abs)
                        coding_context += f"\n<filename>{relative_fname}</filename>\n{self.fence[0]}\n{content}\n{self.fence[1]}\n"
                except Exception as e:
                    self.io.tool_warning(f"Could not read file {fname_abs} for context: {e}")
            
            # Include read-only files as well, as they provide context
            for fname_abs in self.abs_read_only_fnames:
                try:
                    content = self.io.read_text(fname_abs)
                    if content is not None:
                        relative_fname = self.get_rel_fname(fname_abs)
                        coding_context += f"\n<filename>{relative_fname}</filename>\n{self.fence[0]}\n{content}\n{self.fence[1]}\n"
                except Exception as e:
                    self.io.tool_warning(f"Could not read read-only file {fname_abs} for context: {e}")


            unit_test_reqs_list = self.tests.get("unit_tests", {}).get(deliverable, [])
            unit_test_requirements = "\n".join([f"- {req}" for req in unit_test_reqs_list])
            if not unit_test_requirements:
                unit_test_requirements = "No specific unit tests were pre-defined for this deliverable. Please infer appropriate tests and ensure the code is testable."

            coding_attempt = 0
            deliverable_implemented_and_tested = False
            
            edited_files_for_deliverable = [] # Track files edited in this deliverable attempt for debugging context

            while coding_attempt < max_coding_retries_per_deliverable:
                self.io.tool_output(f"Agent (Coding): Attempt {coding_attempt + 1}/{max_coding_retries_per_deliverable} for '{deliverable}'...")
                
                current_coding_prompt_system = prompts.agent_coding_system.format(
                    deliverable_description=deliverable,
                    unit_test_requirements=unit_test_requirements,
                    coding_context=coding_context if coding_context else "No existing file context provided for this deliverable. Write new file(s) as needed."
                )
                
                coding_messages = [
                    {"role": "system", "content": self.fmt_system_prompt(self.gpt_prompts.main_system)}, 
                    {"role": "user", "content": current_coding_prompt_system}
                ]

                llm_code_response = self._get_llm_response(coding_messages)

                if not llm_code_response:
                    self.io.tool_error("Agent (Coding): Failed to get code from LLM.")
                    coding_attempt += 1
                    if coding_attempt >= max_coding_retries_per_deliverable:
                         self.io.tool_error(f"Agent (Execution): Max retries reached for LLM code generation for '{deliverable}'.")
                         self.current_phase = "idle"
                         return "Agent stopped due to persistent LLM error during coding."
                    continue

                # 6.2: Apply edits
                self.io.tool_output("Agent (Coding): Applying edits...")
                edited_files_paths = self._parse_and_apply_edits(llm_code_response)
                edited_files_for_deliverable.extend(p for p in edited_files_paths if p not in edited_files_for_deliverable)


                if not edited_files_paths and "create" not in deliverable.lower() and "write" not in deliverable.lower(): # Heuristic: if not creating, edits are expected
                    self.io.tool_warning("Agent (Coding): LLM did not produce any parsable edits.")
                    # This might be a valid case if the deliverable was e.g. "analyze X"
                    # but for most coding tasks, it's an issue.
                    # For now, we'll let it proceed to testing, which will likely fail if code was expected.
                
                # 6.3: Unit Testing
                test_cmd_to_run = None
                if self.test_cmd: # From aider --test-cmd
                    test_cmd_to_run = self.test_cmd
                    self.io.tool_output(f"Agent (Unit Testing): Using global test command: {test_cmd_to_run}")
                else:
                    # TODO: Smarter test command generation based on deliverable/tests
                    # For now, if no global test_cmd, we can't run specific unit tests.
                    self.io.tool_warning("Agent (Unit Testing): No global --test-cmd provided. Cannot run specific unit tests for this deliverable.")
                    # We could assume success here, or require a test_cmd. For now, assume success if no test_cmd.
                    self.io.tool_output(f"Agent (Unit Testing): Tests presumed passed for '{deliverable}' (no test_cmd).")
                    deliverable_implemented_and_tested = True
                    break # Exit retry loop for this deliverable

                if test_cmd_to_run:
                    self.io.tool_output(f"Agent (Unit Testing): Running tests for '{deliverable}' with command: {test_cmd_to_run}")
                    test_output, test_error, return_code = self._run_shell_command(test_cmd_to_run)
                    self.io.tool_output(f"Test Output:\n{test_output}")
                    if test_error:
                        self.io.tool_error(f"Test Error Output:\n{test_error}")

                    if return_code == 0:
                        self.io.tool_output(f"Agent (Unit Testing): Tests passed for '{deliverable}'.")
                        deliverable_implemented_and_tested = True
                        break # Exit retry loop for this deliverable
                    else:
                        # 6.4: Self-Correction Loop
                        self.io.tool_warning(f"Agent (Unit Testing): Tests failed for '{deliverable}'. Attempting fix...")
                        
                        # Prepare context of written/modified code for the debugging prompt
                        debug_code_context = ""
                        for file_path_rel in edited_files_for_deliverable: # Use files touched in this attempt
                            abs_path = self.abs_root_path(file_path_rel)
                            try:
                                content = self.io.read_text(abs_path)
                                if content is not None:
                                    debug_code_context += f"\n<filename>{file_path_rel}</filename>\n{self.fence[0]}\n{content}\n{self.fence[1]}\n"
                            except Exception as e:
                                self.io.tool_warning(f"Could not read file {file_path_rel} for debugging context: {e}")
                        if not debug_code_context:
                             debug_code_context = "Could not retrieve the content of the modified files for debugging."


                        debugging_prompt_system = prompts.agent_debugging_system.format(
                            deliverable_description=deliverable,
                            code_written=debug_code_context,
                            unit_test_requirements=unit_test_requirements, # Original requirements
                            test_output=test_output,
                            test_error=test_error or "No error output."
                        )
                        debugging_messages = [
                            {"role": "system", "content": self.fmt_system_prompt(self.gpt_prompts.main_system)},
                            {"role": "user", "content": debugging_prompt_system}
                        ]

                        llm_fix_response = self._get_llm_response(debugging_messages)

                        if not llm_fix_response:
                            self.io.tool_error("Agent (Debugging): Failed to get fix from LLM.")
                            # No new code to apply, will retry coding the deliverable or fail if max retries for coding
                            coding_attempt += 1 
                            if coding_attempt >= max_coding_retries_per_deliverable:
                                self.io.tool_error(f"Agent (Execution): Max retries reached for LLM fix generation for '{deliverable}'.")
                            continue 

                        self.io.tool_output("Agent (Debugging): Applying LLM's suggested fix...")
                        fix_edited_files = self._parse_and_apply_edits(llm_fix_response)
                        edited_files_for_deliverable.extend(p for p in fix_edited_files if p not in edited_files_for_deliverable)
                        
                        # Increment coding_attempt as a fix attempt also counts towards retries for the deliverable
                        coding_attempt += 1 
                        # The loop will re-run tests with the new code
                else: # No test_cmd_to_run was set
                    self.io.tool_output(f"Agent (Unit Testing): No specific test command for '{deliverable}', assuming pass.")
                    deliverable_implemented_and_tested = True # Or handle as an error/prompt user?
                    break


            if not deliverable_implemented_and_tested:
                self.io.tool_error(f"Agent (Execution): Failed to implement and test '{deliverable}' after {max_coding_retries_per_deliverable} attempts.")
                self.current_phase = "idle" 
                return "Agent stopped due to unfixable error in deliverable."

            # 6.5: Commit (Optional)
            if self.repo and self.auto_commits and edited_files_for_deliverable:
                try:
                    # Commit only the files that were actually edited for this deliverable
                    files_to_commit_abs = [self.abs_root_path(p) for p in edited_files_for_deliverable]
                    self.repo.commit(fnames=files_to_commit_abs, message=f"Agent: Implemented deliverable - {deliverable}", aider_edits=True, coder=self)
                    self.io.tool_output(f"Committed changes for deliverable: {deliverable}")
                except Exception as e:
                    self.io.tool_error(f"Agent (Commit): Failed to commit changes for {deliverable}: {e}")
            
            self.io.tool_output(f"Agent (Execution): Deliverable '{deliverable}' completed.")
            self.current_deliverable_index += 1
            edited_files_for_deliverable = [] # Reset for next deliverable
        
        # If loop completes
        self.io.tool_output("Agent (Execution): All deliverables completed.")
        if self.tests and self.tests.get("integration_tests"):
            self.io.tool_output("Agent: Proceeding to Integration Testing phase.")
            self.current_phase = "integration_testing"
        else:
            self.io.tool_output("Agent: No integration tests defined. Proceeding to Reporting phase.")
            self.current_phase = "reporting"
        return self.run()

    def run_integration_testing_phase(self):
        """Handles the final integration testing phase."""
        self.io.tool_output("Agent (Integration Testing): Running integration tests...")
        max_integration_test_retries = 1 # Integration test fixes are harder, fewer retries.

        if not self.tests or not self.tests.get("integration_tests"):
            self.io.tool_output("Agent (Integration Testing): No integration tests defined. Skipping.")
            self.current_phase = "reporting"
            return self.run()

        integration_test_ideas = self.tests.get("integration_tests", [])
        if not integration_test_ideas:
            self.io.tool_output("Agent (Integration Testing): No integration test ideas found. Skipping.")
            self.current_phase = "reporting"
            return self.run()

        test_cmd_to_run = None
        if self.test_cmd: # From aider --test-cmd, used for all tests for now
            test_cmd_to_run = self.test_cmd
            self.io.tool_output(f"Agent (Integration Testing): Using global test command: {test_cmd_to_run}")
        else:
            self.io.tool_warning("Agent (Integration Testing): No global --test-cmd provided. Cannot run integration tests.")
            self.io.tool_output("Agent (Integration Testing): Integration tests presumed passed (no test_cmd).")
            self.current_phase = "reporting"
            return self.run()

        attempt = 0
        tests_passed = False
        while attempt < max_integration_test_retries:
            self.io.tool_output(f"Agent (Integration Testing): Attempt {attempt + 1}/{max_integration_test_retries} with command: {test_cmd_to_run}")
            test_output, test_error, return_code = self._run_shell_command(test_cmd_to_run)
            self.io.tool_output(f"Integration Test Output:\n{test_output}")
            if test_error:
                self.io.tool_error(f"Integration Test Error Output:\n{test_error}")

            if return_code == 0:
                self.io.tool_output("Agent (Integration Testing): All integration tests passed.")
                tests_passed = True
                break
            else:
                self.io.tool_warning("Agent (Integration Testing): Integration tests failed. Attempting to formulate a fix description for LLM (conceptual)...")
                # Self-correction for integration tests is complex.
                # It would involve providing the LLM with:
                # - The overall plan
                # - The integration test that failed
                # - The output/error from the test
                # - Context from multiple relevant deliverables/files
                # For now, we will not implement the LLM call for fixing integration tests.
                self.io.tool_error("Agent (Integration Testing): Self-correction for integration test failures is not yet fully implemented. Stopping.")
                # If we were to attempt a fix:
                # 1. Construct a detailed prompt for the LLM.
                # 2. Get code patch from LLM.
                # 3. Apply patch.
                # 4. Re-run integration tests.
                attempt += 1 # Count this as an attempt even if we don't call LLM for a fix yet.
                if attempt >= max_integration_test_retries:
                    self.io.tool_error("Agent (Integration Testing): Max retries reached.")
                    break # Exit retry loop

        if tests_passed:
            self.current_phase = "reporting"
        else:
            self.io.tool_error("Agent (Integration Testing): Integration tests failed and could not be fixed.")
            self.current_phase = "idle" 
            self.io.tool_output("Agent stopped due to integration test failures.")
        
        return self.run()

    def run_reporting_phase(self):
        """Summarizes the work and switches back to the original coder."""
        self.io.tool_output("Agent (Reporting): Task processing complete.")

        summary = ["Agent Task Summary:"]
        summary.append(f"Initial Task: {self.initial_task}")

        if self.plan and self.plan.get("deliverables"):
            summary.append("\nImplemented Deliverables:")
            for i, deliverable in enumerate(self.plan["deliverables"]):
                # Assuming all deliverables were attempted up to current_deliverable_index
                status = "Completed" if i < self.current_deliverable_index else "Not Reached"
                if self.current_phase == "idle" and i >= self.current_deliverable_index and self.current_deliverable_index < len(self.deliverables):
                    status = "Failed/Stopped" # If agent stopped mid-execution
                summary.append(f"  - {deliverable} ({status})")
        else:
            summary.append("No deliverables were planned or executed.")

        # TODO: Add more details like files changed, test results summary if available

        self.io.tool_output("\n".join(summary))
        
        self.current_phase = "idle" # Agent is done

        if self.from_coder:
            self.io.tool_output(f"Switching back to {self.from_coder.coder_name} coder.")
            # Basic switch back. A more robust solution would restore the exact state.
            # This relies on Coder.create to reinitialize from_coder appropriately.
            # We need to pass essential state like fnames, read_only_fnames, history etc.
            # The `from_coder` in SwitchCoder handles passing the instance,
            # and Coder.create uses its attributes.
            
            # Prepare kwargs to restore essential parts of the from_coder's state
            # This is a simplified restoration. A full restoration might need a dedicated
            # get_state_kwargs() method on all coders.
            kwargs_for_switch_back = {
                "fnames": list(self.from_coder.abs_fnames),
                "read_only_fnames": list(self.from_coder.abs_read_only_fnames),
                "done_messages": self.from_coder.done_messages,
                "cur_messages": self.from_coder.cur_messages,
                 # Add other relevant state that from_coder might need
            }
            if hasattr(self.from_coder, 'original_kwargs'):
                 kwargs_for_switch_back.update(self.from_coder.original_kwargs)


            raise SwitchCoder(type(self.from_coder), **kwargs_for_switch_back)
        else:
            self.io.tool_warning("Agent: No previous coder to switch back to. Agent remains idle.")
            return "Agent task finished. No previous coder to restore."

        return "Agent task finished. Switched back to previous coder."


    # Helper methods
    def _get_llm_response(self, messages, expecting_json=False):
        """ Helper to send messages to the main model and get the response content. """
        try:
            # Using send_with_retries from base Coder if available, or a simplified version
            # For AgentCoder, we might want more direct control or specific retry logic.
            # This assumes send_with_retries is a method on Coder or self.
            # If not, replace with direct self.main_model.send_completion_with_retries or similar.
            
            # Placeholder for actual LLM call logic from base_coder.py
            # This needs to be replaced with the actual call to the LLM.
            # For now, let's assume it's:
            # response = self.main_model.send_completion_with_retries(messages)
            # content = response.choices[0].message.content
            # cost = response.usage.total_tokens * some_cost_factor (simplified)
            
            # Simplified for stubbing, replace with actual call
            if hasattr(self, 'send_with_retries') and callable(getattr(self, 'send_with_retries')):
                 content, cost = self.send_with_retries(messages) # Assumes this method exists and returns (content, cost)
            elif hasattr(self.main_model, 'send_completion_with_retries') and callable(getattr(self.main_model, 'send_completion_with_retries')):
                completion = self.main_model.send_completion_with_retries(messages)
                content = completion.choices[0].message.content
                # Simplified cost calculation, replace with actual logic
                cost = (completion.usage.prompt_tokens + completion.usage.completion_tokens) * 0.000002 
            else: # Fallback if no retry mechanism found - direct call (less robust)
                completion = self.main_model.send_completion(messages, stream=False) # Assuming non-streaming for simplicity here
                content = completion.choices[0].message.content
                cost = (completion.usage.prompt_tokens + completion.usage.completion_tokens) * 0.000002


            self.total_cost += cost # Accumulate cost
            return content
        except Exception as e:
            self.io.tool_error(f"Error communicating with LLM: {e}")
            return None

    def _run_shell_command(self, command):
        """ Helper to run a shell command and return output, error, and exit code. """
        try:
            process = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=self.repo.root if self.repo else None # Run in repo root if available
            )
            return process.stdout, process.stderr, process.returncode
        except Exception as e:
            self.io.tool_error(f"Error running shell command '{command}': {e}")
            return None, str(e), -1 # Indicate error with -1 exit code

    def _parse_and_apply_edits(self, llm_response_content):
        """
        Parses LLM response for edit blocks and applies them.
        This is a simplified version. A robust implementation would handle
        different edit formats (diff, whole file, specific edit blocks)
        and interact with self.io for file writing.
        Returns a list of paths of edited files.
        """
        # This uses EditBlockCoder's logic as a helper for parsing.
        # It assumes the LLM is prompted to produce edit blocks.
        # A more generic solution would be needed for other formats.
        
        # Create a temporary EditBlockCoder instance for its parsing capabilities.
        # This is a bit of a hack; ideally, parsing logic would be more modular.
        temp_coder = EditBlockCoder(self.main_model, self.io, self.repo, from_coder=self)
        temp_coder.partial_response_content = llm_response_content
        
        try:
            edits = temp_coder.get_edits() # This will parse based on EditBlockCoder's logic
        except ValueError as e:
            self.io.tool_error(f"Could not parse edits from LLM response: {e}")
            self.io.tool_output(f"LLM Response: {llm_response_content}")
            return []

        edited_files = set()
        for path, original_content, new_content in edits:
            if path is None: # E.g. a thought block
                continue
            
            abs_path = self.abs_root_path(path)
            
            # In a real scenario, we'd check if allowed to edit, etc.
            # For this agent, we assume it has been pre-approved or will manage this.
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding=self.io.encoding) as f:
                    f.write(new_content)
                self.io.tool_output(f"Agent applied edit to: {path}")
                edited_files.add(path)
            except Exception as e:
                self.io.tool_error(f"Agent failed to write changes to {path}: {e}")
        
        return list(edited_files)


    # TODO: Add more helpers for file ops, test execution etc.
