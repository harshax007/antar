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

if __name__ == "__main__":
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
