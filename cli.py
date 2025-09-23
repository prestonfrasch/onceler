import sqlite3
from tabulate import tabulate

def totals(db="ai_impact.sqlite"):
    con = sqlite3.connect(db)
    rows = con.execute("""
     SELECT provider, COUNT(*), SUM(tokens_in), SUM(tokens_out),
            ROUND(SUM(kwh),6), ROUND(SUM(gco2),1), ROUND(SUM(liters),3)
     FROM hits GROUP BY provider ORDER BY 1
    """).fetchall()
    print(tabulate(rows, headers=["Provider","Calls","InTok","OutTok","kWh","gCO2","Liters"]))

if __name__ == "__main__":
    totals()
