import os
import queue
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aider.voice import SoundDeviceError, Voice


# Mock the entire sounddevice module
@pytest.fixture
def mock_sounddevice():
    mock_sd = MagicMock()
    mock_sd.query_devices.return_value = [
        {"name": "test_device", "max_input_channels": 2, "default_samplerate": 44100},
        {"name": "another_device", "max_input_channels": 1, "default_samplerate": 16000},
    ]

    class MockInputStream:
        def __init__(self, samplerate, channels, callback, device):
            self.samplerate = samplerate
            self.channels = channels
            self.callback = callback
            self.device = device
            self.is_active = True

        def __enter__(self):
            # Simulate some audio input by calling the callback
            # Use fixed dummy data to control file size in tests
            # Roughly 16kHz, 1-channel, 16-bit WAV is ~1MB per minute.
            # 1 MB data ~ 60 seconds * 16000 samples/sec = 960,000 samples.
            # 24.9 MB threshold / ~1MB/min = ~24.9 minutes of audio
            # Let's use 1 second of data for small files, 30 seconds for large files.
            # The dummy_data_size_samples attribute will be set by the test
            if not hasattr(self, "dummy_data_size_samples"):
                self.dummy_data_size_samples = self.samplerate * 1  # Default 1 sec

            # Divide into chunks for callback
            num_chunks = 5
            samples_per_chunk = self.dummy_data_size_samples // num_chunks
            for _ in range(num_chunks):
                # Using 0.5 amplitude to get a good RMS for pct calculation
                dummy_data = np.full((samples_per_chunk, self.channels), 0.5, dtype=np.float32)
                self.callback(dummy_data, None, None, None)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            self.is_active = False
            pass

    mock_sd.InputStream = MockInputStream
    with patch.dict("sys.modules", {"sounddevice": mock_sd}):
        yield mock_sd


@pytest.fixture
def mock_prompt_toolkit():
    with patch("aider.voice.prompt") as mock_prompt:
        yield mock_prompt


@pytest.fixture
def mock_litellm_transcription():
    mock_transcript = MagicMock()
    mock_transcript.text = "This is a test transcription."
    with patch(
        "aider.llm.litellm.transcription", return_value=mock_transcript
    ) as mock_transcribe_func:
        yield mock_transcribe_func


def test_voice_init_default_device(mock_sounddevice):
    # Need to mock sf here as Voice() init checks for it, but not in all other tests
    # where it's not relevant.
    with patch("aider.voice.sf", MagicMock()):
        voice = Voice()
        assert voice.device_id is None
        assert voice.audio_format == "wav"
        assert voice.sd == mock_sounddevice


def test_voice_init_specific_device(mock_sounddevice):
    voice = Voice(device_name="test_device")
    assert voice.device_id == 0
    assert voice.sd == mock_sounddevice


def test_voice_init_invalid_device(mock_sounddevice):
    with pytest.raises(ValueError) as exc:
        Voice(device_name="nonexistent_device")
    assert "Device" in str(exc.value)
    assert "not found" in str(exc.value)


def test_voice_init_invalid_format():
    with patch("aider.voice.sf", MagicMock()):  # Need to mock sf to avoid SoundDeviceError
        with pytest.raises(ValueError) as exc:
            Voice(audio_format="invalid")
        assert "Unsupported audio format" in str(exc.value)


def test_callback_processing():
    # Soundfile not needed for callback, but Voice init requires it
    with patch("aider.voice.sf", MagicMock()):
        voice = Voice()
        voice.q = queue.Queue()

        # Test with silence (low amplitude)
        test_data = np.zeros((1000, 1))
        voice.callback(test_data, None, None, None)
        assert voice.pct == 0.5  # When range is too small (<=0.001), pct is set to 0.5

        # Test with loud signal (high amplitude)
        test_data = np.ones((1000, 1))
        voice.callback(test_data, None, None, None)
        assert voice.pct > 0.9

        # Verify data is queued
        assert not voice.q.empty()


def test_get_prompt():
    # Soundfile not needed for get_prompt, but Voice init requires it
    with patch("aider.voice.sf", MagicMock()):
        voice = Voice()
        voice.start_time = os.times().elapsed
        voice.pct = 0.5  # 50% volume level

        prompt = voice.get_prompt()
        assert "Recording" in prompt
        assert "sec" in prompt
        assert "█" in prompt  # Should contain some filled blocks
        assert "░" in prompt  # Should contain some empty blocks


def test_record_and_transcribe_keyboard_interrupt():
    # Soundfile not needed for this test, but Voice init requires it
    with patch("aider.voice.sf", MagicMock()):
        voice = Voice()
        with patch.object(voice, "raw_record_and_transcribe", side_effect=KeyboardInterrupt()):
            result = voice.record_and_transcribe()
            assert result is None


