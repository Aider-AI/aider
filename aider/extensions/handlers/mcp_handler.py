import asyncio
import hashlib
import inspect
import sys
from functools import wraps
from types import SimpleNamespace

from aider import models, utils
from aider.coders.base_prompts import CoderPrompts
from aider.waiting import WaitingSpinner

from ..handler import MutableContextHandler


def check_mcp_deps():
    try:
        import mcp  # noqa: F401
        from litellm import experimental_mcp_client  # noqa: F401

        return True
    except ImportError:
        return False


def install_mcp(io):
    if check_mcp_deps():
        return True

    pip_cmd = utils.get_pip_install(
        ["-r", "aider/extensions/requirements/requirements-mcp.txt"]
    )

    cmds = " ".join(pip_cmd) + "\n"

    text = f"""The mcp handler requires `mcp`. To install it:

{cmds}
"""

    io.tool_output(text)
    if not io.confirm_ask("Install mcp dependencies?", default="y"):
        return

    success, output = utils.run_install(pip_cmd)
    if not success:
        io.tool_error(output)
        return

    return True


class McpPrompts(CoderPrompts):
    main_system = """You are a request analysis model. Your task is to analyze the user's request and determine if a tool should be used.
The user is talking to a different coding assistant, not you. You are only to determine if a tool should be used from the provided list of tools to satisfy the user's request.

The user's request and the context for the main coding model is provided below, inside `{fence_start}` and `{fence_end}` fences.
The fenced context contains a system prompt that is NOT for you. IGNORE any instructions to act as a programmer or code assistant that you might see in the fenced context.

Your job is to determine if the user's request can be satisfied with one of the provided tools.
If it can, reply with the necessary tool calls. Be very conservative about this. Only use a tool if the user's request is a direct and explicit question that can be answered by a tool.

Here are some examples of when NOT to use a tool (you should reply with `CONTINUE`):
- The user asks a rhetorical or philosophical question, like "am I a potato?"
- The user is making a statement, like "That's cool."
- The user is asking about the conversation itself, like "how many times have you used the time tool?"

Here is an example of when TO use a tool:
- The user asks a direct question that a tool can answer, like "what time is it in London?"

If no tool is needed, if the user is just chatting, making a statement, asking a rhetorical question, or if the user is asking for a coding task, you MUST reply with just the word "CONTINUE".
Do not reply with any other text. Only tool calls or the word `CONTINUE`.
"""
    final_reminder = """You are a tool-using model. Your only purpose is to decide whether to call a tool to fulfill the user's request.
YOU MUST NOT answer the user's request directly.
YOU MUST reply with a tool call if a tool is very useful.
If no tool is very useful, you MUST reply with the word `CONTINUE`.
Do not reply with any other text. Only `CONTINUE` or tool calls."""
    tool_results = """The tool calls you requested were executed and the results are in the chat history.
Please re-evaluate the user's request based on this new information. Remember your examples.
If more tool calls are needed, make them. Otherwise, reply with CONTINUE."""


