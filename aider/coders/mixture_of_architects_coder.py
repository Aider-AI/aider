import re

from aider.coders.arbiter_prompts import ArbiterPrompts
from aider.io import InputOutput
from .base_coder import Coder
from .mixture_prompts import MixturePrompts
from .ask_coder import AskCoder
from .compiler_coder import CompilerCoder


class ArbiterAgent:
    """Manages phased discussion and provides structured feedback"""
    
    def __init__(self, model, io: InputOutput, discussion_messages, stream,verbose):
        self.model = model
        self.phases = ["brainstorm", "critique", "optimize"]
        self.current_phase = "brainstorm"
        self.name = "arbiter"
        self.color = "yellow"
        self.io = io
        self.stream = stream
        self.verbose = verbose

        self.gpt_prompts = None
        self.discussion_messages = discussion_messages
    
    def build_context_for_coder(self, target_coder):
        """Reuse the message formatting logic from get_architect_response"""
        for msg in self.discussion_messages:
            if target_coder.cur_messages:
                last_msg_is_user = target_coder.cur_messages[-1]["role"] == "user"
            else:
                last_msg_is_user = False

            match msg["role"]:
                case "user":
                    fenced_content = f"<user_message>\n{msg['content']}\n</user_message>\n\n"
                    if last_msg_is_user:
                        target_coder.cur_messages[-1]["content"] += fenced_content
                    else:
                        target_coder.cur_messages.append({"role": "user", "content": fenced_content})
                case "assistant":
                    if msg.get("name") == "ARBITER":
                        target_coder.cur_messages.append({"role": "assistant", "content": msg["content"]})
                    else:
                        content = extract_proposal_content(msg["content"], msg.get("name", "unknown"), False)
                        if last_msg_is_user:
                            target_coder.cur_messages[-1]["content"] += content
                        else:
                            target_coder.cur_messages.append({"role": "user", "content": content})

    def get_phase(self):
        """Get current phase name."""
        return self.current_phase
    
    def get_next_phase(self):
        """Get the name of the next phase without advancing."""
        current_idx = self.phases.index(self.current_phase)
        if current_idx < len(self.phases) - 1:
            return self.phases[current_idx + 1]
        return self.current_phase
    
    def advance_phase(self):
        """Advance to next phase and return the new phase name."""
        current_idx = self.phases.index(self.current_phase)
        if current_idx < len(self.phases) - 1:
            next_phase = self.phases[current_idx + 1]
            self.current_phase = next_phase
            return next_phase
        return None
    
    def generate_round_feedback(self):
        """Generate arbiter message with targeted feedback."""
        ask_coder = AskCoder.create(
            main_model=self.model,
            io=self.io,
            fnames=[],
            read_only_fnames=[],
            repo=None,
            map_tokens=0,
            summarize_from_coder=False,
            stream=self.stream,
            verbose=self.verbose,
        )
        ask_coder.auto_commits = False
        ask_coder.gpt_prompts = ArbiterPrompts()
        self.build_context_for_coder(ask_coder)

        prompt = f"""Current phase: {self.get_phase()}
        Generate feedback for architects based on the current discussion.
        """

        response = ask_coder.run(with_message=prompt, preproc=False)

        return response.strip()
    
    def generate_phase_summary(self):
        """Generate summary of the current phase before transition."""
        ask_coder = AskCoder.create(
            main_model=self.model,
            io=self.io,
            fnames=[],
            read_only_fnames=[],
            repo=None,
            map_tokens=0,
            summarize_from_coder=False,
            stream=self.stream,
            verbose=self.verbose,
        )
        ask_coder.auto_commits = False
        ask_coder.gpt_prompts = ArbiterPrompts()
        self.build_context_for_coder(ask_coder)

        prompt = f"""
        Generate phase summary for: {self.current_phase}
        """

        response = ask_coder.run(with_message=prompt, preproc=False)
        return response.strip()


    def get_arbiter_verdict(self, responses):
        """Determine if phase should advance based on responses."""
        ask_coder = AskCoder.create(
            main_model=self.model,
            io=self.io,
            fnames=[],
            read_only_fnames=[],
            repo=None,
            map_tokens=0,
            summarize_from_coder=False,
            stream=False,
            verbose=False,
        )
        ask_coder.auto_commits = False
        ask_coder.gpt_prompts = ArbiterPrompts()
        self.build_context_for_coder(ask_coder)

        prompt = f"""Review the current {self.get_phase()} phase discussion and determine if ready to advance.
        
        Consider:
        1. Clear consensus on core solution aspects
        2. Resolution of major conflicts
        3. Existence of mergeable proposal components
        4. Would moving to {self.get_next_phase()} phase be productive?
        
        Respond with either:
        <verdict>advance</verdict> - if ready to move to next phase
        <verdict>continue</verdict> - if more discussion needed in current phase
        
        Explain your decision in <reason> tags.
        
        Discussion context:
        {"\n".join(responses)}"""

        response = ask_coder.run(with_message=prompt, preproc=False)
        
        # Extract and show reasoning
        reason_match = re.search(r"<reason>(.*?)</reason>", response, re.DOTALL)
        if reason_match:
            self.io.tool_output("\nArbiter's phase decision:", bold=True)
            self.io.tool_output(reason_match.group(1).strip(), color=self.color)

        if "<verdict>advance</verdict>" in response:
            return "advance"
        return "continue"

