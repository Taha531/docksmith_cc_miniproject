# Docksmith Sample Application

This directory contains a complete sample application demonstrating all Docksmith features.

## Files

- `Docksmithfile` - Build specification using all 6 instructions (FROM, COPY, RUN, WORKDIR, ENV, CMD)
- `app.py` - Python application that prints output and reads environment variables
- This README

## Setup

Before running the sample, you need to create the base image:

```bash
cd ..
python3 create_base_image.py
```

This creates a minimal `alpine:3.18` base image in `~/.docksmith/images/`.

## Running the Demo

The demo shows all the features described in the specification:

### 1. Cold Build (All steps CACHE MISS)

```bash
cd sample-app
python3 ../docksmith/main.py build -t myapp:latest .
```

Expected output:

```
Step 1/5 : FROM alpine:3.18
Step 2/5 : COPY app.py /app [CACHE MISS] 0.XX s
Step 3/5 : WORKDIR /app
Step 4/5 : ENV MESSAGE="Hello from Docksmith!"
Step 5/5 : RUN echo "Build complete - application ready" [CACHE MISS] X.XX s
Successfully built sha256:XXXX... myapp:latest (X.XX s)
```

### 2. Warm Rebuild (All steps CACHE HIT)

Run the build command again:

```bash
python3 ../docksmith/main.py build -t myapp:latest .
```

Expected output:

```
Step 1/5 : FROM alpine:3.18
Step 2/5 : COPY app.py /app [CACHE HIT] 0.00 s
Step 3/5 : WORKDIR /app
Step 4/5 : ENV MESSAGE="Hello from Docksmith!"
Step 5/5 : RUN echo "Build complete - application ready" [CACHE HIT] 0.00 s
Successfully built sha256:XXXX... myapp:latest (0.00 s)
```

Note: The digest should be identical to the first build.

### 3. Incremental Build (Edit source file)

Edit `app.py` to change the message, then rebuild:

```bash
# Edit app.py
nano app.py

# Rebuild
python3 ../docksmith/main.py build -t myapp:latest .
```

Expected output:

```
Step 1/5 : FROM alpine:3.18
Step 2/5 : COPY app.py /app [CACHE MISS] 0.XX s
Step 3/5 : WORKDIR /app
Step 4/5 : ENV MESSAGE="Hello from Docksmith!"
Step 5/5 : RUN echo "Build complete - application ready" [CACHE HIT] 0.00 s
Successfully built sha256:YYYY... myapp:latest (X.XX s)
```

Note: Step 2 is MISS (because app.py changed), Step 5 becomes MISS (cascade), but Step 1 is still HIT.

### 4. List Images

```bash
python3 ../docksmith/main.py images
```

Expected output:

```
REPOSITORY          TAG                 IMAGE ID        CREATED
alpine              3.18                sha256:XXXX    2024-04-20T...
myapp               latest              sha256:YYYY    2024-04-20T...
```

### 5. Run Container

```bash
python3 ../docksmith/main.py run myapp:latest
```

Expected output:

```
==================================================
Sample Docksmith Application
==================================================

Environment MESSAGE: Hello from Docksmith!
Current working directory: /app
Files in current directory:
  - app.py

✓ Application is running in isolation
==================================================
```

### 6. Environment Variable Override

```bash
python3 ../docksmith/main.py run -e MESSAGE="Custom Message" myapp:latest
```

Expected output:

```
==================================================
Sample Docksmith Application
==================================================

Environment MESSAGE: Custom Message
Current working directory: /app
Files in current directory:
  - app.py

✓ Application is running in isolation
==================================================
```

### 7. Isolation Verification

Files created inside the container should NOT appear on the host. To verify:

```bash
# Create a test script
cat > test_isolation.py << 'EOF'
import subprocess
import os

# Run container with a command that creates a file
result = subprocess.run([
    "python3", "../docksmith/main.py", "run", "myapp:latest",
    "touch", "/app/test_file.txt"
], capture_output=True)

# Check if file exists on host
if os.path.exists("test_file.txt"):
    print("ERROR: File leaked to host filesystem!")
else:
    print("✓ File isolation verified - file did NOT leak to host")
EOF

python3 test_isolation.py
```

Expected output:

```
✓ File isolation verified - file did NOT leak to host
```

### 8. Remove Image

```bash
python3 ../docksmith/main.py rmi myapp:latest
```

Expected output:

```
Deleted image myapp:latest
```

Verify it's gone:

```bash
python3 ../docksmith/main.py images
```

Only `alpine:3.18` should remain.

## Implementation Details

### Docksmithfile Instructions

The sample Docksmithfile demonstrates all 6 instructions:

1. **FROM** - Loads the base `alpine:3.18` image
2. **COPY** - Copies app.py into the /app directory
3. **WORKDIR** - Sets the working directory to /app
4. **ENV** - Sets the MESSAGE environment variable
5. **RUN** - Executes a build step (demonstrates command execution)
6. **CMD** - Sets the default command to run the Python application

### Storage Layout

After running the demo, check the storage:

```bash
ls ~/.docksmith/
```

You should see:

- `images/` - Contains JSON manifests for alpine:3.18 and myapp:latest
- `layers/` - Contains tar files for each layer
- `cache/` - Contains the build cache index

## Troubleshooting

- **"Base image not found"**: Run `python3 ../create_base_image.py` first
- **Module import errors**: Ensure you're running from the `sample-app` directory
- **Permission errors**: On Windows, use appropriate Python paths

## Notes

- On Linux systems with proper permissions, isolation uses `chroot` + `unshare` syscalls
- On Windows/macOS, the current implementation provides simplified isolation
- For production use, native Linux containers are required
- All layer files are immutable once written
- Build cache ensures efficient rebuilds
