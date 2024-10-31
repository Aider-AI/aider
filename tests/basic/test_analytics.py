import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from aider.analytics import Analytics


@pytest.fixture
def temp_analytics_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_data_dir(monkeypatch):
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        monkeypatch.setattr(Path, "home", lambda: temp_dir)
        yield temp_dir


def test_analytics_initialization(temp_data_dir):
    analytics = Analytics(permanently_disable=True)
    assert analytics.mp is None
    assert analytics.ph is None
    assert analytics.permanently_disable is True
    assert analytics.user_id is not None


def test_analytics_enable_disable(temp_data_dir):
    analytics = Analytics()
    analytics.asked_opt_in = True

    analytics.enable()
    assert analytics.mp is not None
    assert analytics.ph is not None

    analytics.disable(permanently=False)
    assert analytics.mp is None
    assert analytics.ph is None
    assert analytics.permanently_disable is not True

    analytics.disable(permanently=True)
    assert analytics.permanently_disable is True


def test_analytics_data_persistence(temp_data_dir):
    analytics1 = Analytics()
    user_id = analytics1.user_id

    analytics2 = Analytics()
    assert analytics2.user_id == user_id


def test_analytics_event_logging(temp_analytics_file, temp_data_dir):
    analytics = Analytics(logfile=temp_analytics_file)
    analytics.asked_opt_in = True
    analytics.enable()

    test_event = "test_event"
    test_properties = {"test_key": "test_value"}

    with patch.object(analytics.mp, "track") as mock_mp_track:
        with patch.object(analytics.ph, "capture") as mock_ph_capture:
            analytics.event(test_event, **test_properties)

            mock_mp_track.assert_called_once()
            mock_ph_capture.assert_called_once()

            # Verify logfile
            with open(temp_analytics_file) as f:
                log_entry = json.loads(f.read().strip())
                assert log_entry["event"] == test_event
                assert "test_key" in log_entry["properties"]


def test_system_info(temp_data_dir):
    analytics = Analytics()
    sys_info = analytics.get_system_info()

    assert "python_version" in sys_info
    assert "os_platform" in sys_info
    assert "os_release" in sys_info
    assert "machine" in sys_info


def test_need_to_ask(temp_data_dir):
    analytics = Analytics()
    assert analytics.need_to_ask() is True

    analytics.asked_opt_in = True
    assert analytics.need_to_ask() is False

    analytics.permanently_disable = True
    assert analytics.need_to_ask() is False
