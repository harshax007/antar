"""
Diagnose the live LLM chat path — shows the routing decision (template + params),
row count, and final answer. Helps see WHY a query returns no records.

Run:  python -m scripts.chat_diag           # English sample
      python -m scripts.chat_diag kn        # Kannada theft-hotspots sample
"""

from __future__ import annotations

import asyncio
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.core.settings import settings
from app.api.chat import _llm_available
from app.agents.query_agent import select_template, run_template, compose_answer
from app.services.quickml import quickml_generate

QUERIES = {
    "en": ("show robbery trends in Bengaluru North last 3 months", "en"),
    "kn": ("ಈ ತಿಂಗಳು ಕಳ್ಳತನದ ಪ್ರಮುಖ ಸ್ಥಳಗಳು ಎಲ್ಲಿವೆ?", "kn"),  # "where are theft hotspots this month?"
}


async def main() -> None:
    arg = sys.argv[1] if len(sys.argv) > 1 else "en"
    text, lang = QUERIES.get(arg, (arg, "en"))
    print(f"query ({lang}): {text}")
    print("_llm_available:", _llm_available(), "| DEMO_MODE:", settings.DEMO_MODE, "\n")

    if not (_llm_available() and not settings.DEMO_MODE):
        print("Chat is OFFLINE (creds/DEMO_MODE). Restart backend after setting .env.")
        return

    try:
        choice = await select_template(text, lang, {}, quickml_generate)
        print("LLM routing choice:", choice)
        tid = choice.get("template_id")
        if tid in (None, "NONE"):
            print("→ LLM did not pick a template.")
            return
        rows, cites = run_template(tid, choice.get("params", {}))
        print(f"→ template {tid} returned {len(rows)} rows")
        if rows:
            print("  sample row:", rows[0])
        answer, used_llm, _violations = await compose_answer(text, rows, lang, tid, quickml_generate)
        print(f"\nanswer (llm={used_llm}):\n{answer}")
    except Exception as e:
        print("❌ error:", repr(e))


if __name__ == "__main__":
    asyncio.run(main())