class ArchitectAgent:
    def __init__(self, name, model):
        self.name = name  # NATO name (alpha, bravo, etc)
        self.model = model
        self.active = True
        self.last_response: str | None = None


def extract_proposal_content(content, name, is_architect = True):
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

    if is_architect:
        return f"<architect name='{name}'>\n{proposal_content}\n</architect>\n\n"
    else:
        return f"<{name}>{proposal_content}</{name}>"


class MixtureOfArchitectsCoder(Coder):
    edit_format = "mixture"
    gpt_prompts = MixturePrompts()

    def __init__(self, main_model, io, architect_models=None, **kwargs):
        super().__init__(main_model, io, **kwargs)
        
        # Add conversation history tracking
        self.discussion_messages = []  # List to store the full conversation

        # Add arbiter component
        self.arbiter = ArbiterAgent(main_model, self.io, self.discussion_messages, self.stream, self.verbose,)

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
                verbose=self.verbose,
            )
            ask_coder.auto_commits = self.auto_commits
            ask_coder.gpt_prompts = MixturePrompts()

            for msg in self.discussion_messages:
                if ask_coder.cur_messages:
                    last_msg_is_user = ask_coder.cur_messages[-1]["role"] == "user"
                else:
                    last_msg_is_user = False

                match msg["role"]:
                    case "user":
                        fenced_content = (
                            f"<user_message>\n{msg['content']}\n</user_message>\n\n"
                        )
                        if last_msg_is_user:
                            latest_user_content = ask_coder.cur_messages[-1]["content"]
                            latest_user_content += fenced_content
                            ask_coder.cur_messages[-1]["content"] = latest_user_content
                        else:
                            ask_coder.cur_messages.append(
                                {"role": "user", "content": fenced_content}
                            )
                    case "assistant":
                        # If its the current architect, then we use role=assistant
                        if msg["name"] == architect.name.upper() or msg["name"] == "ANY":
                            ask_coder.cur_messages.append(
                                {"role": "assistant", "content": msg["content"]}
                            )
                        else:
                            # If the not current architect, then we inject in user side
                            # append to the last user message
                            if last_msg_is_user:

                                latest_user_content = ask_coder.cur_messages[-1][
                                    "content"
                                ]
                                latest_user_content += extract_proposal_content(
                                    msg["content"], msg["name"]
                                )
                                ask_coder.cur_messages[-1][
                                    "content"
                                ] = latest_user_content
                            # or create a new user message
                            else:
                                ask_coder.cur_messages.append(
                                    {
                                        "role": "user",
                                        "content": extract_proposal_content(
                                            msg["content"], msg["name"]
                                        ),
                                    }
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
            if ask_coder.cur_messages[-1].get("role") == "user":
                architect_assignment = f""" You are architect {architect.name}"""
                ask_coder.cur_messages[-1]["content"] += architect_assignment
                ask_coder.cur_messages.append(
                    {"role": "assistant", "content": f"I am architect {architect.name}"}
                )
            formatted_message = (
                f"<user_message>\n{current_user_message}\n</user_message>"
            )

            response = ask_coder.run(with_message=formatted_message, preproc=False)

            if not response.strip():
                self.io.tool_warning(f"Warning: Empty response from {architect.name}")

            return architect, response

        except Exception as e:
            self.io.tool_error(
                f"Error getting response from {architect.name}: {str(e)}"
            )
            return architect, f"Error: {str(e)}"


    def run_arbiter(self, user_message):
        try:
            initial_message = user_message
            # Store initial user message
            self.discussion_messages.append({"role": "user", "content": initial_message})
            
            while True:  # Outer loop - continues until all phases complete
                phase = self.arbiter.get_phase()
                is_final_phase = phase == self.arbiter.phases[-1]
                
                phase_prompt = self.gpt_prompts.phase_prompts[phase]
                phase_message = f"""## Phase Context: {phase.capitalize()}
                {phase_prompt}
### User Request:
                {initial_message}"""
                
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
                
                while True:  # Inner loop - continues until phase advances
                    responses = []
                    architect_names = []
                    
                    # Process architects sequentially
                    for arch in active_architects:
                        self.io.tool_output(f"{arch.name}'s response...", bold=True)
                        self.io.rule()
                        try:
                            arch, response = self.get_architect_response(arch, phase_message)
                            responses.append(response)
                            architect_names.append(arch.name)

                            if not response.strip():
                                self.io.tool_warning(f"Empty response from {arch.name}")
                                continue

                            arch.last_response = response
                            self.discussion_messages.append({
                                "role": "assistant",
                                "name": arch.name.upper(),
                                "content": response,
                            })

                            self.io.tool_output(
                                f"Received {arch.name}'s response ({len(response)} chars)"
                            )
                        except Exception as e:
                            self.io.tool_error(
                                f"Failed to get response from {arch.name}: {str(e)}"
                            )

                        # Show architect's proposal immediately if verbose
                        if self.verbose and arch.last_response:
                            self.io.rule()
                            self.io.tool_output(f"{arch.name.upper()}'s Response:", bold=True)
                            self.io.tool_output(f"\n{arch.last_response}\n")

                    # Single arbiter feedback at end of round
                    self.io.tool_output("\nArbiter's Round Feedback:", bold=True)
                    self.arbiter.discussion_messages = self.discussion_messages
                    arbiter_feedback = self.arbiter.generate_round_feedback()
                    if arbiter_feedback.strip():
                        # self.io.tool_output("=== ARBITER FEEDBACK ===", color=self.arbiter.color)
                        self.discussion_messages.append({
                            "role": "assistant",
                            "name": "ARBITER",
                            "content": arbiter_feedback
                        })
                        # self.io.tool_output(arbiter_feedback, color=self.arbiter.color)
                        # self.io.tool_output("=== END FEEDBACK ===", color=self.arbiter.color)
                    
                    # Get arbiter verdict for phase advancement
                    self.io.tool_output("\nArbiter's Verdict:", bold=True)
                    verdict = self.arbiter.get_arbiter_verdict(responses)
                    if verdict == "advance":

                        self.io.tool_output("\nArbiter's Summary:", bold=True)
                        transition_message = self.arbiter.generate_phase_summary()
                        
                        # Announce phase completion and transition
                        self.io.tool_output("\nPhase Transition", bold=True)
                        self.io.tool_output("=" * 40, color=self.arbiter.color)
                        self.io.tool_output(f"Completing {self.arbiter.current_phase} phase", color=self.arbiter.color)
                        
                        next_phase = self.arbiter.get_next_phase()
                        if next_phase != self.arbiter.current_phase:
                            self.io.tool_output(f"Moving to {next_phase} phase", bold=True, color=self.arbiter.color)
                        else:
                            self.io.tool_output("Remaining in final phase", color=self.arbiter.color)
                        self.io.tool_output("=" * 40, color=self.arbiter.color)
                        
                        # Store transition in discussion history
                        self.discussion_messages.append({
                            "role": "assistant",
                            "name": "ARBITER",
                            "content": f"""<phase_transition>
                                {transition_message}
                                Moving from {self.arbiter.current_phase} to {next_phase} phase.
                                </phase_transition>"""
                        })
                        
                        self.arbiter.advance_phase()
                        
                        # If we completed the final phase, exit both loops
                        if is_final_phase:
                            # Yes is proxy for auto running code, As proxy for benchmarking
                            # TODO: Replace with a better testing strategy
                            if self.io.yes:
                                self.run_coding_phase("lets implement best simplest solution")

                            return
                        
                        # Break inner loop to move to next phase
                        break
                    else:
                        # Continue in current phase for another round of responses
                        continue
                
                # Add final divider between phases
                self.io.rule()
                
        finally:
            self.io.tool_output("All phases complete.")

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
                self.io.tool_output(f"{arch.name}'s response...", bold=True)
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
            self.run_coding_phase("lets implement best simplest solution")

    def preproc_user_input(self, inp):
        if not inp:
            return

        # Check for special mixture commands first
        words = inp.strip().split()
        if words:
            cmd = words[0].lower()
            args = " ".join(words[1:])

            if cmd in ["/ignore", "/discuss", "/code", "/clear", "/reset", "/arbiter",]:
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
        /arbiter <msg> - Start a new arbitrated round
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

        elif cmd == "arbiter":
            self.run_arbiter(args)
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
                    "content": f"{message}",
                }
            )

        # Create compiler coder instance
        compiler_coder = CompilerCoder(
            main_model=self.main_model.editor_model or self.main_model,
            io=self.io,
            fnames=list(self.abs_fnames),
            read_only_fnames=list(self.abs_read_only_fnames),
            repo=self.repo,
            map_tokens=0,
            stream=self.stream,
        )
        compiler_coder.auto_commits = self.auto_commits

        # Format the conversation for the compiler
        compiler_input = "Please compile the following architects' proposals into implementation instructions:\n\n"
        for msg in self.discussion_messages:
            if msg["role"] == "user":
                compiler_input += "<user_message>\n"
                compiler_input += msg["content"]
                compiler_input += "\n</user_message>\n\n"
            else:
                compiler_input += f"<architect name='{msg['name']}'>\n"
                compiler_input += msg["content"]
                compiler_input += "\n</architect>\n\n"

        # Get compiled instructions
        self.io.tool_output("Compiler's instructions", bold=True)
        self.io.rule()
        compiler_coder.run(with_message=compiler_input, preproc=False)
        compiled_instructions = compiler_coder.partial_response_content
        compiled_instructions += "\n\nCompletely implement all steps in the instructions above. Do not return to me until you have done so."

        # Debug print the compiled instructions
        if self.verbose:
            self.io.tool_output("\nDebug: Compiled instructions being sent to editor:")
            self.io.tool_output("-" * 40)
            self.io.tool_output(compiled_instructions)
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
        kwargs["verbose"] = self.verbose

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

        self.io.tool_output("Coder's output", bold=True)
        self.io.rule()
        editor_coder.run(with_message=compiled_instructions, preproc=False)


        # Inject implementation notice to discussion
        self.discussion_messages.append(
            {
                "role": "user",
                "content": "We have implemented the plan. Refer to the latest code state",
            }
        )
        self.discussion_messages.append(
            {
                "role": "assistant",
                "name": "ANY",
                "content": "Okay, i'll refer to the latest code state",
            }
        )


        self.move_back_cur_messages(
            "Changes have been applied based on architects' consensus."
        )
        self.total_cost = editor_coder.total_cost
        self.aider_commit_hashes = editor_coder.aider_commit_hashes
