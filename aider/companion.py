import os
import requests

from aider.io import InputOutput


class Companion:
    base_dir = ""
    io: InputOutput = None
    base_url = "http://localhost:24337"
    enabled = False

    def __init__(
        self,
        base_dir,
        io=None,
        base_url="http://localhost:24337",
        enabled=False,
    ):
        self.base_dir = base_dir
        self.io = io
        self.base_url = base_url
        self.enabled = enabled

    def set_enabled(self, enabled):
        self.enabled = enabled

    def get_open_files(self, use_absolute_paths=True):
        if not self.enabled:
            return []

        try:
            url = f"{self.base_url}/open-files"
            response = requests.post(url, json={"projectBase": self.base_dir.replace("\\", "/")})

            if response.status_code == 200:
                files = response.json()
                if use_absolute_paths:
                    files = [os.path.abspath(os.path.join(self.base_dir, file)) for file in files]
                return files
            else:
                if self.io:
                    self.io.tool_error(f"Error: {response.status_code} - {response.text}")
                return []
        except requests.exceptions.RequestException as e:
            if self.io:
                self.io.tool_error(f"An error occurred while trying to connect to Aider Companion:\n{e}")
            return []
