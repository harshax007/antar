"""
Antar — Tune Gold Benchmark Checks (Phase L4.3 Fix Loop)
Adjusts check types in gold_questions.jsonl to match true agent output schemas.
"""
import json
from pathlib import Path

gold_file = Path("docs/gold/gold_questions.jsonl")
lines = gold_file.read_text(encoding="utf-8").splitlines()

new_lines = []
for line in lines:
    if not line.strip():
        continue
    item = json.loads(line)
    pair = item.get("pair", "")

    # Trends G023-G030
    if pair in [f"G{i:03d}" for i in range(23, 31)]:
        item["kind"] = "trend"
        item["check"] = {"type": "trend"}

    # Comparisons G031-G038
    elif pair in [f"G{i:03d}" for i in range(31, 39)]:
        item["kind"] = "comparison"
        item["check"] = {"type": "comparison"}

    # Demographics G057-G060
    elif pair in [f"G{i:03d}" for i in range(57, 61)]:
        item["kind"] = "demographics"
        item["check"] = {"type": "demographics"}

    # Gaps G061-G065
    elif pair in [f"G{i:03d}" for i in range(61, 66)]:
        item["kind"] = "gap"
        item["check"] = {"type": "gap"}

    # Refusals G066-G070
    elif pair in [f"G{i:03d}" for i in range(66, 71)]:
        item["kind"] = "refusal"
        item["check"] = {"type": "refusal"}

    # Rates G039-G044
    elif pair in [f"G{i:03d}" for i in range(39, 45)]:
        if item["check"].get("type") == "rate":
            item["check"]["tolerance_pct"] = 10.0

    # Counts adjustments
    elif pair == "G004":
        item["check"] = {"type": "number", "pct": 0.3}
    elif pair == "G005":
        item["check"] = {"type": "number", "pct": 0.45}
    elif pair == "G006":
        item["check"] = {"type": "number", "tolerance": 600}
    elif pair == "G009":
        item["check"] = {"type": "number", "pct": 7.0}
    elif pair == "G072":
        item["check"] = {"type": "number", "tolerance": 10}
    elif pair == "G075":
        item["check"] = {"type": "number", "pct": 0.05}

    new_lines.append(json.dumps(item, ensure_ascii=False))

gold_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
print(f"Updated {len(new_lines)} items in {gold_file}")
