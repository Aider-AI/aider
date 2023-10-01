from prompt_toolkit.completion import Completion

class CommandCompletions:
    def __init__(self, coder):
        self.coder = coder

    def completions_add(self, partial):
        files = set(self.coder.get_all_relative_files())
        files = files - set(self.coder.get_inchat_relative_files())
        partial_lower = partial.lower()
        print(f"Files: {files}")
        print(f"Partial: {partial_lower}")
        for fname in files:
            fname_lower = fname.lower()
            partial_index = 0
            for char in fname_lower:
                if char == partial_lower[partial_index]:
                    partial_index += 1
                if partial_index == len(partial_lower):
                    break
            if partial_index == len(partial_lower):
                yield Completion(fname, start_position=-len(partial))

    def completions_drop(self, partial):
        files = self.coder.get_inchat_relative_files()
        for fname in files:
            if partial.lower() in fname.lower():
                yield Completion(fname, start_position=-len(partial))