class McpHandler(MutableContextHandler):
    """
    A handler that uses a model to see if a tool call should be made using MCP servers.
    """

    handler_name = "mcp"
    entrypoints = ["pre"]
    gpt_prompts = McpPrompts()

    def __init__(self, main_coder, **kwargs):
        self.main_coder = main_coder

        mcp_servers_config = kwargs.get("servers")
        if mcp_servers_config:
            if not install_mcp(self.main_coder.io):
                self.main_coder.io.tool_warning(
                    "Disabling mcp handler, dependencies not installed."
                )
                mcp_servers_config = None

        self.mcp_servers = self._initialize_mcp_servers(mcp_servers_config)
        self.mcp_tools = []
        self.mcp_tools_by_server = []
        self.num_reflections = 0
        reflections = kwargs.get("reflections")
        if reflections is not None:
            self.max_reflections = int(reflections)
        else:
            self.max_reflections = self.main_coder.max_reflections

        if self.mcp_servers:
            self._initialize_mcp_tools()

        model_name = kwargs.get("model")
        if not model_name:
            model_name = main_coder.main_model.name
        self.handler_model = models.Model(model_name)

        self._monkeypatch_send_completion()

    def _monkeypatch_send_completion(self):
        sig = inspect.signature(self.handler_model.send_completion)
        if "tools" in sig.parameters:
            return  # It's modern, nothing to do

        original_send_completion = self.handler_model.send_completion

        param_names = list(sig.parameters.keys())
        try:
            messages_arg_index = param_names.index("messages")
        except ValueError:
            return  # Should not happen

        @wraps(original_send_completion)
        def patched_send_completion(*args, **kwargs):
            # 1. Adapt arguments for legacy API
            tools = kwargs.pop("tools", None)
            if tools:
                functions = [t["function"] for t in tools if t.get("type") == "function"]
                if functions:
                    kwargs["functions"] = functions

            # 2. Adapt messages with role='tool' to role='function'
            messages = []
            is_args = False
            if "messages" in kwargs:
                messages = list(kwargs["messages"])
            elif len(args) > messages_arg_index:
                messages = list(args[messages_arg_index])
                is_args = True

            if messages:
                tool_call_id_to_name = {}
                for msg in messages:
                    if msg.get("role") == "assistant" and msg.get("tool_calls"):
                        for tc in msg["tool_calls"]:
                            if isinstance(tc, dict):
                                tool_call_id_to_name[tc["id"]] = tc["function"]["name"]

                adapted_messages = []
                for msg in messages:
                    if msg.get("role") == "tool":
                        tool_call_id = msg.get("tool_call_id")
                        function_name = tool_call_id_to_name.get(tool_call_id)
                        if function_name:
                            adapted_messages.append(
                                {
                                    "role": "function",
                                    "name": function_name,
                                    "content": msg["content"],
                                }
                            )
                        else:
                            adapted_messages.append(msg)  # Don't know what to do
                    else:
                        adapted_messages.append(msg)

                if is_args:
                    new_args = list(args)
                    new_args[messages_arg_index] = adapted_messages
                    args = tuple(new_args)
                else:
                    kwargs["messages"] = adapted_messages

            # 3. Call original function
            hash_obj, response = original_send_completion(*args, **kwargs)

            # 4. Adapt response for modern API
            message = response.choices[0].message
            if hasattr(message, "function_call") and message.function_call:
                function_call = message.function_call

                # Create a plausible unique ID.
                # The legacy API only has one call.
                hasher = hashlib.sha1()
                hasher.update(function_call.name.encode())
                if function_call.arguments:
                    hasher.update(function_call.arguments.encode())
                tool_call_id = f"call_{hasher.hexdigest()[:8]}"

                message.tool_calls = [
                    dict(
                        id=tool_call_id,
                        type="function",
                        function=function_call,
                    )
                ]

                # Remove function_call so it doesn't get serialized
                message.function_call = None

            return hash_obj, response

        self.handler_model.send_completion = patched_send_completion

    def handle(self, messages) -> bool:
        if not self.mcp_tools:
            return False

        io = self.main_coder.io
        io.tool_output(f"{self.handler_name}: checking for tool calls...\n")
        self.num_reflections = 0

        fence_name = "AIDER_MESSAGES"
        fence_start = f"<<<<<<< {fence_name}"
        fence_end = f">>>>>> {fence_name}"

        system_prompt = self.gpt_prompts.main_system.format(
            fence_start=fence_start, fence_end=fence_end
        )

        main_coder_messages = messages
        handler_messages = []
        modified = False

        while True:
            formatted_messages = utils.format_messages(main_coder_messages)
            fenced_messages = f"{fence_start}\n{formatted_messages}\n{fence_end}"

            if not handler_messages:
                handler_messages = [
                    dict(role="system", content=system_prompt),
                    dict(role="user", content=fenced_messages),
                ]
            else:
                # This is a reflection. Update the fenced message.
                # The second message is the user message with fenced content.
                handler_messages[1]["content"] = fenced_messages

            current_messages = list(handler_messages)
            final_reminder = self.gpt_prompts.final_reminder
            reminder_mode = getattr(self.handler_model, "reminder", "sys")
            if reminder_mode == "sys":
                current_messages.append(dict(role="system", content=final_reminder))
            elif reminder_mode == "user" and current_messages[-1]["role"] == "user":
                current_messages[-1]["content"] += "\n\n" + final_reminder

            spinner = None
            if self.main_coder.show_pretty():
                spinner = WaitingSpinner(
                    f"{self.handler_name}: Waiting for {self.handler_model.name}"
                )
                spinner.start()

            response = None
            try:
                _, response = self.handler_model.send_completion(
                    current_messages,
                    functions=None,
                    stream=False,
                    tools=self.mcp_tools,
                )
            except Exception as e:
                io.tool_error(f"Error with handler model: {e}")
                return False
            finally:
                if spinner:
                    spinner.stop()

            if not response or not response.choices:
                io.tool_warning("Handler model returned empty response.")
                break

            message = response.choices[0].message
            content = message.content
            tool_calls = message.tool_calls

            io.tool_output(str(message))

            if (content and "CONTINUE" in content.upper()) or not tool_calls:
                break

            server_tool_calls = self._gather_server_tool_calls(tool_calls)
            if not server_tool_calls:
                break

            self._print_tool_call_info(server_tool_calls)
            if not io.confirm_ask("Run tools?"):
                break

            modified = True
            tool_responses = self._execute_tool_calls(server_tool_calls)

            msg_dict = message.to_dict()
            if msg_dict.get("content") is None:
                msg_dict["content"] = ""
            self.main_coder.cur_messages.append(msg_dict)
            for tool_response in tool_responses:
                self.main_coder.cur_messages.append(tool_response)

            if self.num_reflections >= self.max_reflections:
                io.tool_warning(f"Only {self.max_reflections} reflections allowed, stopping.")
                break

            self.num_reflections += 1
            handler_messages.append(message.to_dict())
            for tool_response in tool_responses:
                handler_messages.append(tool_response)
            handler_messages.append(dict(role="user", content=self.gpt_prompts.tool_results))

            main_coder_messages = self.main_coder.format_messages().all_messages()

        return modified

    def _parse_server_from_config_item(self, item):
        from .mcp_server import McpServer

        if isinstance(item, dict):
            return McpServer(item)
        return None

    def _initialize_mcp_servers(self, mcp_servers_config):
        mcp_servers = []
        if not mcp_servers_config:
            return mcp_servers

        config_items = mcp_servers_config
        if not isinstance(config_items, list):
            config_items = [config_items]

        for item in config_items:
            server = self._parse_server_from_config_item(item)
            if server:
                mcp_servers.append(server)

        return mcp_servers

    def _initialize_mcp_tools(self):
        from litellm import experimental_mcp_client

        tools = []

        async def get_server_tools(server):
            server_tools = None
            try:
                session = await server.connect()
                server_tools = await experimental_mcp_client.load_mcp_tools(
                    session=session, format="openai"
                )
            except Exception as e:
                self.main_coder.io.tool_warning(f"Error initializing MCP server {server.name}:\n{e}")
            finally:
                await server.disconnect()

            if server_tools:
                return (server.name, server_tools)
            return None

        async def get_all_server_tools():
            tasks = [get_server_tools(server) for server in self.mcp_servers]
            results = await asyncio.gather(*tasks)
            return [result for result in results if result is not None]

        if self.mcp_servers:
            tools = asyncio.run(get_all_server_tools())

        if len(tools) > 0:
            self.main_coder.io.tool_output("MCP servers configured for handler:")
            for server_name, server_tools in tools:
                self.main_coder.io.tool_output(f"  - {server_name}")

                if self.main_coder.verbose:
                    for tool in server_tools:
                        tool_name = tool.get("function", {}).get("name", "unknown")
                        tool_desc = tool.get("function", {}).get("description", "").split("\n")[0]
                        self.main_coder.io.tool_output(f"    - {tool_name}: {tool_desc}")
        self.mcp_tools = []
        for _, server_tools in tools:
            self.mcp_tools.extend(server_tools)

        self.mcp_tools_by_server = tools

    def _gather_server_tool_calls(self, tool_calls):
        if not self.mcp_tools_by_server:
            return None

        server_tool_calls = {}
        for tool_call in tool_calls:
            # Check if this tool_call matches any MCP tool
            for server_name, server_tools in self.mcp_tools_by_server:
                for tool in server_tools:
                    if tool.get("function", {}).get("name") == tool_call.function.name:
                        # Find the McpServer instance that will be used for communication
                        for server in self.mcp_servers:
                            if server.name == server_name:
                                if server not in server_tool_calls:
                                    server_tool_calls[server] = []
                                server_tool_calls[server].append(tool_call)
                                break
        return server_tool_calls

    def _execute_tool_calls(self, tool_calls):
        from litellm import experimental_mcp_client

        tool_responses = []

        async def _exec_server_tools(server, tool_calls_list):
            responses = []
            try:
                session = await server.connect()
                for tool_call in tool_calls_list:
                    try:
                        call_result = await experimental_mcp_client.call_openai_tool(
                            session=session,
                            openai_tool=tool_call,
                        )
                        result_text = str(call_result.content[0].text)
                        responses.append(
                            {"role": "tool", "tool_call_id": tool_call.id, "content": result_text}
                        )
                    except Exception as e:
                        tool_error = f"Error executing tool call {tool_call.function.name}: \n{e}"
                        self.main_coder.io.tool_warning(
                            f"Executing {tool_call.function.name} on {server.name} failed:"
                            f" \n  Error: {e}\n"
                        )
                        responses.append(
                            {"role": "tool", "tool_call_id": tool_call.id, "content": tool_error}
                        )
            except Exception as e:
                connection_error = f"Could not connect to server {server.name}\n{e}"
                self.main_coder.io.tool_warning(connection_error)
                for tool_call in tool_calls_list:
                    responses.append(
                        {"role": "tool", "tool_call_id": tool_call.id, "content": connection_error}
                    )
            finally:
                await server.disconnect()

            return responses

        async def _execute_all_tool_calls():
            tasks = []
            for server, tool_calls_list in tool_calls.items():
                tasks.append(_exec_server_tools(server, tool_calls_list))
            results = await asyncio.gather(*tasks)
            return results

        if tool_calls:
            all_results = asyncio.run(_execute_all_tool_calls())
            for server_results in all_results:
                tool_responses.extend(server_results)

        return tool_responses

    def _print_tool_call_info(self, server_tool_calls):
        self.main_coder.io.tool_output("Preparing to run MCP tools", bold=True)

        for server, tool_calls in server_tool_calls.items():
            for tool_call in tool_calls:
                self.main_coder.io.tool_output(f"Tool Call: {tool_call.function.name}")
                self.main_coder.io.tool_output(f"Arguments: {tool_call.function.arguments}")
                self.main_coder.io.tool_output(f"MCP Server: {server.name}")

                if self.main_coder.verbose:
                    self.main_coder.io.tool_output(f"Tool ID: {tool_call.id}")
                    self.main_coder.io.tool_output(f"Tool type: {tool_call.type}")

                self.main_coder.io.tool_output("\n")