def test_raw_record_and_transcribe_success_no_conversion(
    mock_sounddevice, mock_prompt_toolkit, mock_litellm_transcription, tmp_path
):
    # Simulate small audio file, should not trigger conversion
    mock_sounddevice.InputStream.dummy_data_size_samples = 16000 * 5  # 5 seconds of 16kHz audio

    with patch("os.remove") as mock_remove:
        voice = Voice(audio_format="wav", device_name="another_device")
        voice.tempfile_mktemp = MagicMock(side_effect=[str(tmp_path / "temp.wav")])
        with patch("tempfile.mktemp", new=voice.tempfile_mktemp):
            result = voice.raw_record_and_transcribe(None, None)

            assert result == "This is a test transcription."
            mock_prompt_toolkit.assert_called_once()
            mock_litellm_transcription.assert_called_once()

            # Check transcription was called with the wav file
            assert "temp.wav" in mock_litellm_transcription.call_args.kwargs["file"].name

            # Check cleanup
            mock_remove.assert_called_once_with(str(tmp_path / "temp.wav"))


def test_raw_record_and_transcribe_success_with_conversion_to_mp3(
    mock_sounddevice, mock_prompt_toolkit, mock_litellm_transcription, tmp_path
):
    # Simulate large audio file (over 24.9MB for 16kHz, 1-channel, 16-bit WAV), should
    # trigger MP3 conversion
    # Approx 1MB/min for 16kHz, 16-bit mono WAV. So ~25 mins = 25MB
    # 25 mins * 60 sec/min * 16000 samples/sec = 24,000,000 samples
    mock_sounddevice.InputStream.dummy_data_size_samples = 16000 * 60 * 26  # 26 minutes of audio

    with patch("os.remove") as mock_remove:
        voice = Voice(audio_format="wav", device_name="another_device")
        voice.tempfile_mktemp = MagicMock(
            side_effect=[str(tmp_path / "temp.wav"), str(tmp_path / "output.mp3")]
        )
        with patch("tempfile.mktemp", new=voice.tempfile_mktemp):
            result = voice.raw_record_and_transcribe(None, None)

            assert result == "This is a test transcription."
            mock_prompt_toolkit.assert_called_once()
            mock_litellm_transcription.assert_called_once()

            # Check transcription was called with the mp3 file
            assert "output.mp3" in mock_litellm_transcription.call_args.kwargs["file"].name

            # Check cleanup: original wav and converted mp3 should be removed
            mock_remove.assert_any_call(str(tmp_path / "temp.wav"))
            mock_remove.assert_any_call(str(tmp_path / "output.mp3"))
            assert mock_remove.call_count == 3


def test_raw_record_and_transcribe_success_direct_mp3_format(
    mock_sounddevice, mock_prompt_toolkit, mock_litellm_transcription, tmp_path
):
    # Specify mp3 format directly, should convert regardless of size
    mock_sounddevice.InputStream.dummy_data_size_samples = 16000 * 10  # 10 seconds of 16kHz audio

    with patch("os.remove") as mock_remove:
        voice = Voice(audio_format="mp3", device_name="another_device")
        voice.tempfile_mktemp = MagicMock(
            side_effect=[str(tmp_path / "temp.wav"), str(tmp_path / "output.mp3")]
        )
        with patch("tempfile.mktemp", new=voice.tempfile_mktemp):
            result = voice.raw_record_and_transcribe(None, None)

            assert result == "This is a test transcription."
            mock_prompt_toolkit.assert_called_once()
            mock_litellm_transcription.assert_called_once()

            # Check transcription was called with the mp3 file
            assert "output.mp3" in mock_litellm_transcription.call_args.kwargs["file"].name

            # Check cleanup: original wav and converted mp3 should be removed
            mock_remove.assert_any_call(str(tmp_path / "temp.wav"))
            mock_remove.assert_any_call(str(tmp_path / "output.mp3"))
            assert mock_remove.call_count == 3


def test_raw_record_and_transcribe_transcription_failure_cleanup(
    mock_sounddevice, mock_prompt_toolkit, mock_litellm_transcription, tmp_path
):
    # Simulate transcription failure, ensure temporary files are cleaned up
    mock_litellm_transcription.side_effect = Exception("Transcription failed!")
    mock_sounddevice.InputStream.dummy_data_size_samples = 16000 * 5  # 5 seconds of audio

    with patch("os.path.exists", side_effect=lambda x: True):
        with patch("os.remove") as mock_remove:
            voice = Voice(audio_format="wav", device_name="another_device")
            voice.tempfile_mktemp = MagicMock(side_effect=[str(tmp_path / "temp.wav")])
            with patch("tempfile.mktemp", new=voice.tempfile_mktemp):
                result = voice.raw_record_and_transcribe(None, None)

                assert result is None  # Should return None on transcription failure
                mock_prompt_toolkit.assert_called_once()
                mock_litellm_transcription.assert_called_once()

                # Ensure temp wav file was removed even after transcription failure
                mock_remove.assert_called_once_with(str(tmp_path / "temp.wav"))


def test_record_and_transcribe_device_error():
    # Soundfile not needed for this test, but Voice init requires it
    with patch("aider.voice.sf", MagicMock()):
        voice = Voice()
        with patch.object(
            voice, "raw_record_and_transcribe", side_effect=SoundDeviceError("Test error")
        ):
            result = voice.record_and_transcribe()
            assert result is None
