#!/usr/bin/env python3
"""Sample application for Docksmith demonstration."""

import os
import sys

def main():
    print("=" * 50)
    print("Sample Docksmith Application")
    print("=" * 50)
    
    # Read environment variable
    message = os.environ.get("MESSAGE", "No message set")
    print(f"\nEnvironment MESSAGE: {message}")
    
    # Show current working directory
    cwd = os.getcwd()
    print(f"Current working directory: {cwd}")
    
    # List files in current directory
    print("\nFiles in current directory:")
    try:
        for item in os.listdir("."):
            print(f"  - {item}")
    except Exception as e:
        print(f"  (Error listing files: {e})")
    
    # Demonstrate that we're isolated from host
    print("\n✓ Application is running in isolation")
    print("=" * 50)
    return 0

if __name__ == "__main__":
    sys.exit(main())
