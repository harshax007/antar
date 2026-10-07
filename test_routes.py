
import asyncio, sys, sqlite3, os
from app.services.zcql_local import DB_PATH
from app.agents.heuristics import heuristic_select
from app.agents.agentic_spine import _route
sys.stdout.reconfigure(encoding='utf-8')
async def main():
    c = sqlite3.connect(os.path.join(os.path.dirname(DB_PATH), 'intelligent.db'))
    rows = c.execute('SELECT question_en FROM question_bank').fetchall()
    c.close()
    for r in rows:
        q = r[0]
        sel = await heuristic_select(q, 'en')
        if sel.get('template_id') in ('NONE', 'CLARIFY'):
            routes, _ = _route(q)
            print(q, '->', routes)
asyncio.run(main())

