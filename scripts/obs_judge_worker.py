import asyncio
import sys
from pathlib import Path

# Force UTF-8 so console output is safe on Windows platforms
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add backend root to sys.path so app modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import settings

async def main():
    if not getattr(settings, "OBS_ENABLED", False) or not getattr(settings, "OBS_JUDGE_ENABLED", True):
        print("Observability or Judge is disabled in settings. Exiting.")
        return

    from app.obs import store
    store.init_db()

    print("🚀 Started Observability Judge Worker & SDAR Generator")
    from app.obs.judge import score_pending
    from app.obs.sdar_generator import process_sdar_pending
    
    while True:
        try:
            done = await score_pending(20)
            if done > 0:
                print(f"✅ Judged {done} pending traces.")
                
            sdar_done = await process_sdar_pending(2)
            if sdar_done > 0:
                print(f"✅ Generated {sdar_done} SDAR groups.")
                
        except Exception as e:
            print(f"⚠️ Worker error: {e}")
        
        # Sleep for 30 seconds before next sweep to ensure efficiency
        await asyncio.sleep(30)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped.")
