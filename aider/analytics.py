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
from aider.models import model_info_manager

mixpanel_project_token = "6da9a43058a5d1b9f3353153921fb04d"
posthog_project_api_key = "phc_99T7muzafUMMZX15H8XePbMSreEUzahHbtWjy3l5Qbv"
posthog_host = "https://us.i.posthog.com"


class Analytics:
    # providers
    mp = None
    ph = None

    # saved
    user_id = None
    permanently_disable = None
    asked_opt_in = None

    # ephemeral
    logfile = None

    def __init__(self, logfile=None, permanently_disable=False):
        self.logfile = logfile
        self.get_or_create_uuid()

        if self.permanently_disable or permanently_disable or not self.asked_opt_in:
            self.disable(permanently_disable)

    def enable(self):
        if not self.user_id:
            self.disable(False)
            return

        if self.permanently_disable:
            self.disable(True)
            return

        if not self.asked_opt_in:
            self.disable(False)
            return

        self.mp = Mixpanel(mixpanel_project_token)
        self.ph = Posthog(project_api_key=posthog_project_api_key, host=posthog_host)

    def disable(self, permanently):
        self.mp = None
        self.ph = None

        if permanently:
            self.asked_opt_in = True
            self.permanently_disable = True
            self.save_data()

    def need_to_ask(self):
        return not self.asked_opt_in and not self.permanently_disable

    def get_data_file_path(self):
        data_file = Path.home() / ".aider" / "analytics.json"
        data_file.parent.mkdir(parents=True, exist_ok=True)
        return data_file

    def get_or_create_uuid(self):
        self.load_data()
        if self.user_id:
            return

        self.user_id = str(uuid.uuid4())
        self.save_data()

    def load_data(self):
        data_file = self.get_data_file_path()
        if data_file.exists():
            try:
                data = json.loads(data_file.read_text())
                self.permanently_disable = data.get("permanently_disable")
                self.user_id = data.get("uuid")
                self.asked_opt_in = data.get("asked_opt_in", False)
            except (json.decoder.JSONDecodeError, OSError):
                self.disable(permanently=False)

    def save_data(self):
        data_file = self.get_data_file_path()
        data = dict(
            uuid=self.user_id,
            permanently_disable=self.permanently_disable,
            asked_opt_in=self.asked_opt_in,
        )

        # Allow exceptions; crash if we can't record permanently_disabled=True, etc
        data_file.write_text(json.dumps(data, indent=4))

    def get_system_info(self):
        return {
            "python_version": sys.version.split()[0],
            "os_platform": platform.system(),
            "os_release": platform.release(),
            "machine": platform.machine(),
        }

    def _redact_model_name(self, model):
        if not model:
            return None

        info = model_info_manager.get_model_from_cached_json_db(model.name)
        if info:
            return model.name
        elif "/" in model.name:
            return model.name.split("/")[0] + "/REDACTED"
        return None

    def event(self, event_name, main_model=None, **kwargs):
        if not (self.mp or self.ph) and not self.logfile:
            return

        properties = {}

        if main_model:
            properties["main_model"] = self._redact_model_name(main_model)
            properties["weak_model"] = self._redact_model_name(main_model.weak_model)
            properties["editor_model"] = self._redact_model_name(main_model.editor_model)

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
            self.mp.track(self.user_id, event_name, dict(properties))

        if self.ph:
            self.ph.capture(self.user_id, event_name, dict(properties))

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
