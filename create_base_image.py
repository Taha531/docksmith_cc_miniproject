#!/usr/bin/env python3
"""Create a base image for demonstration."""

import json
import pathlib
import sys
from datetime import datetime, timezone

# Add docksmith directory to path
sys.path.insert(0, str(pathlib.Path(__file__).parent / "docksmith"))

from util import sha256_string, iso8601_now, get_docksmith_home
from image import ImageManifest, ImageConfig, save_layer
import tarfile
from io import BytesIO

def create_base_image():
    """Create a minimal base image."""
    
    # Create image manifest
    manifest = ImageManifest(
        name="alpine",
        tag="3.18",
        created=iso8601_now(),
        config=ImageConfig(
            Env=[],
            Cmd=None,
            WorkingDir="/",
        ),
    )
    
    # Create a minimal root filesystem layer
    # This just has a few essential directories
    tar_io = BytesIO()
    with tarfile.open(fileobj=tar_io, mode="w") as tar:
        # Add basic directories
        for dirname in ["bin", "etc", "home", "tmp", "root", "var", "usr", "lib", "app"]:
            tarinfo = tarfile.TarInfo(name=dirname)
            tarinfo.type = tarfile.DIRTYPE
            tarinfo.mode = 0o755
            tarinfo.mtime = 0
            tar.addfile(tarinfo)
    
    tar_io.seek(0)
    layer_bytes = tar_io.getvalue()
    
    # Save layer using the proper function
    from util import sha256_bytes
    layer_digest = sha256_bytes(layer_bytes)
    
    # Save to proper location
    home = get_docksmith_home()
    (home / "layers").mkdir(parents=True, exist_ok=True)
    safe_digest = layer_digest.replace(":", "-")
    layer_path = home / "layers" / f"{safe_digest}.tar"
    with open(layer_path, "wb") as f:
        f.write(layer_bytes)
    
    # Add layer to manifest
    from image import LayerInfo
    manifest.layers.append(
        LayerInfo(
            digest=layer_digest,
            size=len(layer_bytes),
            createdBy="Initial base image",
        )
    )
    
    # Save manifest
    manifest.save()
    
    print(f"Created base image: alpine:3.18")
    print(f"Manifest saved to: {home / 'images' / 'alpine_3.18.json'}")


if __name__ == "__main__":
    create_base_image()
