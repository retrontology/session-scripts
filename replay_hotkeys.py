from __future__ import annotations

import argparse
import logging
import shutil
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable

import keyboard
import yaml


DEFAULT_CONFIG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_CONFIG_TEMPLATE = {
    "replay_source_dir": "C:/path/to/session/replays/inbox",
    "replay_destination_dir": "C:/path/to/kept/replays",
    "skipped_replay_dir": "C:/path/to/skipped/replays",
    "video_source_dir": "C:/path/to/source/videos",
    "video_destination_dir": "C:/path/to/kept/videos",
    "keep_hotkey": "ctrl+alt+k",
    "skip_hotkey": "ctrl+alt+s",
    "replay_extensions": ["rep"],
    "video_extensions": ["mp4", "mov", "mkv", "avi", "webm"],
    "overwrite_existing": False,
}


@dataclass(frozen=True)
class AppConfig:
    replay_source_dir: Path
    replay_destination_dir: Path
    skipped_replay_dir: Path
    video_source_dir: Path
    video_destination_dir: Path
    keep_hotkey: str
    skip_hotkey: str
    replay_extensions: tuple[str, ...]
    video_extensions: tuple[str, ...]
    overwrite_existing: bool


class ReplayHotkeyApp:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._operation_lock = threading.Lock()

    def handle_keep_hotkey(self) -> None:
        self._run_hotkey_operation("keep replay/video", self.keep_next_replay)

    def handle_skip_hotkey(self) -> None:
        self._run_hotkey_operation("skip replay", self.skip_next_replay)

    def _run_hotkey_operation(self, operation_name: str, operation: Callable[[], None]) -> None:
        try:
            operation()
        except Exception:
            logging.exception("Failed to %s", operation_name)

    def keep_next_replay(self) -> None:
        with self._operation_lock:
            replay = get_top_replay(
                self.config.replay_source_dir,
                self.config.replay_extensions,
            )
            if replay is None:
                logging.warning("No replay files found in %s", self.config.replay_source_dir)
                return

            moved_replay = move_file(
                replay,
                self.config.replay_destination_dir / replay.name,
                self.config.overwrite_existing,
            )
            logging.info("Moved replay: %s -> %s", replay, moved_replay)

            video = get_newest_video(
                self.config.video_source_dir,
                self.config.video_extensions,
            )
            if video is None:
                logging.warning(
                    "No video files found in %s after moving replay %s",
                    self.config.video_source_dir,
                    moved_replay.name,
                )
                return

            renamed_video = self.config.video_destination_dir / f"{moved_replay.stem}{video.suffix}"
            moved_video = move_file(video, renamed_video, self.config.overwrite_existing)
            logging.info("Moved video: %s -> %s", video, moved_video)

    def skip_next_replay(self) -> None:
        with self._operation_lock:
            replay = get_top_replay(
                self.config.replay_source_dir,
                self.config.replay_extensions,
            )
            if replay is None:
                logging.warning("No replay files found in %s", self.config.replay_source_dir)
                return

            moved_replay = move_file(
                replay,
                self.config.skipped_replay_dir / replay.name,
                self.config.overwrite_existing,
            )
            logging.info("Skipped replay: %s -> %s", replay, moved_replay)

    def run(self) -> None:
        keyboard.add_hotkey(self.config.keep_hotkey, self.handle_keep_hotkey)
        keyboard.add_hotkey(self.config.skip_hotkey, self.handle_skip_hotkey)

        logging.info("Listening for hotkeys.")
        logging.info("Keep replay/video: %s", self.config.keep_hotkey)
        logging.info("Skip replay: %s", self.config.skip_hotkey)
        logging.info("Press Ctrl+C in this window to quit.")

        keyboard.wait()


def normalize_extensions(extensions: Iterable[str]) -> tuple[str, ...]:
    normalized = []
    for extension in extensions:
        value = extension.strip().lower()
        if not value:
            continue
        normalized.append(value if value.startswith(".") else f".{value}")
    return tuple(normalized)


def get_top_replay(source_dir: Path, replay_extensions: tuple[str, ...]) -> Path | None:
    files = list_matching_files(source_dir, replay_extensions)
    return sorted(files, key=lambda path: path.name.lower())[0] if files else None


def get_newest_video(source_dir: Path, video_extensions: tuple[str, ...]) -> Path | None:
    files = list_matching_files(source_dir, video_extensions)
    return max(files, key=lambda path: path.stat().st_mtime) if files else None


def list_matching_files(source_dir: Path, extensions: tuple[str, ...]) -> list[Path]:
    if not source_dir.exists():
        logging.warning("Directory does not exist: %s", source_dir)
        return []

    if not source_dir.is_dir():
        logging.warning("Path is not a directory: %s", source_dir)
        return []

    return [
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    ]


def move_file(source: Path, destination: Path, overwrite_existing: bool) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not overwrite_existing:
            raise FileExistsError(
                f"Destination already exists: {destination}. "
                "Set overwrite_existing to true or move the existing file."
            )
        destination.unlink()

    return Path(shutil.move(str(source), str(destination)))


def load_config(config_path: Path) -> AppConfig:
    if not config_path.exists():
        create_default_config(config_path)
        raise FileNotFoundError(
            f"Created default config at {config_path}. Edit it with your folders and run again."
        )

    with config_path.open("r", encoding="utf-8") as file:
        raw_config = yaml.safe_load(file)

    if not isinstance(raw_config, dict):
        raise ValueError(f"Config file must contain a YAML mapping: {config_path}")

    return AppConfig(
        replay_source_dir=Path(raw_config["replay_source_dir"]).expanduser(),
        replay_destination_dir=Path(raw_config["replay_destination_dir"]).expanduser(),
        skipped_replay_dir=Path(raw_config["skipped_replay_dir"]).expanduser(),
        video_source_dir=Path(raw_config["video_source_dir"]).expanduser(),
        video_destination_dir=Path(raw_config["video_destination_dir"]).expanduser(),
        keep_hotkey=raw_config["keep_hotkey"],
        skip_hotkey=raw_config["skip_hotkey"],
        replay_extensions=normalize_extensions(raw_config["replay_extensions"]),
        video_extensions=normalize_extensions(raw_config["video_extensions"]),
        overwrite_existing=bool(raw_config.get("overwrite_existing", False)),
    )


def create_default_config(config_path: Path) -> None:
    with config_path.open("w", encoding="utf-8") as file:
        yaml.safe_dump(DEFAULT_CONFIG_TEMPLATE, file, sort_keys=False)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Global hotkeys for sorting Session replay and video recordings.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config YAML. Defaults to {DEFAULT_CONFIG_PATH}.",
    )
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    args = parse_args()

    try:
        config = load_config(args.config)
        ReplayHotkeyApp(config).run()
    except KeyboardInterrupt:
        logging.info("Exiting.")
        return 0
    except Exception as error:
        logging.error("%s", error)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
