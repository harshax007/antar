import json
import re

transcript_path = r"C:\Users\hx07-\.gemini\antigravity\brain\74d1cdb6-2593-400d-9e36-904acf025a93\.system_generated\logs\transcript.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
            tools = data.get("tool_calls", [])
            for t in tools:
                if t.get("function", {}).get("name") == "default_api:run_command":
                    args = t.get("function", {}).get("arguments", {})
                    cmd = args.get("CommandLine", "")
                    if "BrainStructure.jsx" in cmd or "DataOverview.jsx" in cmd or "BrainLoader.jsx" in cmd:
                        print(f"--- Step {data.get('step_index')} ---")
                        print(cmd[:500])
