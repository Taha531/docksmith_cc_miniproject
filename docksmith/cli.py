"""CLI commands for Docksmith."""

import sys
import argparse
import pathlib
from typing import Optional, Dict

from build import BuildEngine
from image import ImageManifest, remove_image
from runtime import ContainerRuntime


def cmd_build(args) -> int:
    """docksmith build -t <name:tag> [--no-cache] <context_dir>"""
    try:
        # Parse image name and tag
        if ":" in args.tag:
            name, tag = args.tag.rsplit(":", 1)
        else:
            name = args.tag
            tag = "latest"
        
        # Create build engine
        engine = BuildEngine(args.context_dir, no_cache=args.no_cache)
        
        # Execute build
        manifest = engine.build(name, tag)
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_images(args) -> int:
    """docksmith images"""
    try:
        manifests = ImageManifest.list_all()
        
        if not manifests:
            print("No images found")
            return 0
        
        # Sort by name, then tag
        manifests.sort(key=lambda m: (m.name, m.tag))
        
        # Print header
        print("REPOSITORY          TAG                 IMAGE ID        CREATED")
        
        # Print each image
        for manifest in manifests:
            image_id = manifest.digest[7:19]  # sha256: + 12 chars
            print(
                f"{manifest.name:<20}{manifest.tag:<20}{image_id:<16}{manifest.created}"
            )
        
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_rmi(args) -> int:
    """docksmith rmi <name:tag>"""
    try:
        # Parse image reference
        if ":" in args.image:
            name, tag = args.image.rsplit(":", 1)
        else:
            name = args.image
            tag = "latest"
        
        # Remove image
        remove_image(name, tag)
        print(f"Deleted image {name}:{tag}")
        return 0
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def cmd_run(args) -> int:
    """docksmith run <name:tag> [cmd] [-e KEY=VALUE ...]"""
    try:
        # Parse image reference
        if ":" in args.image:
            name, tag = args.image.rsplit(":", 1)
        else:
            name = args.image
            tag = "latest"
        
        # Parse environment overrides
        env_overrides = {}
        if args.env:
            for env_str in args.env:
                if "=" not in env_str:
                    print(f"Error: Invalid environment variable format: {env_str}")
                    return 1
                key, val = env_str.split("=", 1)
                env_overrides[key] = val
        
        # Run container
        runtime = ContainerRuntime()
        exit_code = runtime.run(
            name,
            tag,
            command=args.cmd,
            env_overrides=env_overrides if env_overrides else None,
        )
        
        return exit_code
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main(argv=None):
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="docksmith",
        description="A simplified Docker-like build and runtime system",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # build command
    build_parser = subparsers.add_parser("build", help="Build an image from Docksmithfile")
    build_parser.add_argument(
        "-t", "--tag",
        required=True,
        help="Name and optionally tag of the image (format: name[:tag])",
    )
    build_parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Skip build cache",
    )
    build_parser.add_argument(
        "context_dir",
        help="Build context directory containing Docksmithfile",
    )
    build_parser.set_defaults(func=cmd_build)
    
    # images command
    images_parser = subparsers.add_parser("images", help="List all images")
    images_parser.set_defaults(func=cmd_images)
    
    # rmi command
    rmi_parser = subparsers.add_parser("rmi", help="Remove an image")
    rmi_parser.add_argument(
        "image",
        help="Image to remove (format: name[:tag])",
    )
    rmi_parser.set_defaults(func=cmd_rmi)
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run a container")
    run_parser.add_argument(
        "image",
        help="Image to run (format: name[:tag])",
    )
    run_parser.add_argument(
        "cmd",
        nargs="*",
        help="Command to execute",
    )
    run_parser.add_argument(
        "-e", "--env",
        action="append",
        help="Set environment variable (format: KEY=VALUE)",
    )
    run_parser.set_defaults(func=cmd_run)
    
    # Parse arguments
    args = parser.parse_args(argv)
    
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
