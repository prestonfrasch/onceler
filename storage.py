import sqlite3
from dataclasses import dataclass
from contextlib import closing
import os

@dataclass
class Hit:
    ts_ms: int
    url: str
    provider: str
    tokens_in: int
    tokens_out: int
    kwh: float
    gco2: float
    liters: float

SCHEMA = """
CREATE TABLE IF NOT EXISTS hits (
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 ts_ms INTEGER,
 url TEXT,
 provider TEXT,
 tokens_in INTEGER,
 tokens_out INTEGER,
 kwh REAL,
 gco2 REAL,
 liters REAL
);
"""

class DB:
    def __init__(self, path: str | None = None):
        if path is None:
            # Default to ai_impact.sqlite in the same directory as storage.py
            path = os.path.join(os.path.dirname(__file__), "ai_impact.sqlite")
        self.path = path
        with closing(sqlite3.connect(self.path)) as con:
            con.execute(SCHEMA); con.commit()

    def insert(self, h: Hit):
        with closing(sqlite3.connect(self.path)) as con:
            con.execute("""INSERT INTO hits
            (ts_ms,url,provider,tokens_in,tokens_out,kwh,gco2,liters)
            VALUES (?,?,?,?,?,?,?,?)""",
            (h.ts_ms,h.url,h.provider,h.tokens_in,h.tokens_out,h.kwh,h.gco2,h.liters))
            con.commit()


    def totals(self, since_ms: int | None = None) -> dict[str, float]:
        import sqlite3
        from contextlib import closing
        q = "SELECT IFNULL(SUM(kwh),0), IFNULL(SUM(gco2),0), IFNULL(SUM(liters),0) FROM hits"
        args = ()
        if since_ms is not None:
            q += " WHERE ts_ms >= ?"
            args = (since_ms,)
        with closing(sqlite3.connect(self.path)) as con:
            kwh, gco2, liters = con.execute(q, args).fetchone()
        return {"kwh": float(kwh or 0), "gco2": float(gco2 or 0), "liters": float(liters or 0)}
