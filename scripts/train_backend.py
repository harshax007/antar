import asyncio
import time
import sys
for _stream in (sys.stdout, sys.stderr):
    try:
        if _stream and _stream.encoding and _stream.encoding.lower() not in ("utf-8", "utf8"):
            _stream.reconfigure(encoding="utf-8")
    except Exception:
        pass
import os

# Ensure the app module is in the path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.second_brain.consolidation import consolidate_nightly
from app.second_brain.index import BrainIndex
from app.services import zcql_local

from app.second_brain.store import load_all_embeddings_from_store

async def main():
    print("=" * 60)
    print(" Antar RAG Model 'Training' & Optimization")
    print("=" * 60)
    
    print("\n[1/3] Loading World Data...")
    world = zcql_local._world()
    fir_count = len(world.get("firs", []))
    suspect_count = len(world.get("suspects", []))
    print(f"      Found {fir_count} FIRs and {suspect_count} Suspects in database.")
    
    print("\n[2/3] Executing Graph Consolidation (Nightly Engine)...")
    t0 = time.time()
    await consolidate_nightly()
    t1 = time.time()
    print(f"      Consolidation complete in {t1 - t0:.2f} seconds.")
    print("      (Vectors deduplicated, edge scores aggregated, attention metrics mapped)")
    
    print("\n[3/3] Rebuilding FAISS Multimodal Index (768-dim)...")
    t0 = time.time()
    rows = await load_all_embeddings_from_store()
    index = BrainIndex()
    index.rebuild(rows)
    t1 = time.time()
    print(f"      Index rebuilt successfully in {t1 - t0:.2f} seconds.")
    
    print(f"\n✅ Training Complete. The Second Brain is optimized and ready for production inference.")

if __name__ == "__main__":
    asyncio.run(main())
