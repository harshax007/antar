import json

transcript_path = r"C:\Users\hx07-\.gemini\antigravity\brain\74d1cdb6-2593-400d-9e36-904acf025a93\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
            content = data.get("content", "")
            tools = data.get("tool_calls", [])
            if not tools and "I have " in content:
                print(f"--- Step {data.get('step_index')} (No tools) ---")
                print(content[:200])
