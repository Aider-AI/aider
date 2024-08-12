import uuid
from pathlib import Path
import json
from mixpanel import Mixpanel

class Analytics:
    def __init__(self, project_token="3f9ad6b9d7b7e8e5a1a5a9a7b0b0b0b0"):
        self.mp = Mixpanel(project_token) if project_token else None
        self.user_id = self.get_or_create_uuid()

    def get_or_create_uuid(self):
        uuid_file = Path.home() / ".aider" / "caches" / "mixpanel-uuid.json"
        uuid_file.parent.mkdir(parents=True, exist_ok=True)

        if uuid_file.exists():
            with open(uuid_file, 'r') as f:
                return json.load(f)['uuid']

        new_uuid = str(uuid.uuid4())
        with open(uuid_file, 'w') as f:
            json.dump({'uuid': new_uuid}, f)

        return new_uuid

    def track_event(self, event_name, properties=None):
        if self.mp:
            self.mp.track(self.user_id, event_name, properties)
