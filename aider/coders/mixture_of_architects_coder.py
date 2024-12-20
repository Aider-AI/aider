import re
from .base_coder import Coder
from .mixture_prompts import MixturePrompts
from .ask_coder import AskCoder


class ArchitectAgent:
    def __init__(self, name, model):
        self.name = name  # NATO name (alpha, bravo, etc)
        self.model = model
        self.active = True
        self.last_response: str | None = None


def extract_proposal_content(content, architect_name):
    """
    Extracts proposal content from the given content string.

    Args:
        content: The string content to extract from.
        architect_name: The name of the architect.

    Returns:
        A string containing the extracted proposal content,
        wrapped in <architect name='...'> tags.
    """
    # Try to get properly fenced content first
    proposal_match = re.search(r"<proposal>(.*?)</proposal>", content, re.DOTALL)
    if proposal_match:
        proposal_content = proposal_match.group(1).strip()
    else:
        # Fallback: Try to get content after <proposal> tag
        proposal_start = content.find("<proposal>")
        if proposal_start != -1:
            proposal_content = content[proposal_start + len("<proposal>") :].strip()
        else:
            # Last resort: Use the entire response
            proposal_content = content.strip()

    return f"<architect name='{architect_name}'>\n{proposal_content}\n</architect>\n\n"


