class CustomTool:
    def __init__(self, name, config):
        self.name = name
        self.config = config

    def initialize(self, coder):
        """
        Initialize the custom tool with the given coder instance.
        """
        self.coder = coder

    def execute(self, *args, **kwargs):
        """
        Execute the custom tool with the provided arguments.
        """
        raise NotImplementedError("Custom tools must implement the execute method.")
