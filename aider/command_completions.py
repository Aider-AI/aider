from prompt_toolkit.completion import Completion

class CommandCompletions:
    def __init__(self, coder):
        self.coder = coder

    def completions_add(self, partial):
        files = set(self.coder.get_all_relative_files())
        files = files - set(self.coder.get_inchat_relative_files())
        partial_lower = partial.lower()
        for fname in files:
            fname_lower = fname.lower()
            if all(c in fname_lower for c in partial_lower) and \
               ''.join(c for c in fname_lower if c in partial_lower) == partial_lower:
                yield Completion(fname, start_position=-len(partial))

    def completions_drop(self, partial):
        files = self.coder.get_inchat_relative_files()
        for fname in files:
            if partial.lower() in fname.lower():
                yield Completion(fname, start_position=-len(partial))
