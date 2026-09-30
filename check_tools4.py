import json

transcript_path = r"C:\Users\hx07-\.gemini\antigravity\brain\74d1cdb6-2593-400d-9e36-904acf025a93\.system_generated\logs\transcript_full.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
            tools = data.get("tool_calls", [])
            for t in tools:
                if t.get("function", {}).get("name") == "default_api:replace_file_content":
                    args = t.get("function", {}).get("arguments", {})
                    target = args.get("TargetFile", "")
                    if "BrainStructure" in target or "DataOverview" in target or "BrainLoader" in target or "globals.css" in target:
                        print(f"--- Step {data.get('step_index')} (replace_file_content) ---")
                        print(f"Target: {target}")
                        # Print the replacement content to a file so we can view it
                        with open(f"D:\\Project\\recovered_step_{data.get('step_index')}.txt", "w", encoding="utf-8") as outf:
                            outf.write(json.dumps(args, indent=2))
