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
        status = "enabled" if enabled else "disabled"
        if self.io:
            self.io.tool_output(f"Companion functionality is now {status}.")

    def get_open_files(self):
        if not self.enabled:
            return []

        try:
            url = f"{self.base_url}/open-files"
            response = requests.post(url, json={"projectBase": self.base_dir.replace("\\", "/")})

            if response.status_code == 200:
                return response.json()
            else:
                if self.io:
                    self.io.tool_error(f"Error: {response.status_code} - {response.text}")
                return []
        except requests.exceptions.RequestException as e:
            if self.io:
                self.io.tool_error(f"An error occurred while trying to connect to Aider Companion:\n{e}")
            return []
