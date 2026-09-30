import json
import re

transcript_path = r"C:\Users\hx07-\.gemini\antigravity\brain\74d1cdb6-2593-400d-9e36-904acf025a93\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
            tools = data.get("tool_calls", [])
            for t in tools:
                args = json.dumps(t.get("function", {}).get("arguments", {}))
                if "BrainStructure.jsx" in args or "DataOverview.jsx" in args:
                    print(f"--- Step {data.get('step_index')} Tool: {t.get('function', {}).get('name')} ---")
