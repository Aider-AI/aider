import yaml

class PromptManager:
    def __init__(self, file_path):
        self.file_path = file_path
        self.prompts = None
        self.load_prompts()

    def load_prompts(self):
        with open(self.file_path, 'r') as file:
            self.prompts = yaml.safe_load(file)

    def get_prompt_value(self, class_name, key_name):
        class_prompts = self.prompts.get(class_name, {})
        return class_prompts.get(key_name, "false")
