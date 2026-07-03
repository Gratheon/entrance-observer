import json
import os
import requests
import threading
import time
from datetime import datetime
from typing import Callable, Optional

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False

import app_settings
import storage_manager

# Load environment variables from .env file
load_dotenv()


DEVICE_POLL_INTERVAL_SECONDS = 5
LIVE_FRAME_PUBLISH_INTERVAL_SECONDS = 0.25


def _poll_interval_seconds():
    settings = app_settings.get_telemetry_settings()
    try:
        return max(1, int(settings.get("live_control_poll_interval_sec", DEVICE_POLL_INTERVAL_SECONDS)))
    except (TypeError, ValueError):
        return DEVICE_POLL_INTERVAL_SECONDS


def _video_service_base_url(upload_url: str) -> str:
    if not upload_url:
        return "https://video.gratheon.com"

    if upload_url.endswith('/graphql'):
        return upload_url[:-8]

    return upload_url.rstrip('/')


def _post_video_service_json(path: str, payload: dict, timeout: int = 30):
    settings = app_settings.get_telemetry_settings()
    bearer_token = settings.get("api_token")
    upload_url = settings.get("video_upload_url") or "https://video.gratheon.com/graphql"
    base_url = _video_service_base_url(upload_url)

    if not bearer_token:
        raise ValueError("API token is required to contact gate-video-stream")

    return requests.post(
        f"{base_url}{path}",
        headers={
            'Authorization': f'Bearer {bearer_token}',
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=timeout,
        allow_redirects=True,
    )


def build_live_device_status(status_override=None):
    telemetry_settings = app_settings.get_telemetry_settings()
    box_id = telemetry_settings.get("section_id")
    if not box_id:
        return None

    status_override = status_override or {}
    return {
        "boxId": box_id,
        "deviceId": os.getenv("HOSTNAME") or os.getenv("DEVICE_ID") or "entrance-observer",
        "appVersion": os.getenv("APP_VERSION") or os.getenv("GIT_SHA") or "dev",
        "cameraStatus": status_override.get("cameraStatus", "ok"),
        "publisherState": status_override.get("publisherState", "idle"),
        "lastErrorCode": status_override.get("lastErrorCode"),
        "lastErrorMessage": status_override.get("lastErrorMessage"),
        "status": status_override.get("status", {}),
    }


def report_live_device_status(status_override=None):
    payload = build_live_device_status(status_override)
    if not payload:
        return None

    return _post_video_service_json('/api/entrance-live/device/status', payload)


def poll_live_commands(status_override=None, limit=10):
    payload = build_live_device_status(status_override)
    if not payload:
        return []

    payload["limit"] = limit
    response = _post_video_service_json('/api/entrance-live/device/poll', payload)
    response.raise_for_status()
    body = response.json() or {}
    return body.get("commands") or []


def acknowledge_live_command(box_id, command_id, status, payload=None):
    response = _post_video_service_json('/api/entrance-live/device/command-ack', {
        "boxId": box_id,
        "commandId": command_id,
        "status": status,
        "payload": payload or {},
    })
    response.raise_for_status()
    return response


def report_live_event(box_id, event_type, session_id=None, payload=None):
    response = _post_video_service_json('/api/entrance-live/device/event', {
        "boxId": box_id,
        "sessionId": session_id,
        "eventType": event_type,
        "payload": payload or {},
    })
    response.raise_for_status()
    return response


def publish_live_frame(session_id, publisher_url, publish_token, frame_bytes, timeout=10):
    settings = app_settings.get_telemetry_settings()
    bearer_token = settings.get("api_token")
    if not bearer_token:
        raise ValueError("API token is required to publish live frames")

    response = requests.post(
        publisher_url,
        headers={
            'Authorization': f'Bearer {bearer_token}',
            'X-Publish-Token': publish_token,
            'Content-Type': 'image/jpeg',
        },
        data=frame_bytes,
        timeout=timeout,
        allow_redirects=True,
    )
    response.raise_for_status()
    return response


def run_live_frame_publisher(
    stop_event,
    session_id: str,
    publisher_url: str,
    publish_token: str,
    frame_supplier: Callable[[], Optional[bytes]],
    status_supplier=None,
):
    last_error_message = None
    box_id = app_settings.get_telemetry_settings().get("section_id")

    while not stop_event.is_set():
        frame_bytes = frame_supplier() if callable(frame_supplier) else None
        if not frame_bytes:
            stop_event.wait(LIVE_FRAME_PUBLISH_INTERVAL_SECONDS)
            continue

        try:
            publish_live_frame(session_id, publisher_url, publish_token, frame_bytes)
            last_error_message = None
        except Exception as error:
            current_error = str(error)
            if current_error != last_error_message and box_id:
                last_error_message = current_error
                try:
                    status_override = status_supplier() if callable(status_supplier) else {}
                    status_override = status_override or {}
                    report_live_device_status({
                        'cameraStatus': status_override.get('cameraStatus', 'error'),
                        'publisherState': 'error',
                        'lastErrorCode': 'LIVE_FRAME_PUBLISH_ERROR',
                        'lastErrorMessage': current_error,
                        'status': {
                            **(status_override.get('status') or {}),
                            'publisherSessionId': session_id,
                            'publisherUrl': publisher_url,
                        },
                    })
                except Exception as nested_error:
                    print(f"⚠️ Could not report live frame publish error: {nested_error}")
            print(f"⚠️ Live frame publish failed: {error}")

        stop_event.wait(LIVE_FRAME_PUBLISH_INTERVAL_SECONDS)


def upload_file_async(file_path, detections_file_path, start_time_utc):
    upload_thread = threading.Thread(target=uploadAndRemove, args=(file_path, detections_file_path, start_time_utc))
    upload_thread.start()


def uploadAndRemove(output_file: str, detections_file: str, start_time_utc: datetime):
    video_settings = app_settings.get_video_settings()
    if not video_settings.get("upload_videos_enabled", True):
        print("☁️ Video upload disabled in app settings.")
        storage_manager.cleanup_storage()
        return

    settings = app_settings.get_telemetry_settings()
    bearer_token = settings.get("api_token")
    box_id = settings.get("section_id")
    upload_url = settings.get("video_upload_url") or "https://video.gratheon.com/graphql"

    if not bearer_token or not box_id:
        print("Error: Please set API token and section ID in app settings.")
        print("Skipping video upload for testing purposes.")
        storage_manager.cleanup_storage()
        return

    uploaded_successfully = False
def start_live_command_loop(stop_event, status_supplier=None, frame_supplier=None):
    telemetry_settings = app_settings.get_telemetry_settings()
    box_id = telemetry_settings.get("section_id")
    if not telemetry_settings.get("api_token") or not box_id:
        print("ℹ️ Skipping live command loop because API token or section ID is missing.")
        return

    active_publishers = {}

    try:
        report_live_event(box_id, 'DEVICE_ONLINE', payload={
            'cameraStatus': 'ok',
            'publisherState': 'idle',
        })
    except Exception as error:
        print(f"⚠️ Could not report live device online event: {error}")

    while not stop_event.is_set():
        try:
            status_override = status_supplier() if callable(status_supplier) else None
            commands = poll_live_commands(status_override=status_override)
            for command in commands:
                command_type = command.get('commandType')
                session_id = command.get('sessionId')
                payload = command.get('payload') or {}
                command_id = command.get('id')

                if command_type == 'START_STREAM':
                    acknowledge_live_command(box_id, command_id, 'accepted', {
                        'sessionId': session_id,
                        'relayProtocol': payload.get('relayProtocol'),
                    })

                    publisher_url = payload.get('publisherUrl')
                    publish_token = payload.get('publishToken')
                    relay_protocol = payload.get('relayProtocol')
                    if relay_protocol != 'http-jpeg-push' or not publisher_url or not publish_token:
                        report_live_event(box_id, 'STREAM_FAILED', session_id=session_id, payload={
                            'cameraStatus': 'error',
                            'publisherState': 'error',
                            'relayProtocol': relay_protocol,
                            'errorCode': 'UNSUPPORTED_RELAY_PROTOCOL',
                            'message': f'Unsupported or incomplete relay config: {relay_protocol}',
                        })
                        continue

                    existing_publisher = active_publishers.pop(session_id, None)
                    if existing_publisher:
                        existing_publisher['stop_event'].set()
                        existing_publisher['thread'].join(timeout=5)

                    publisher_stop_event = threading.Event()
                    publisher_thread = threading.Thread(
                        target=run_live_frame_publisher,
                        args=(publisher_stop_event, session_id, publisher_url, publish_token, frame_supplier, status_supplier),
                    )
                    publisher_thread.daemon = True
                    publisher_thread.start()
                    active_publishers[session_id] = {
                        'stop_event': publisher_stop_event,
                        'thread': publisher_thread,
                    }

                    report_live_event(box_id, 'STREAM_STARTING', session_id=session_id, payload={
                        'cameraStatus': 'ok',
                        'publisherState': 'starting',
                        'qualityProfile': payload.get('qualityProfile'),
                        'recordingMode': payload.get('recordingMode'),
                        'relayProtocol': relay_protocol,
                        'publisherUrl': publisher_url,
                    })
                    report_live_event(box_id, 'STREAM_ACTIVE', session_id=session_id, payload={
                        'cameraStatus': 'ok',
                        'publisherState': 'active',
                        'qualityProfile': payload.get('qualityProfile'),
                        'recordingMode': payload.get('recordingMode'),
                        'relayProtocol': relay_protocol,
                        'publisherUrl': publisher_url,
                        'clipHandoffEnabled': bool(payload.get('clipHandoffEnabled')),
                    })
                elif command_type == 'STOP_STREAM':
                    existing_publisher = active_publishers.pop(session_id, None)
                    if existing_publisher:
                        existing_publisher['stop_event'].set()
                        existing_publisher['thread'].join(timeout=5)

                    acknowledge_live_command(box_id, command_id, 'accepted', {
                        'sessionId': session_id,
                    })
                    report_live_event(box_id, 'STREAM_STOPPED', session_id=session_id, payload={
                        'cameraStatus': 'ok',
                        'publisherState': 'idle',
                        'reason': 'commanded-stop',
                    })
                else:
                    acknowledge_live_command(box_id, command_id, 'ignored', {
                        'sessionId': session_id,
                        'reason': f'Unsupported command type {command_type}',
                    })
        except Exception as error:
            print(f"⚠️ Live command loop error: {error}")
            try:
                report_live_device_status({
                    'cameraStatus': 'error',
                    'publisherState': 'idle',
                    'lastErrorCode': 'LIVE_COMMAND_LOOP_ERROR',
                    'lastErrorMessage': str(error),
                    'status': {
                        'loopError': str(error),
                    },
                })
            except Exception as nested_error:
                print(f"⚠️ Could not report live command loop error: {nested_error}")

        stop_event.wait(_poll_interval_seconds())

    for active_publisher in active_publishers.values():
        active_publisher['stop_event'].set()
        active_publisher['thread'].join(timeout=5)


def delete_old_mp4_files():
    storage_manager.cleanup_storage()
