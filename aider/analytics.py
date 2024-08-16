import json
import platform
import sys
import time
import uuid
from pathlib import Path

from mixpanel import Mixpanel
from posthog import Posthog

from aider import __version__
from aider.dump import dump  # noqa: F401

mixpanel_project_token = "6da9a43058a5d1b9f3353153921fb04d"
posthog_project_api_key = "phc_99T7muzafUMMZX15H8XePbMSreEUzahHbtWjy3l5Qbv"
posthog_host = "https://us.i.posthog.com"


class Analytics:
    mp = None
    ph = None
    user_id = None
    permanently_disable = None
    logfile = None

    def __init__(self, enable=False, logfile=None, permanently_disable=False):
        self.logfile = logfile
        self.permanently_disable = permanently_disable
        if not enable or permanently_disable:
            self.mp = None
            self.ph = None
            if permanently_disable:
                self.mark_as_permanently_disabled()
            return

        self.user_id = self.get_or_create_uuid()

        if self.user_id and not self.permanently_disable:
            self.mp = Mixpanel(mixpanel_project_token)
            self.ph = Posthog(project_api_key=posthog_project_api_key, host=posthog_host)

    def get_data_file_path(self):
        data_file = Path.home() / ".aider" / "analytics.json"
        data_file.parent.mkdir(parents=True, exist_ok=True)
        return data_file

    def mark_as_permanently_disabled(self):
        data_file = self.get_data_file_path()
        if data_file.exists():
            with open(data_file, "r") as f:
                data = json.load(f)
        else:
            data = {"uuid": str(uuid.uuid4())}
        data["permanently_disabled"] = True
        with open(data_file, "w") as f:
            json.dump(data, f)

    def get_or_create_uuid(self):
        data_file = self.get_data_file_path()

        if data_file.exists():
            with open(data_file, "r") as f:
                data = json.load(f)
                if "permanently_disabled" in data and data["permanently_disabled"]:
                    self.permanently_disable = True
                    self.mp = None
                    self.ph = None
                    return
                return data["uuid"]

        new_uuid = str(uuid.uuid4())
        with open(data_file, "w") as f:
            json.dump({"uuid": new_uuid}, f)

        return new_uuid

    def get_system_info(self):
        return {
            "python_version": sys.version.split()[0],
            "os_platform": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
        }

    def event(self, event_name, main_model=None, **kwargs):
        if not (self.mp or self.ph) and not self.logfile:
            return

        properties = {}

        if main_model:
            if main_model.info:
                properties["main_model"] = main_model.name
            elif "/" in main_model.name:
                properties["main_model"] = main_model.name.split("/")[0] + "/REDACTED"

        properties.update(kwargs)
        properties.update(self.get_system_info())  # Add system info to all events

        # Handle numeric values
        for key, value in properties.items():
            if isinstance(value, (int, float)):
                properties[key] = value
            else:
                properties[key] = str(value)

        properties["aider_version"] = __version__

        if self.mp:
            self.mp.track(self.user_id, event_name, properties)

        if self.ph:
            self.ph.capture(self.user_id, event_name, properties)

        if self.logfile:
            log_entry = {
                "event": event_name,
                "properties": properties,
                "user_id": self.user_id,
                "time": int(time.time()),
            }
            with open(self.logfile, "a") as f:
                json.dump(log_entry, f)
                f.write("\n")

    def __del__(self):
        if self.ph:
            self.ph.shutdown()
