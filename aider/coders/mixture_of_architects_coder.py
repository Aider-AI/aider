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


class MixtureOfArchitectsCoder(Coder):
    edit_format = "mixture"
    gpt_prompts = MixturePrompts()

    def __init__(self, main_model, io, architect_models=None, **kwargs):
        super().__init__(main_model, io, **kwargs)

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

    def get_architect_response(self, architect, context):
        """Get response from individual architect with proper prompting"""
        try:
            # Add architect name to the context
            full_context = f"You are architect {architect.name.upper()}.\n\n{context}"

            # Add other architects' previous responses to the context
            other_responses = []
            for other_arch in self.architects:
                if (
                    other_arch != architect
                    and other_arch.active
                    and other_arch.last_response
                ):
                    # Extract just the proposal content from the last response
                    proposal_match = re.search(
                        r"<proposal>(.*?)</proposal>",
                        other_arch.last_response,
                        re.DOTALL,
                    )
                    if proposal_match:
                        proposal = proposal_match.group(1).strip()
                        other_responses.append(
                            f"<architect name='{other_arch.name.upper()}'>\n{proposal}\n</architect>"
                        )

            if other_responses:
                full_context += "\nPrevious proposals from other architects:\n\n"
                full_context += "\n".join(other_responses)

            # Create AskCoder with architect-specific system prompt
            ask_coder = AskCoder.create(
                main_model=architect.model,
                io=self.io,
                fnames=list(self.abs_fnames),
                read_only_fnames=list(self.abs_read_only_fnames),
                repo=self.repo,
                map_tokens=self.repo_map.max_map_tokens if self.repo_map else 0,
                summarize_from_coder=False,
                stream=False,  # Explicitly disable streaming
            )
            ask_coder.auto_commit = self.auto_commits

            # Override AskCoder's prompts with MixturePrompts
            ask_coder.gpt_prompts = MixturePrompts()

            # Run with empty message since we already set up the messages
            response = ask_coder.run(with_message=full_context, preproc=False)

            # Add debug logging
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
            # Create context for all architects
            base_context = f"User message: {user_message}\n\n"

            # Get active architects
            active_architects = [arch for arch in self.architects if arch.active]
            if not active_architects:
                self.io.tool_error("No active architects remaining!")
                return

            # Debug: Show which architects are active
            self.io.tool_output(
                f"Active architects: {[arch.name for arch in active_architects]}"
            )

            # Process architects sequentially instead of concurrently
            all_responses = {}
            for arch in active_architects:
                self.io.tool_output(f"Waiting for {arch.name}'s response...")
                try:
                    # Get response directly instead of using ThreadPoolExecutor
                    arch, response = self.get_architect_response(arch, base_context)

                    if not response.strip():
                        self.io.tool_warning(f"Empty response from {arch.name}")
                        continue

                    arch.last_response = response
                    all_responses[arch.name] = response
                    self.io.tool_output(
                        f"Received {arch.name}'s response ({len(response)} chars)"
                    )
                except Exception as e:
                    self.io.tool_error(
                        f"Failed to get response from {arch.name}: {str(e)}"
                    )

            # Show all architects' proposals after all are complete
            for arch in active_architects:
                if arch.last_response:
                    self.io.rule()
                    self.io.tool_output(f"{arch.name.upper()}'s proposal:", bold=True)
                    self.io.tool_output(f"\n{arch.last_response}\n")

            # Add final divider
            self.io.rule()
        finally:
            self.io.tool_output("Discussion round complete.")

    def preproc_user_input(self, inp):
        if not inp:
            return

        # Check for special mixture commands first
        words = inp.strip().split()
        if words:
            cmd = words[0].lower()
            args = " ".join(words[1:])

            if cmd in ["/drop", "/discuss", "/code"]:
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
        /drop <name>   - Remove an architect from the discussion
        /discuss <msg> - Start a new discussion round
        /code <msg>    - Move to implementation phase
        """
        if cmd == "drop":
            nato_name = args.strip().lower()
            for arch in self.architects:
                if arch.name == nato_name:
                    arch.active = False
                    self.io.tool_output(f"Dropped architect {nato_name}")
                    return

        elif cmd == "discuss":
            self.run_discussion_round(args)
            return

        elif cmd == "code":
            self.run_coding_phase(args)
            return

        return False

    def run_coding_phase(self, message):
        # Combine active architects' responses
        combined_response = f"User request: {message}\n\n"
        combined_response += "Based on the discussion between architects:\n\n"
        for arch in self.architects:
            if arch.active and arch.last_response:
                combined_response += (
                    f"From {arch.name.upper()}:\n{arch.last_response}\n\n"
                )

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

        new_kwargs = dict(io=self.io)
        new_kwargs.update(kwargs)

        editor_coder = Coder.create(**new_kwargs)
        editor_coder.auto_commit = self.auto_commits
        editor_coder.cur_messages = []
        editor_coder.done_messages = []

        if self.verbose:
            editor_coder.show_announcements()

        editor_coder.run(with_message=combined_response, preproc=False)

        self.move_back_cur_messages(
            "Changes have been applied based on architects' consensus."
        )
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes
