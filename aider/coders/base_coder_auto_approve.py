from pathlib import Path
import time
import traceback
from aider.coders.chat_chunks_auto_approve import AutoApproveChatChunks
from aider.exceptions import LiteLLMExceptions
from aider.models import RETRY_TIMEOUT
from .base_coder import Coder, FinishReasonLength
from aider import prompts, utils


class ReflectionRequired(Exception):
    def __init__(self, message, append=False):
        self.append = append
        self.message = message
        super().__init__(message)


class AutoApproveCoder(Coder):
    # This AutoApproveCoder auto approves to complete task.
    # Overload check_for_file_mentions to auto approve files.

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.max_failures = 3
        self.failures = 0

    def run(self, with_message=None, preproc=True):
        """
        User puts in the task
        Coder tries to loop and complete the task within run_one
        If coder wants to ask user for more input, coder exits run_one to come back to this main loop
        """
        try:
            while True:
                try:
                    if not self.io.placeholder:
                        self.copy_context()
                    if with_message is not None:
                        self.io.user_input(with_message)
                        user_message = with_message
                        with_message = None
                    else:
                        user_message = self.get_input()

                    # Coder tries to loop and complete the task within run_one
                    # If coder wants to ask user for more input, coder exits run_one to come back to this main loop
                    self.run_one(user_message, preproc)
                    self.show_undo_hint()
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
        except EOFError:
            return
        
    def run_one(self, user_message, preproc):
        """
        Coder tries to loop to respond to user_message.
        It first preprocesses the user input, like getting files mentioned, then
        
        It loops send_message to LLM department to solve the task until there is no longer refected message (or max reflections reached)
        Currently, during this loop, there is no user message input (unless keyboard interrupt)

        send_message is a generator that yields the response from LLM department

        """
        return super().run_one(user_message, preproc)


    def send_message(self, inp):
        """
        Send message to the POC for the task.
        The POC is the main model.
        POC will response with direct solution or with request for special agents to solve subtasks it is breaking down.


        This is the core controller of the coder, including:
            - request planner, editor, and other agents to solve the task
            - apply updates to the task
            - run any shell commands/other actions
            - set reflected message if it wants to loop back to run_one for another iteration

        Coder asks 2 LLM agents (with failed retries via while loop):
            - planner/architecter (with its planning system prompt): coder send the input message for plan/updated plan (maybe can also be for a simple solution)
            - editor (with its editing system prompt): coder asks reply_completed for edit/updated edit based on the plan
            - then apply_updates to apply the edits
            - coder can set self.reflected_message at any point and return to repeat run_one (via outer run loop)
                (note: that will also ask for user input currently)
            - NOTE: currently, coder keeps planner/architect system prompt, while editor is a separate coder which its own system prompt.
                It can be cleaner to have this coder to keep its own system prompt while planner/architect is a separate coder with its own system prompt, and editor is a separate coder with its own system prompt.
                
                Right now, one boss coder who is planner/architect to control one editor coder. 
        """

        self.event("message_send_starting")

        messages = self.preprocess_input(inp)

        # 1. Message the POC --- the main model: planner/architect
        exhausted = False
        interrupted = False
        self.usage_report = None
        retry_delay = 0.125
        litellm_ex = LiteLLMExceptions()
        try:
            # while loop is only to retry sending message if having llm send exceptions
            while True:
                try:
                    yield from self.send(messages, model=self.main_model, functions=self.functions)
                    break

                # region exceptions: break if too long context window, too many retries, keyboard interrupt, hitting output limit (adding info to llm message), if other errors then raise event and return
                except litellm_ex.exceptions_tuple() as err:
                    ex_info = litellm_ex.get_ex_info(err)

                    if ex_info.name == "ContextWindowExceededError":
                        exhausted = True
                        break

                    should_retry = ex_info.retry
                    if should_retry:
                        retry_delay *= 2
                        if retry_delay > RETRY_TIMEOUT:
                            should_retry = False

                    if not should_retry:
                        self.mdstream = None
                        self.check_and_open_urls(err, ex_info.description)
                        break

                    err_msg = str(err)
                    if ex_info.description:
                        self.io.tool_warning(err_msg)
                        self.io.tool_error(ex_info.description)
                    else:
                        self.io.tool_error(err_msg)

                    self.io.tool_output(f"Retrying in {retry_delay:.1f} seconds...")
                    time.sleep(retry_delay)
                    continue
                except KeyboardInterrupt:
                    interrupted = True
                    break
                except FinishReasonLength:
                    # We hit the output limit!
                    if not self.main_model.info.get("supports_assistant_prefill"):
                        exhausted = True
                        break

                    self.multi_response_content = self.get_multi_response_content_in_progress()

                    if messages[-1]["role"] == "assistant":
                        messages[-1]["content"] = self.multi_response_content
                    else:
                        messages.append(
                            dict(role="assistant", content=self.multi_response_content, prefix=True)
                        )
                except Exception as err:
                    self.mdstream = None
                    lines = traceback.format_exception(type(err), err, err.__traceback__)
                    self.io.tool_warning("".join(lines))
                    self.io.tool_error(str(err))
                    self.event("message_send_exception", exception=str(err))
                    return
                # endregion
        finally:
            # region clean up
            if self.mdstream:
                self.live_incremental_response(True)
                self.mdstream = None

            self.partial_response_content = self.get_multi_response_content_in_progress(True)
            self.partial_response_content = self.main_model.remove_reasoning_content(
                self.partial_response_content
            )
            self.multi_response_content = ""
            # endregion

        # report usage
        self.io.tool_output()
        self.show_usage_report()

        # add assistant reply to cur messages
        self.add_assistant_reply_to_cur_messages()

        # POC agent responses with exception of token exhausted
        if exhausted:
            self.handle_exhausted_token_error()
            return
        
        # user triggers keyboard interrupt
        if interrupted:
            self.handle_keyboard_interrupted()
            return

        try:
            # set reflected_message with file mentions 
            # and next run_one's call to send_message will augment user message with file contents
            self.reflect_on_possible_file_mentions()
                
            # set reflected_message with url mentions 
            # and next run_one's call to send_message will augment user message with url contents
            self.reflect_on_possible_url_mentions()
            
            # =================
            # 2. Message Special Agents --- messages the editor llm/worker
            # POC should tell what special agents for subtasks are needed if any
            # These special agents should be running in threads either parallel or sequentially
            # And so differently from base_coder, we dont catch keyboard interrupt here - we let special agents to catch it
            self.request_special_agents() 
            # =================       

            # NOTE: all regions below add to reflected_message corresponding errors, 
            # etc. for llm to fix in the next iteration in the while loop in run_one
            
            # 3. APPLY UPDATES - by default is None - leaving editor to edit and apply updates
        
            edited = self.apply_updates()  # This could have edit errors, which will be added to reflected_message
            self.create_commit_and_reset_cur_messages(edited)

            self.fix_lint(edited)

            self.run_commands() # shell command: currently only edit_coder processes llm response to extract possible shell commands to be executed
        
            self.run_test(edited) # test commands provided by user in coder init - not by llm
        except ReflectionRequired as rr:
            if rr.append and self.reflected_message:
                self.reflected_message += "\n\n" + rr.message
            else:
                self.reflected_message = rr.message
            return
        except KeyboardInterrupt:
            self.handle_keyboard_interrupted()
            return


    def request_special_agents(self):
        """
        Request more agents to solve the task.
        For now, be default, we only request the editor coder to solve the task.
        """

        editor_model = self.main_model.editor_model or self.main_model
        self.request_editor_coder(model=editor_model)  

        
        # set your message and raise ReflectionRequired to loop back to run_one
        # reflection_message = ""
        # raise ReflectionRequired(reflection_message)

    def request_editor_coder(self, model):
        content = self.partial_response_content
        
        if not content or not content.strip():
            return

        kwargs = dict()
        editor_model = model
        
        kwargs.update({
            "main_model": editor_model,
            "edit_format": self.main_model.editor_edit_format,
            "suggest_shell_commands": False,
            "map_tokens": 0,
            "total_cost": self.total_cost,
            "cache_prompts": False,
            "num_cache_warming_pings": 0,
            "summarize_from_coder": False
        })

        new_kwargs = dict(io=self.io, from_coder=self)
        new_kwargs.update(kwargs)

        editor_coder = AutoApproveCoder.create(**new_kwargs)
        editor_coder.cur_messages = []
        editor_coder.done_messages = []

        if self.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=content, preproc=False)

        self.move_back_cur_messages("Changes applied automatically.")
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes

    def create_commit_and_reset_cur_messages(self, edited):
        if edited:
            self.aider_edited_files.update(edited) # doesn't seem to be used
            saved_message = self.auto_commit(edited)

            if not saved_message and hasattr(self.gpt_prompts, "files_content_gpt_edits_no_repo"):
                saved_message = self.gpt_prompts.files_content_gpt_edits_no_repo

            self.move_back_cur_messages(saved_message)

            if self.reflected_message:
                raise ReflectionRequired(self.reflected_message)

    def run_commands(self):
        # shell command: currently only edit_coder processes llm response to extract possible shell commands to be executed
    
        shared_output = self.run_shell_commands()
        if shared_output:
            self.cur_messages += [
                dict(role="user", content=shared_output),
                dict(role="assistant", content="Ok"),
            ]

    def run_test(self, edited):
        """
        Run tests
        """
        if edited and self.auto_test:
            test_errors = self.commands.cmd_test(self.test_cmd)
            self.test_outcome = not test_errors
            if test_errors:
                raise ReflectionRequired(test_errors)
    
    def fix_lint(self, edited):
        """
        Fix lint errors
        """
        if edited and self.auto_lint:
            lint_errors = self.lint_edited(edited)
            self.auto_commit(edited, context="Ran the linter")
            self.lint_outcome = not lint_errors
            if lint_errors:
                raise ReflectionRequired(lint_errors)

    def preprocess_input(self, inp):
        """
        Preprocesses the input message by appending it to the current messages,
        formatting the message chunks, and checking token limits.

        This method updates `self.cur_messages` with the input message and
        constructs a complete message including system prompts to be sent to
        the planner/architect. It checks if the message is within token limits
        and prepares the cache if necessary. If verbose mode is enabled, it
        displays the messages. It also initializes streaming settings for
        pretty output if required.

        Args:
            inp (str): The input message from the user to be processed.

        Returns:
            list: The formatted messages ready for the planner/architect if
            within token limits, otherwise returns None.
        """

        self.cur_messages += [
            dict(role="user", content=inp),
        ]

        # Construct the full message including system prompt, etc. to be sent to the planner/architect
        chunks = self.format_messages()
        messages = chunks.all_messages()

        if not self.check_tokens(messages):
            return
        self.warm_cache(chunks)

        if self.verbose:
            utils.show_messages(messages, functions=self.functions)

        self.multi_response_content = ""
        if self.show_pretty() and self.stream:
            self.mdstream = self.io.get_assistant_mdstream()
        else:
            self.mdstream = None

        return messages


    def reflect_on_possible_file_mentions(self):
        """
        Reflect on file mentions in the LLM's response and add them to the
        reflected_message. This method checks if the response contains a
        function call or regular text, extracts the content, and checks for
        file mentions. If file mentions are found, it adds them to the
        reflected_message. This method returns True if the reflected_message
        is modified, otherwise it returns False.
        """

        if self.partial_response_function_call:
            args = self.parse_partial_args()
            if args:
                content = args.get("explanation") or ""
            else:
                content = ""
        elif self.partial_response_content:
            content = self.partial_response_content
        else:
            content = ""

        # check for file mentions and add them to reflected_message before returning to run_one
        add_rel_files_message = self.check_for_file_mentions(content)
        if add_rel_files_message:
            raise ReflectionRequired(add_rel_files_message, append=True)
    

    def reflect_on_possible_url_mentions(self):
        # set your message and raise ReflectionRequired to loop back to run_one
        # reflection_message = ""
        # raise ReflectionRequired(reflection_message)
        pass
    

    def handle_exhausted_token_error(self) -> None:
        # Messsage is too long 
        # Add the info to cur message

        if self.cur_messages and self.cur_messages[-1]["role"] == "user":
            self.cur_messages += [
                dict(
                    role="assistant",
                    content="FinishReasonLength exception: you sent too many tokens",
                ),
            ]

        self.show_exhausted_error()
        self.num_exhausted_context_windows += 1


    def handle_keyboard_interrupted(self) -> None:
        # Keyboard interrupted during llm response
        # Add the info to cur message

        if self.cur_messages and self.cur_messages[-1]["role"] == "user":
            self.cur_messages[-1]["content"] += "\n^C KeyboardInterrupt"
        else:
            self.cur_messages += [dict(role="user", content="^C KeyboardInterrupt")]
        self.cur_messages += [
            dict(role="assistant", content="I see that you interrupted my previous reply.")
        ]


    def allowed_to_edit(self, path):
        full_path = self.abs_root_path(path)
        if self.repo:
            need_to_add = not self.repo.path_in_repo(path)
        else:
            need_to_add = False

        if full_path in self.abs_fnames:
            self.check_for_dirty_commit(path)
            return True

        if self.repo and self.repo.git_ignored_file(path):
            self.io.tool_warning(f"Skipping edits to {path} that matches gitignore spec.")
            return

        if not Path(full_path).exists():
            if not self.dry_run:
                if not utils.touch_file(full_path):
                    self.io.tool_error(f"Unable to create {path}, skipping edits.")
                    return

                # Seems unlikely that we needed to create the file, but it was
                # actually already part of the repo.
                # But let's only add if we need to, just to be safe.
                if need_to_add:
                    self.repo.repo.git.add(full_path)

            self.abs_fnames.add(full_path)
            self.check_added_files()
            return True

        if not self.io.confirm_ask(
            "Allow edits to file that has not been added to the chat?",
            subject=path,
        ):
            self.io.tool_output(f"Skipping edits to {path}")
            return

        if need_to_add:
            self.repo.repo.git.add(full_path)

        self.abs_fnames.add(full_path)
        self.check_added_files()
        self.check_for_dirty_commit(path)

        return True

    def run(self, with_message=None, preproc=True):
        try:
            if with_message:
                self.io.user_input(with_message)
                self.run_one(with_message, preproc)
                return self.partial_response_content
            while True:
                try:
                    if not self.io.placeholder:
                        self.copy_context()
                    user_message = self.get_input()
                    self.run_one(user_message, preproc)
                    self.show_undo_hint()
                except KeyboardInterrupt:
                    self.keyboard_interrupt()
        except EOFError:
            return
        
    def check_for_file_mentions(self, content):
        mentioned_rel_fnames = self.get_file_mentions(content)

        new_mentions = mentioned_rel_fnames - self.ignore_mentions

        if not new_mentions:
            return

        added_fnames = []
        for rel_fname in sorted(new_mentions):
            self.io.print(f"=====Adding file: {rel_fname}")
            self.add_rel_fname(rel_fname)
            added_fnames.append(rel_fname)

        if added_fnames:
            return prompts.added_files.format(fnames=", ".join(added_fnames))
