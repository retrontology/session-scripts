# Session Replay Hotkeys

A small Windows Python app for sorting Session: Skate Sim replay files and matching them with captured videos.

## What It Does

- `keep_hotkey`: moves the first replay file from `replay_source_dir`, sorted by filename, into `replay_destination_dir`.
- Before keeping a replay, it confirms a video exists in `video_source_dir`. If one exists, it moves the replay, renames the newest video to the replay basename while keeping the video extension, and moves it into `video_destination_dir`.
- `skip_hotkey`: moves the first replay file from `replay_source_dir`, sorted by filename, into `skipped_replay_dir`.

Example: if the kept replay is `00042.replay` and the newest video is `SessionClip.mp4`, the moved video becomes `00042.mp4`.

## Setup

Install Python 3.10 or newer, then install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create your config:

```powershell
Copy-Item config.example.yaml config.yaml
```

Edit `config.yaml` with your actual folders and preferred hotkeys.

## Run

```powershell
python replay_hotkeys.py
```

Leave that console window open while playing. Press `Ctrl+C` in the console to quit.

On Windows, global hotkey libraries may require running the terminal as Administrator depending on your system permissions and what other apps are focused.

## Config Fields

- `replay_source_dir`: where new replay files appear.
- `replay_destination_dir`: where kept replay files are moved.
- `skipped_replay_dir`: where skipped replay files are moved.
- `video_source_dir`: where new captured videos appear.
- `video_destination_dir`: where renamed kept videos are moved.
- `keep_hotkey`: hotkey that keeps the next replay and pairs it with the newest video.
- `skip_hotkey`: hotkey that skips the next replay.
- `preview_hotkey`: hotkey that shows which replay would be kept or skipped next.
- `replay_extensions`: replay file extensions to include, without the leading dot.
- `video_extensions`: video file extensions to include, without the leading dot.
- `overwrite_existing`: when `false`, the app stops an operation instead of replacing a file with the same destination name.
- `notifications_enabled`: when `true`, hotkey actions show a small bottom-right overlay notification.
- `notification_duration_ms`: how long each overlay notification stays visible.
