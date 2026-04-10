import math

import litellm

from aider.utils import format_tokens


class UsageTracker:
    """Tracks token usage and costs for LLM interactions."""

    def __init__(self, main_model, io):
        self.main_model = main_model
        self.io = io
        self.message_tokens_sent = 0
        self.message_tokens_received = 0
        self.message_cost = 0.0
        self.total_cost = 0.0
        self.total_tokens_sent = 0
        self.total_tokens_received = 0
        self.usage_report = None

    def calculate_and_show_tokens_and_cost(self, messages, completion=None):
        prompt_tokens = 0
        completion_tokens = 0
        cache_hit_tokens = 0
        cache_write_tokens = 0

        if completion and hasattr(completion, "usage") and completion.usage is not None:
            prompt_tokens = completion.usage.prompt_tokens
            completion_tokens = completion.usage.completion_tokens
            cache_hit_tokens = getattr(completion.usage, "prompt_cache_hit_tokens", 0) or getattr(
                completion.usage, "cache_read_input_tokens", 0
            )
            cache_write_tokens = getattr(completion.usage, "cache_creation_input_tokens", 0)

            if hasattr(completion.usage, "cache_read_input_tokens") or hasattr(
                completion.usage, "cache_creation_input_tokens"
            ):
                self.message_tokens_sent += prompt_tokens
                self.message_tokens_sent += cache_write_tokens
            else:
                self.message_tokens_sent += prompt_tokens

        else:
            prompt_tokens = self.main_model.token_count(messages)
            completion_tokens = self.main_model.token_count_for_text(completion)
            self.message_tokens_sent += prompt_tokens

        self.message_tokens_received += completion_tokens

        tokens_report = f"Tokens: {format_tokens(self.message_tokens_sent)} sent"

        if cache_write_tokens:
            tokens_report += f", {format_tokens(cache_write_tokens)} cache write"
        if cache_hit_tokens:
            tokens_report += f", {format_tokens(cache_hit_tokens)} cache hit"
        tokens_report += f", {format_tokens(self.message_tokens_received)} received."

        if not self.main_model.info.get("input_cost_per_token"):
            self.usage_report = tokens_report
            return

        try:
            cost = litellm.completion_cost(completion_response=completion)
        except Exception:
            cost = 0

        if not cost:
            cost = self.compute_costs_from_tokens(
                prompt_tokens, completion_tokens, cache_write_tokens, cache_hit_tokens
            )

        self.total_cost += cost
        self.message_cost += cost

        def format_cost(value):
            if value == 0:
                return "0.00"
            magnitude = abs(value)
            if magnitude >= 0.01:
                return f"{value:.2f}"
            else:
                return f"{value:.{max(2, 2 - int(math.log10(magnitude)))}f}"

        cost_report = (
            f"Cost: ${format_cost(self.message_cost)} message,"
            f" ${format_cost(self.total_cost)} session."
        )

        if cache_hit_tokens and cache_write_tokens:
            sep = "\n"
        else:
            sep = " "

        self.usage_report = tokens_report + sep + cost_report

    def compute_costs_from_tokens(
        self, prompt_tokens, completion_tokens, cache_write_tokens, cache_hit_tokens
    ):
        cost = 0

        input_cost_per_token = self.main_model.info.get("input_cost_per_token") or 0
        output_cost_per_token = self.main_model.info.get("output_cost_per_token") or 0
        input_cost_per_token_cache_hit = (
            self.main_model.info.get("input_cost_per_token_cache_hit") or 0
        )

        if input_cost_per_token_cache_hit:
            cost += input_cost_per_token_cache_hit * cache_hit_tokens
            cost += (prompt_tokens - input_cost_per_token_cache_hit) * input_cost_per_token
        else:
            cost += cache_write_tokens * input_cost_per_token * 1.25
            cost += cache_hit_tokens * input_cost_per_token * 0.10
            cost += prompt_tokens * input_cost_per_token

        cost += completion_tokens * output_cost_per_token
        return cost

    def show_usage_report(self, event_callback=None, main_model=None, edit_format=None):
        if not self.usage_report:
            return

        self.total_tokens_sent += self.message_tokens_sent
        self.total_tokens_received += self.message_tokens_received

        self.io.tool_output(self.usage_report)

        if event_callback:
            event_callback(
                "message_send",
                main_model=main_model,
                edit_format=edit_format,
                prompt_tokens=self.message_tokens_sent,
                completion_tokens=self.message_tokens_received,
                total_tokens=self.message_tokens_sent + self.message_tokens_received,
                cost=self.message_cost,
                total_cost=self.total_cost,
            )

        self.message_cost = 0.0
        self.message_tokens_sent = 0
        self.message_tokens_received = 0