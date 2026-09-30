import json
import re

transcript_path = r"C:\Users\hx07-\.gemini\antigravity\brain\74d1cdb6-2593-400d-9e36-904acf025a93\.system_generated\logs\transcript.jsonl"
with open(transcript_path, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        if data.get("source") == "MODEL" and data.get("type") == "PLANNER_RESPONSE":
            content = data.get("content", "")
            # Look for phrases like "I have updated" or "I have modified"
            if content and re.search(r'I have (?:updated|modified|changed|added|removed|implemented|fixed)', content, re.IGNORECASE):
                print(f"--- Step {data.get('step_index')} ---")
                print(content[:500] + ("..." if len(content) > 500 else ""))