class MixtureOfArchitectsCoder(Coder):
    edit_format = "mixture"
    gpt_prompts = MixturePrompts()

    def __init__(self, main_model, io, architect_models=None, **kwargs):
        super().__init__(main_model, io, **kwargs)

        # Add conversation history tracking
        self.discussion_messages = []  # List to store the full conversation

        # The main_model is always the first architect (alpha)
        self.architects = [ArchitectAgent("alpha", main_model)]

        # Add additional architect models with NATO names
        nato_names = ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel"]
        if architect_models:
            for i, amodel in enumerate(architect_models):
                name = nato_names[i] if i < len(nato_names) else f"agent{i+2}"
                self.architects.append(ArchitectAgent(name, amodel))

    def get_architect_prompt(self, architect):
        """Get the system prompt customized for this architect"""
        prompt = self.gpt_prompts.main_system.format(
            architect_name=architect.name.upper(),
            language=self.chat_language or "the same language they are using",
        )
        return prompt

    def get_architect_response(self, architect, current_user_message):
        """Get response from individual architect with proper prompting"""
        try:
            # Create and configure AskCoder
            ask_coder = AskCoder.create(
                main_model=architect.model,
                io=self.io,
                fnames=list(self.abs_fnames),
                read_only_fnames=list(self.abs_read_only_fnames),
                repo=self.repo,
                map_tokens=self.repo_map.max_map_tokens if self.repo_map else 0,
                summarize_from_coder=False,
                stream=self.stream,
            )
            ask_coder.auto_commits = self.auto_commits
            ask_coder.gpt_prompts = MixturePrompts()

            # Group messages by conversation round
            rounds = []
            current_round = []
            for msg in self.discussion_messages:
                if msg["role"] == "user":
                    if current_round:
                        rounds.append(current_round)
                    current_round = [msg]
                else:
                    current_round.append(msg)
            if current_round:
                rounds.append(current_round)

            # Build the conversation messages
            for round_msgs in rounds:
                user_msg = next(msg for msg in round_msgs if msg["role"] == "user")

                # Combine user message with other architects' proposals
                user_content = "<user_message>\n"
                user_content += user_msg["content"]
                user_content += "\n</user_message>\n\n"

                # Add other architects' proposals from this round
                for msg in round_msgs:
                    if (
                        msg["role"] == "assistant"
                        and msg["name"] != architect.name.upper()
                    ):
                        # Use the helper function to extract proposal content
                        user_content += extract_proposal_content(
                            msg["content"], msg["name"]
                        )

                ask_coder.cur_messages.append({"role": "user", "content": user_content})

                # Add this architect's own response if they had one
                for msg in round_msgs:
                    if (
                        msg["role"] == "assistant"
                        and msg["name"] == architect.name.upper()
                    ):
                        ask_coder.cur_messages.append(
                            {"role": "assistant", "content": msg["content"]}
                        )

            # Debug output if verbose
            if self.verbose:

                self.io.rule()
                self.io.tool_output(
                    f"\nDebug: Messages being sent to {architect.name}:", bold=True
                )
                self.io.tool_output("-" * 40)
                for msg in ask_coder.cur_messages:
                    self.io.tool_output(f"{msg['role'].upper()}:")
                    self.io.tool_output(msg["content"])
                    self.io.tool_output("-" * 40)

            # Pass the current message with XML tags as with_message
            formatted_message = f"""
                You are arhitect {architect.name}
                <user_message>
                {current_user_message}
                </user_message>"""
            response = ask_coder.run(with_message=formatted_message, preproc=False)

            if not response.strip():
                self.io.tool_warning(f"Warning: Empty response from {architect.name}")

            return architect, response

        except Exception as e:
            self.io.tool_error(
                f"Error getting response from {architect.name}: {str(e)}"
            )
            return architect, f"Error: {str(e)}"

    def run_discussion_round(self, user_message):
        try:
            # Store user message
            self.discussion_messages.append({"role": "user", "content": user_message})

            # Get active architects
            active_architects = [arch for arch in self.architects if arch.active]
            if not active_architects:
                self.io.tool_error("No active architects remaining!")
                return

            # Debug: Show which architects are active
            self.io.rule()
            self.io.tool_output(
                f"Active architects: {[arch.name for arch in active_architects]}"
            )

            # Process architects sequentially instead of concurrently
            for arch in active_architects:
                self.io.tool_output(f"Waiting for {arch.name}'s response...", bold=True)
                self.io.rule()
                try:
                    arch, response = self.get_architect_response(arch, user_message)

                    if not response.strip():
                        self.io.tool_warning(f"Empty response from {arch.name}")
                        continue

                    arch.last_response = response
                    # Store architect's response in discussion history
                    self.discussion_messages.append(
                        {
                            "role": "assistant",
                            "name": arch.name.upper(),
                            "content": response,
                        }
                    )

                    self.io.tool_output(
                        f"Received {arch.name}'s response ({len(response)} chars)"
                    )
                except Exception as e:
                    self.io.tool_error(
                        f"Failed to get response from {arch.name}: {str(e)}"
                    )

                # Show architect's proposal immediately
                if self.verbose and arch.last_response:
                    self.io.rule()
                    self.io.tool_output(f"{arch.name.upper()}'s Response:", bold=True)
                    self.io.tool_output(f"\n{arch.last_response}\n")

            # Add final divider
            self.io.rule()
        finally:
            self.io.tool_output("Discussion round complete.")
        # Yes is proxy for auto running code, As proxy for benchmarking
        # TODO: Replace with a better testing strategy
        if self.io.yes:
            self.run_coding_phase(user_message)

    def preproc_user_input(self, inp):
        if not inp:
            return

        # Check for special mixture commands first
        words = inp.strip().split()
        if words:
            cmd = words[0].lower()
            args = " ".join(words[1:])

            if cmd in ["/ignore", "/discuss", "/code", "/clear", "/reset"]:
                cmd = cmd[1:]  # strip the /
                return self.handle_discussion_commands(cmd, args)

        # Fall back to normal command processing
        return super().preproc_user_input(inp)

    def run_one(self, user_message, preproc):
        self.init_before_message()

        if preproc:
            message = self.preproc_user_input(user_message)
        else:
            message = user_message

        # If no special command was handled, treat as discussion by default
        if message:
            self.run_discussion_round(message)

    def handle_discussion_commands(self, cmd, args):
        """
        Handle special mixture of architects commands:
        /ignore <name>  - Remove an architect from the discussion
        /discuss <msg> - Start a new discussion round
        /code <msg>    - Move to implementation phase
        /clear        - Clear chat and discussion history
        /reset        - Drop files and clear all history
        """
        if cmd == "clear":
            self.discussion_messages = []
            self.io.tool_output("Chat history and discussion history cleared.")
            return
        elif cmd == "reset":
            self.abs_fnames = set()
            self.abs_read_only_fnames = set()
            self.discussion_messages = []
            self.io.tool_output(
                "All files dropped, chat history and discussion history cleared."
            )
            return
        elif cmd == "ignore":
            nato_name = args.strip().lower()
            for arch in self.architects:
                if arch.name == nato_name:
                    arch.active = False
                    self.io.tool_output(f"Ignored architect {nato_name}")
                    return

        elif cmd == "discuss":
            self.run_discussion_round(args)
            return

        elif cmd == "code":
            self.run_coding_phase(args)
            return

        return False

    def run_coding_phase(self, message):
        # Add the final code implementation request to the discussion
        if message.strip():
            self.discussion_messages.append(
                {
                    "role": "user",
                    "content": f"Please implement the following: {message}",
                }
            )

        # Format the full conversation history with XML fences
        combined_response = "Full discussion history:\n\n"
        for msg in self.discussion_messages:
            if msg["role"] == "user":
                combined_response += "<user_message>\n"
                combined_response += msg["content"]
                combined_response += "\n</user_message>\n\n"
            else:
                combined_response += f"<architect name='{msg['name']}'>\n"
                combined_response += msg["content"]
                combined_response += f"\n</architect>\n\n"

        combined_response += (
            "\nBased on the above discussion, please implement the requested changes."
        )

        # Debug print the combined response
        if self.verbose:
            self.io.tool_output("\nDebug: Combined response being sent to editor:")
            self.io.tool_output("-" * 40)
            self.io.tool_output(combined_response)
            self.io.tool_output("-" * 40 + "\n")

        # Use editor coder like ArchitectCoder does
        kwargs = dict()
        editor_model = self.main_model.editor_model or self.main_model
        kwargs["main_model"] = editor_model
        kwargs["edit_format"] = self.main_model.editor_edit_format
        kwargs["suggest_shell_commands"] = False
        kwargs["map_tokens"] = 0
        kwargs["total_cost"] = self.total_cost
        kwargs["cache_prompts"] = False
        kwargs["num_cache_warming_pings"] = 0
        kwargs["summarize_from_coder"] = False
        kwargs["stream"] = self.stream
        kwargs["auto_commits"] = self.auto_commits

        new_kwargs = dict(io=self.io)
        new_kwargs.update(kwargs)

        editor_coder = Coder.create(**new_kwargs)
        editor_coder.abs_fnames = set(self.abs_fnames)
        editor_coder.abs_read_only_fnames = set(self.abs_read_only_fnames)
        editor_coder.auto_commits = self.auto_commits
        editor_coder.cur_messages = []
        editor_coder.done_messages = []
        editor_coder.repo = self.repo

        if self.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=combined_response, preproc=False)

        self.move_back_cur_messages(
            "Changes have been applied based on architects' consensus."
        )
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes
