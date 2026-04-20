"""Utility functions for Docksmith."""

import hashlib
import json
import os
import pathlib
import shutil
from typing import Dict, List, Set
from datetime import datetime, timezone


def get_docksmith_home() -> pathlib.Path:
    """Get ~/.docksmith path."""
    home = pathlib.Path.home()
    docksmith_home = home / ".docksmith"
    return docksmith_home


def ensure_docksmith_dirs() -> None:
    """Ensure ~/.docksmith subdirectories exist."""
    home = get_docksmith_home()
    (home / "images").mkdir(parents=True, exist_ok=True)
    (home / "layers").mkdir(parents=True, exist_ok=True)
    (home / "cache").mkdir(parents=True, exist_ok=True)


def sha256_file(filepath: pathlib.Path) -> str:
    """Compute SHA-256 hash of a file."""
    sha = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(65536)  # 64KB chunks
            if not data:
                break
            sha.update(data)
    return "sha256:" + sha.hexdigest()


def sha256_bytes(data: bytes) -> str:
    """Compute SHA-256 hash of bytes."""
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sha256_string(data: str) -> str:
    """Compute SHA-256 hash of a string."""
    return sha256_bytes(data.encode("utf-8"))


def iso8601_now() -> str:
    """Get current time as ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def find_files_glob(context_dir: pathlib.Path, patterns: List[str]) -> Set[pathlib.Path]:
    """
    Find files matching glob patterns.
    Supports * and ** globs.
    """
    files = set()
    context_dir = pathlib.Path(context_dir)
    
    for pattern in patterns:
        # Handle absolute paths in pattern by making them relative
        if pattern.startswith("/"):
            pattern = pattern.lstrip("/")
        
        # Use glob to find matching files
        for match in context_dir.glob(pattern):
            if match.is_file():
                files.add(match)
    
    return files


def parse_image_ref(ref: str) -> tuple:
    """
    Parse image reference like 'myapp:latest' or 'alpine'.
    Returns (name, tag)
    """
    if ":" in ref:
        parts = ref.rsplit(":", 1)
        return parts[0], parts[1]
    return ref, "latest"


def format_image_filename(name: str, tag: str) -> str:
    """Format image filename from name and tag."""
    return f"{name}_{tag}.json"


def parse_image_filename(filename: str) -> tuple:
    """Parse image filename to get name and tag."""
    if not filename.endswith(".json"):
        return None
    name_tag = filename[:-5]  # Remove .json
    if "_" not in name_tag:
        return None
    # Find the last underscore (tag can contain underscores in some image names)
    parts = name_tag.rsplit("_", 1)
    return parts[0], parts[1]
