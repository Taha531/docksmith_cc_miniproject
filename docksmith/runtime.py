"""Container runtime execution."""

import pathlib
import tempfile
import shutil
import subprocess
import os
from typing import List, Dict, Optional

from image import ImageManifest, load_layer
from util import parse_image_ref


class ContainerRuntime:
    """Handles container runtime execution."""
    
    def run(
        self,
        image_name: str,
        image_tag: str,
        command: Optional[List[str]] = None,
        env_overrides: Optional[Dict[str, str]] = None,
    ) -> int:
        """
        Run a container from an image.
        
        Args:
            image_name: Image name
            image_tag: Image tag
            command: Command to execute (overrides CMD)
            env_overrides: Environment variable overrides
        
        Returns:
            Exit code of the process
        """
        # Load image manifest
        manifest = ImageManifest.load(image_name, image_tag)
        if not manifest:
            raise FileNotFoundError(f"Image not found: {image_name}:{image_tag}")
        
        # Create temporary root filesystem
        fs_root = tempfile.mkdtemp()
        
        try:
            # Extract all layers
            for layer in manifest.layers:
                layer_bytes = load_layer(layer.digest)
                if not layer_bytes:
                    raise FileNotFoundError(f"Layer not found: {layer.digest}")
                self._extract_layer(fs_root, layer_bytes)
            
            # Prepare environment
            env = os.environ.copy()
            
            # Add image environment variables
            for env_str in manifest.config.Env:
                if "=" in env_str:
                    key, val = env_str.split("=", 1)
                    env[key] = val
            
            # Apply overrides
            if env_overrides:
                env.update(env_overrides)
            
            # Determine command to execute
            if command is None:
                if manifest.config.Cmd is None:
                    raise ValueError(
                        f"Image {image_name}:{image_tag} has no default CMD and no command given"
                    )
                command = manifest.config.Cmd
            
            # Get working directory
            workdir = manifest.config.WorkingDir or "/"
            
            # Execute container
            return self._execute_container(
                fs_root, command, workdir, env
            )
        finally:
            # Clean up
            shutil.rmtree(fs_root)
    
    def _extract_layer(self, fs_root: str, tar_bytes: bytes) -> None:
        """Extract a tar layer into the filesystem root."""
        import tarfile
        from io import BytesIO
        
        tar_io = BytesIO(tar_bytes)
        with tarfile.open(fileobj=tar_io, mode="r") as tar:
            tar.extractall(path=fs_root)
    
    def _execute_container(
        self,
        fs_root: str,
        command: List[str],
        workdir: str,
        env: Dict[str, str],
    ) -> int:
        """
        Execute a command in an isolated container environment.
        
        For now, this is a simplified implementation that doesn't use chroot/unshare.
        On a real Linux system, it would use clone() with CLONE_NEWPID | CLONE_NEWNS.
        """
        import platform
        import shlex
        
        # Build the command - handle both list and string formats
        cmd_to_run = None
        
        if isinstance(command, list) and len(command) > 0:
            # If it's a list like ["python3", "app.py"], it could be:
            # 1. An executable with args
            # 2. A shell command that needs to be executed via shell
            
            # Try to execute directly first
            cmd_to_run = command
        elif isinstance(command, str) and command:
            # String command - need to execute via shell
            if os.name == "nt":
                cmd_to_run = ["cmd", "/c", command]
            else:
                cmd_to_run = ["sh", "-c", command]
        else:
            # Empty command
            print("Error: No command to execute")
            return 1
        
        try:
            # Compute working directory path
            if workdir.startswith("/"):
                workdir_path = os.path.join(fs_root, workdir[1:])
            else:
                workdir_path = os.path.join(fs_root, workdir)
            
            # Create working directory if it doesn't exist
            os.makedirs(workdir_path, exist_ok=True)
            
            # On Windows, it's harder to execute shell commands and list commands
            # directly. We'll wrap everything in a shell command
            if os.name == "nt" and isinstance(command, list):
                # Convert list to string and execute via shell
                cmd_string = " ".join(f'"{arg}"' if " " in arg else arg for arg in command)
                cmd_to_run = ["cmd", "/c", cmd_string]
            
            result = subprocess.run(
                cmd_to_run,
                cwd=workdir_path,
                env=env,
                capture_output=False,
            )
            return result.returncode
        except Exception as e:
            print(f"Error executing container: {e}")
            return 1
