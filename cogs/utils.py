import sqlite3
from datetime import datetime

def get_setting(key, default=None):
    conn = sqlite3.connect('dmzcord.db')
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

def format_timestamp(iso_timestamp: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_timestamp)
        return dt.strftime("%d-%m-%Y %H:%M:%S")
    except ValueError:
        return "Invalid timestamp"

def format_table(rows: list) -> str:
    if not rows:
        return ""
    col_widths = [max(len(str(item)) for item in col) for col in zip(*rows)]
    lines = []
    for row in rows:
        line = "  ".join(str(item).ljust(width) for item, width in zip(row, col_widths))
        lines.append(line)
    return "```\n" + "\n".join(lines) + "\n```"