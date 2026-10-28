import os
import sys
import subprocess

def install_dependencies():
    print("📦 Missing dependencies detected! Forcing pip install at runtime...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully!")
    except Exception as e:
        print(f"❌ Failed to install dependencies: {e}")

def log_capacity():
    """One line per resource at start-up: where the database will be staged, how much room
    that has, and how much memory the container may use. AppSail's disk and memory limits
    decide whether the expanded register fits, and only the running container can say."""
    import shutil
    import tempfile
    for label, path in (("tmp", tempfile.gettempdir()), ("app", os.getcwd())):
        try:
            u = shutil.disk_usage(path)
            print(f"[capacity] {label} {path}: total {u.total / 1048576:.0f} MB, free {u.free / 1048576:.0f} MB")
        except OSError as e:
            print(f"[capacity] {label} {path}: {e}")
    try:
        with open("/proc/mounts") as fh:
            for line in fh:
                parts = line.split()
                if len(parts) > 2 and parts[1] in ("/", "/tmp", "/app"):
                    print(f"[capacity] mount {parts[1]}: {parts[2]} {parts[3][:60]}")
    except OSError:
        pass
    for path in ("/sys/fs/cgroup/memory.max", "/sys/fs/cgroup/memory/memory.limit_in_bytes"):
        try:
            with open(path) as fh:
                raw = fh.read().strip()
            print(f"[capacity] memory limit: {raw if raw == 'max' else f'{int(raw) / 1048576:.0f} MB'}")
            break
        except (OSError, ValueError):
            continue
    try:
        with open("/proc/meminfo") as fh:
            info = dict(line.split(":", 1) for line in fh if ":" in line)
        print(f"[capacity] meminfo: total {info['MemTotal'].strip()}, available {info['MemAvailable'].strip()}")
    except (OSError, KeyError):
        pass


if __name__ == "__main__":
    log_capacity()
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not found. Ensure dependencies are installed.")
        sys.exit(1)
        
    try:
        from main import app  # Import it directly here to catch errors early
        from dotenv import load_dotenv
        load_dotenv()
        
        port_str = (
            os.environ.get("X_ZOHO_CATALYST_LISTEN_PORT")
            or os.environ.get("PORT")
            or os.environ.get("APP_PORT")
            or "8000"
        )
        port = int(port_str)
        print(f"🚀 Starting Uvicorn server on 0.0.0.0:{port} (detected from env)...")
        
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"CRITICAL STARTUP ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
