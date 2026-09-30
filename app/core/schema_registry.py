"""
Schema Registry Module
Exposes live database schema to LLM agents dynamically to prevent hallucination.
"""
import sqlite3
from typing import List, Dict

from app.core.db_path import DB_PATH

_KNOWN_TABLES = {"FIRs", "crimes", "suspects", "crime_suspects"}


def get_table_schema(table_name: str) -> List[Dict]:
    """Dynamically fetches schema so LLMs don't hallucinate."""
    if table_name not in _KNOWN_TABLES:       # PRAGMA cannot take a bound parameter
        return [{"error": "unknown table"}]
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        conn.close()
        
        return [
            {"name": col[1], "type": col[2], "notnull": bool(col[3]), "default": col[4], "pk": bool(col[5])}
            for col in columns
        ]
    except Exception as e:
        from app.core.security import public_message
        return [{"error": public_message(e, "db")}]

def get_db_schema_context() -> str:
    """Returns a markdown string of the schema for injection into LLM prompts."""
    tables = ["FIRs", "crimes", "suspects", "crime_suspects"]
    context = "### Current Live Database Schema\n\n"
    for table in tables:
        schema = get_table_schema(table)
        context += f"**Table: {table}**\n"
        for col in schema:
            if "error" in col:
                context += f"- Error reading table: {col['error']}\n"
            else:
                context += f"- `{col['name']}` ({col['type']})\n"
        context += "\n"
    return context
