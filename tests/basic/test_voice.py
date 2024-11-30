import pytest
from unittest.mock import Mock, patch
import numpy as np
import queue
import tempfile
import os

from aider.voice import Voice, SoundDeviceError

@pytest.fixture
def mock_sounddevice():
    with patch('sounddevice.query_devices') as mock_query:
        mock_query.return_value = [
            {'name': 'test_device', 'max_input_channels': 2},
            {'name': 'another_device', 'max_input_channels': 1}
        ]
        yield mock_query

@pytest.fixture
def mock_soundfile():
    with patch('soundfile.SoundFile') as mock_sf:
        yield mock_sf

def test_voice_init_default_device(mock_sounddevice):
    voice = Voice()
    assert voice.device_id is None
    assert voice.audio_format == 'wav'

def test_voice_init_specific_device(mock_sounddevice):
    voice = Voice(device_name='test_device')
    assert voice.device_id == 0

def test_voice_init_invalid_device(mock_sounddevice):
    with pytest.raises(ValueError) as exc:
        Voice(device_name='nonexistent_device')
    assert 'Device' in str(exc.value)
    assert 'not found' in str(exc.value)

def test_voice_init_invalid_format():
    with pytest.raises(ValueError) as exc:
        Voice(audio_format='invalid')
    assert 'Unsupported audio format' in str(exc.value)

def test_callback_processing():
    voice = Voice()
    voice.q = queue.Queue()
    
    # Test with silence (low amplitude)
    test_data = np.zeros((1000, 1))
    voice.callback(test_data, None, None, None)
    assert voice.pct < 0.1
    
    # Test with loud signal (high amplitude)
    test_data = np.ones((1000, 1))
    voice.callback(test_data, None, None, None)
    assert voice.pct > 0.9
    
    # Verify data is queued
    assert not voice.q.empty()

@patch('aider.voice.litellm')
def test_record_and_transcribe(mock_litellm, mock_soundfile):
    voice = Voice()
    
    # Mock the recording process
    with patch('prompt_toolkit.shortcuts.prompt'):
        with patch('sounddevice.InputStream'):
            # Mock the transcription response
            mock_litellm.transcription.return_value = Mock(text="Hello, world!")
            
            result = voice.record_and_transcribe()
            
            assert result == "Hello, world!"
            mock_litellm.transcription.assert_called_once()

def test_get_prompt():
    voice = Voice()
    voice.start_time = voice.start_time = os.times().elapsed
    voice.pct = 0.5  # 50% volume level
    
    prompt = voice.get_prompt()
    assert "Recording" in prompt
    assert "sec" in prompt
    assert "█" in prompt  # Should contain some filled blocks
    assert "░" in prompt  # Should contain some empty blocks

@patch('sounddevice.InputStream')
def test_record_and_transcribe_keyboard_interrupt(mock_stream):
    voice = Voice()
    mock_stream.side_effect = KeyboardInterrupt()
    
    result = voice.record_and_transcribe()
    assert result is None

@patch('sounddevice.InputStream')
def test_record_and_transcribe_device_error(mock_stream):
    voice = Voice()
    mock_stream.side_effect = SoundDeviceError("Test error")
    
    result = voice.record_and_transcribe()
    assert result is None
