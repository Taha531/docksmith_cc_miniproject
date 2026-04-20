"""Build cache management."""

import json
import pathlib
from typing import Optional

from util import (
    sha256_bytes,
    sha256_string,
    get_docksmith_home,
    ensure_docksmith_dirs,
)


class BuildCache:
    """Manages build cache."""
    
    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.cache_index_file = None
        self._cache_index = {}
        if self.enabled:
            ensure_docksmith_dirs()
            home = get_docksmith_home()
            cache_dir = home / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_index_file = cache_dir / "index.json"
            self._load_index()
    
    def _load_index(self) -> None:
        """Load cache index from disk."""
        if self.cache_index_file and self.cache_index_file.exists():
            with open(self.cache_index_file, "r") as f:
                self._cache_index = json.load(f)
        else:
            self._cache_index = {}
    
    def _save_index(self) -> None:
        """Save cache index to disk."""
        if self.cache_index_file:
            with open(self.cache_index_file, "w") as f:
                json.dump(self._cache_index, f, indent=2)
    
    def compute_cache_key(
        self,
        prev_layer_digest: str,
        instruction_text: str,
        workdir: str,
        env_vars: dict,
        source_files_digests: Optional[str] = None,
    ) -> str:
        """
        Compute cache key from instruction and context.
        
        Args:
            prev_layer_digest: Digest of previous layer (or base image digest for first layer)
            instruction_text: Full instruction text as written
            workdir: Current working directory
            env_vars: Dict of environment variables
            source_files_digests: Concatenated SHA256 hashes of source files (for COPY)
        
        Returns:
            Cache key as sha256
        """
        # Sort environment variables
        env_parts = []
        for key in sorted(env_vars.keys()):
            env_parts.append(f"{key}={env_vars[key]}")
        env_str = ";".join(env_parts)
        
        # Concatenate all parts
        cache_input = (
            prev_layer_digest +
            "|" +
            instruction_text +
            "|" +
            workdir +
            "|" +
            env_str +
            "|" +
            (source_files_digests or "")
        )
        
        return sha256_string(cache_input)
    
    def get(self, cache_key: str) -> Optional[str]:
        """Get cached layer digest for a key. Returns None if not found."""
        if not self.enabled:
            return None
        return self._cache_index.get(cache_key)
    
    def put(self, cache_key: str, layer_digest: str) -> None:
        """Store mapping from cache key to layer digest."""
        if not self.enabled:
            return
        self._cache_index[cache_key] = layer_digest
        self._save_index()
    
    def reset(self) -> None:
        """Clear all cache entries (for --no-cache)."""
        self._cache_index = {}
        if self.cache_index_file and self.cache_index_file.exists():
            self.cache_index_file.unlink()
