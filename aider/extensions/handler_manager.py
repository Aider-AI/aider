#!/usr/bin/env python

import importlib
import inspect
import ast

from .handler import (
    Handler,
    ImmutableContextHandler,
    MutableContextHandler,
)


class HandlerManager:
    """
    The HandlerManager is responsible for loading and running handlers.
    """

    def __init__(self, main_coder, handlers=None):
        """
        Initialize the HandlerManager.

        :param main_coder: The main coder instance.
        :param handlers: An optional list of handlers to use, from user config.
                         If None, no handlers will be used.
        """
        self.main_coder = main_coder
        self.handlers = []

        if handlers:
            self._load_handlers(handlers)

    def _load_handlers(self, handlers_config):
        """
        Load handlers based on the provided configuration.
        """
        for handler_config in handlers_config:
            if isinstance(handler_config, str):
                try:
                    handler_config = ast.literal_eval(handler_config)
                except (ValueError, SyntaxError):
                    pass  # Keep it as a string, will be turned into a dict below

            if isinstance(handler_config, str):
                handler_config = dict(name=handler_config)

            if not isinstance(handler_config, dict):
                self.main_coder.io.tool_warning(
                    f"Invalid handler configuration: {handler_config}"
                )
                continue

            handler_name = handler_config.get("name")
            config = handler_config.get("config", {})

            if not handler_name:
                self.main_coder.io.tool_warning(
                    f"Handler configuration missing name: {handler_config}"
                )
                continue

            self._load_handler(handler_name, config)

    def _load_handler(self, handler_name, config):
        """
        Dynamically load a single handler.
        """
        try:
            # Construct module name from handler name, e.g., 'file-adder' -> 'file_adder_handler'
            module_name = handler_name.replace("-", "_") + "_handler"
            module_path = f"aider.extensions.handlers.{module_name}"
            module = importlib.import_module(module_path)

            handler_class = None
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(obj, Handler)
                    and obj is not Handler
                    and obj is not MutableContextHandler
                    and obj is not ImmutableContextHandler
                ):
                    handler_class = obj
                    break

            if handler_class:
                handler_instance = handler_class(self.main_coder, **config)
                handler_instance.name = handler_name
                self.handlers.append(handler_instance)
            else:
                self.main_coder.io.tool_warning(
                    f"No handler class found in module for: {handler_name}"
                )
        except ImportError as e:
            self.main_coder.io.tool_warning(f"Could not import handler: {handler_name}\n{e}")
        except Exception as e:
            self.main_coder.io.tool_warning(f"Failed to instantiate handler {handler_name}: {e}")

    def run(self, messages, entrypoint):
        """
        Execute the handler logic by running handlers for a specific entrypoint.

        This method iterates through its handlers, allowing each to process and
        potentially modify the chat context. If a handler modifies the
        context, the message history is updated for subsequent handlers.

        :param messages: The current list of messages in the chat.
        :param entrypoint: The entrypoint to run handlers for (e.g., "pre").
        """
        current_messages = messages
        for handler in self.handlers:
            if entrypoint in handler.entrypoints:
                modified = handler.handle(current_messages)
                if modified:
                    chunks = self.main_coder.format_messages()
                    current_messages = chunks.all_messages()
