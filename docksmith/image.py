"""Image manifest and storage management."""

import json
import pathlib
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone

from util import (
    sha256_bytes,
    sha256_string,
    iso8601_now,
    get_docksmith_home,
    ensure_docksmith_dirs,
    format_image_filename,
    parse_image_filename,
)


@dataclass
class LayerInfo:
    """Represents a layer in an image."""
    digest: str
    size: int
    createdBy: str


@dataclass
class ImageConfig:
    """Container configuration."""
    Env: List[str] = field(default_factory=list)
    Cmd: Optional[List[str]] = None
    WorkingDir: str = "/"


@dataclass
class ImageManifest:
    """Image manifest structure."""
    name: str
    tag: str
    digest: str = ""  # Computed, can be empty during construction
    created: str = ""
    config: ImageConfig = field(default_factory=ImageConfig)
    layers: List[LayerInfo] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        config_dict = {
            "Env": self.config.Env,
            "WorkingDir": self.config.WorkingDir,
        }
        if self.config.Cmd is not None:
            config_dict["Cmd"] = self.config.Cmd
        
        return {
            "name": self.name,
            "tag": self.tag,
            "digest": self.digest,
            "created": self.created,
            "config": config_dict,
            "layers": [
                {
                    "digest": layer.digest,
                    "size": layer.size,
                    "createdBy": layer.createdBy,
                }
                for layer in self.layers
            ],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ImageManifest":
        """Create manifest from dictionary."""
        config_data = data.get("config", {})
        config = ImageConfig(
            Env=config_data.get("Env", []),
            Cmd=config_data.get("Cmd"),
            WorkingDir=config_data.get("WorkingDir", "/"),
        )
        
        layers = [
            LayerInfo(
                digest=l["digest"],
                size=l["size"],
                createdBy=l["createdBy"],
            )
            for l in data.get("layers", [])
        ]
        
        return ImageManifest(
            name=data["name"],
            tag=data["tag"],
            digest=data.get("digest", ""),
            created=data.get("created", ""),
            config=config,
            layers=layers,
        )

    def compute_digest(self) -> str:
        """Compute the digest for this manifest."""
        # Create a copy with digest set to empty string
        manifest_copy = ImageManifest(
            name=self.name,
            tag=self.tag,
            digest="",
            created=self.created,
            config=self.config,
            layers=self.layers,
        )
        # Serialize to JSON with compact format
        manifest_json = json.dumps(
            manifest_copy.to_dict(),
            separators=(",", ":"),
            sort_keys=True,
        )
        return sha256_string(manifest_json)

    def save(self) -> None:
        """Save manifest to ~/.docksmith/images/."""
        ensure_docksmith_dirs()
        
        # Set created timestamp if not already set
        if not self.created:
            self.created = iso8601_now()
        
        # Compute digest
        self.digest = self.compute_digest()
        
        # Write to file
        home = get_docksmith_home()
        images_dir = home / "images"
        filename = format_image_filename(self.name, self.tag)
        filepath = images_dir / filename
        
        with open(filepath, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @staticmethod
    def load(name: str, tag: str) -> Optional["ImageManifest"]:
        """Load manifest from ~/.docksmith/images/."""
        ensure_docksmith_dirs()
        home = get_docksmith_home()
        images_dir = home / "images"
        filename = format_image_filename(name, tag)
        filepath = images_dir / filename
        
        if not filepath.exists():
            return None
        
        with open(filepath, "r") as f:
            data = json.load(f)
        
        return ImageManifest.from_dict(data)

    @staticmethod
    def list_all() -> List["ImageManifest"]:
        """List all images in ~/.docksmith/images/."""
        ensure_docksmith_dirs()
        home = get_docksmith_home()
        images_dir = home / "images"
        
        manifests = []
        for filepath in images_dir.glob("*.json"):
            try:
                with open(filepath, "r") as f:
                    data = json.load(f)
                manifests.append(ImageManifest.from_dict(data))
            except Exception:
                pass  # Skip malformed manifests
        
        return manifests


def save_layer(tar_bytes: bytes) -> str:
    """
    Save a layer tar file to ~/.docksmith/layers/.
    Returns the digest.
    """
    ensure_docksmith_dirs()
    digest = sha256_bytes(tar_bytes)
    home = get_docksmith_home()
    layers_dir = home / "layers"
    
    # Convert digest to safe filename (replace colon with dash)
    safe_digest = digest.replace(":", "-")
    filepath = layers_dir / f"{safe_digest}.tar"
    
    # Only write if not already present (immutable)
    if not filepath.exists():
        with open(filepath, "wb") as f:
            f.write(tar_bytes)
    
    return digest


def load_layer(digest: str) -> Optional[bytes]:
    """Load a layer tar file from ~/.docksmith/layers/."""
    ensure_docksmith_dirs()
    home = get_docksmith_home()
    layers_dir = home / "layers"
    
    # Convert digest to safe filename (replace colon with dash)
    safe_digest = digest.replace(":", "-")
    filepath = layers_dir / f"{safe_digest}.tar"
    
    if not filepath.exists():
        return None
    
    with open(filepath, "rb") as f:
        return f.read()


def remove_image(name: str, tag: str) -> None:
    """Remove an image manifest and all its layers."""
    ensure_docksmith_dirs()
    home = get_docksmith_home()
    images_dir = home / "images"
    filename = format_image_filename(name, tag)
    filepath = images_dir / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"Image {name}:{tag} not found")
    
    # Load manifest to get layers
    with open(filepath, "r") as f:
        data = json.load(f)
    
    manifest = ImageManifest.from_dict(data)
    
    # Remove layers
    layers_dir = home / "layers"
    for layer in manifest.layers:
        safe_digest = layer.digest.replace(":", "-")
        layer_path = layers_dir / f"{safe_digest}.tar"
        if layer_path.exists():
            layer_path.unlink()
    
    # Remove manifest
    filepath.unlink()
