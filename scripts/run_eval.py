import asyncio
import sys
import uuid
from pathlib import Path

# Add backend root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.obs import store
from app.obs.eval import run_evaluation_suite

async def main():
    store.init_db()
    run_id = f"eval_{uuid.uuid4().hex[:8]}"
    await run_evaluation_suite(run_id)

if __name__ == "__main__":
    asyncio.run(main())
