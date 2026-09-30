"""
Measure the QuickML endpoint's real success rate with MINIMAL requests
(single attempt each, spaced) — isolates platform health from our prompt size.

Run:  python -m scripts.quickml_ping
"""

from __future__ import annotations

import asyncio
import sys
import time

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.services.quickml import quickml_generate

N = 8


async def main() -> None:
    print(f"Pinging the QuickML endpoint {N}× (minimal prompt, 1 attempt each, 2s apart)…\n")
    ok = 0
    for i in range(1, N + 1):
        t0 = time.time()
        try:
            out = await quickml_generate(system="Be concise.", user="Say OK.",
                                         max_tokens=16, temperature=0.7, retries=0)
            ok += 1
            print(f"  {i}: ✅ {time.time() - t0:4.1f}s  → {out[:40]!r}")
        except Exception as e:
            print(f"  {i}: ❌ {time.time() - t0:4.1f}s  → {str(e)[:220]}")
        await asyncio.sleep(2)
    print(f"\n→ {ok}/{N} succeeded ({100*ok//N}%).")
    if ok == N:
        print("   Endpoint healthy for short prompts → if chat still 500s, the long routing")
        print("   prompt is the trigger; tell me and I'll compact it.")
    elif ok == 0:
        print("   Endpoint is down/erroring right now → wait & retry; the app uses offline fallback meanwhile.")
    else:
        print("   Intermittent 500s (cold-start/rate). Warm-up + retries + fallback handle this;")
        print("   first query after idle may be offline, subsequent ones fluent.")


if __name__ == "__main__":
    asyncio.run(main())
