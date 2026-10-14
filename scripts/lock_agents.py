"""Record the reviewed version of every agent module and system prompt in agents.lock.json.

    python scripts/lock_agents.py          write the lock
    python scripts/lock_agents.py --check  say what changed since the last lock (exit 1 if anything)

Run it after an intended change to an agent or a prompt, and commit the lock with the change.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from app.agents import agent_lock  # noqa: E402

if "--check" in sys.argv:
    st = agent_lock.status()
    print("prompt version:", st.get("prompt_version"))
    for c in st.get("changed") or []:
        print("CHANGED:", c)
    print(st.get("note") or ("in step with the lock" if st["ok"] else "differs from the lock"))
    sys.exit(0 if st["ok"] else 1)

now = agent_lock.write_lock()
print(f"locked {len(now['modules'])} agents and {len(now['prompts'])} prompts; prompt version {now['prompt_version']}")
