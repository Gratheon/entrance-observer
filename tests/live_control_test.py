import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

import uploader


@patch('uploader.requests.post')
def test_poll_live_commands_uses_gate_video_stream_rest_api(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        'commands': [
            {
                'id': 11,
                'sessionId': 'session-1',
                'commandType': 'START_STREAM',
                'payload': {
                    'relayProtocol': 'stored-clip-handoff',
                    'qualityProfile': 'inspect',
                },
            }
        ]
    }
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch('uploader.app_settings.get_telemetry_settings', return_value={
        'api_token': 'secret',
        'section_id': '42',
        'video_upload_url': 'https://video.gratheon.com/graphql',
    }):
        commands = uploader.poll_live_commands(status_override={
            'cameraStatus': 'ok',
            'publisherState': 'idle',
        })

    assert commands[0]['commandType'] == 'START_STREAM'
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'https://video.gratheon.com/api/entrance-live/device/poll'
    assert kwargs['headers']['Authorization'] == 'Bearer secret'
    assert kwargs['json']['boxId'] == '42'
    assert kwargs['json']['cameraStatus'] == 'ok'


@patch('uploader.requests.post')
def test_poll_live_commands_passes_limit_to_rest_api(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {'commands': []}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch('uploader.app_settings.get_telemetry_settings', return_value={
        'api_token': 'secret',
        'section_id': '42',
        'video_upload_url': 'https://video.gratheon.com/graphql',
    }):
        uploader.poll_live_commands(limit=3)

    args, kwargs = mock_post.call_args
    assert args[0] == 'https://video.gratheon.com/api/entrance-live/device/poll'
    assert kwargs['json']['limit'] == 3


@patch('uploader.requests.post')
def test_acknowledge_live_command_uses_gate_video_stream_rest_api(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch('uploader.app_settings.get_telemetry_settings', return_value={
        'api_token': 'secret',
        'section_id': '42',
        'video_upload_url': 'https://video.gratheon.com/graphql',
    }):
        uploader.acknowledge_live_command('42', 11, 'accepted', payload={'publisherState': 'starting'})

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'https://video.gratheon.com/api/entrance-live/device/command-ack'
    assert kwargs['json']['boxId'] == '42'
    assert kwargs['json']['commandId'] == 11
    assert kwargs['json']['status'] == 'accepted'
    assert kwargs['json']['payload']['publisherState'] == 'starting'


@patch('uploader.requests.post')
def test_report_live_event_uses_gate_video_stream_rest_api(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch('uploader.app_settings.get_telemetry_settings', return_value={
        'api_token': 'secret',
        'section_id': '42',
        'video_upload_url': 'https://video.gratheon.com/graphql',
    }):
        uploader.report_live_event('42', 'STREAM_ACTIVE', session_id='session-1', payload={'fps': 15})

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'https://video.gratheon.com/api/entrance-live/device/event'
    assert kwargs['json']['eventType'] == 'STREAM_ACTIVE'
    assert kwargs['json']['payload']['fps'] == 15


@patch('uploader.requests.post')
def test_report_live_device_status_uses_gate_video_stream_rest_api(mock_post):
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    with patch('uploader.app_settings.get_telemetry_settings', return_value={
        'api_token': 'secret',
        'section_id': '42',
        'video_upload_url': 'https://video.gratheon.com/graphql',
    }):
        uploader.report_live_device_status(status_override={
            'cameraStatus': 'ok',
            'publisherState': 'idle',
            'status': {'fps': 0},
        })

    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == 'https://video.gratheon.com/api/entrance-live/device/status'
    assert kwargs['json']['boxId'] == '42'
    assert kwargs['json']['cameraStatus'] == 'ok'
    assert kwargs['json']['publisherState'] == 'idle'
    assert kwargs['json']['status']['fps'] == 0
