"""Runbook snippet A (events by EDGAR form type), for the overnight loop. EDGAR renamed "SC 13D/G" to
"SCHEDULE 13D/G" in Dec 2024: pass both names so the 2024-26 half is not empty.

    PYTHONPATH=. .venv/bin/python -m research.sim.events_form_build NAME "FORM1|FORM2"
"""
import sys

import pandas as pd

from research.sim import event_fetch as F


def build(name: str, forms: list[str], busy_max: int = 50) -> pd.DataFrame:
    tick = F.company_tickers()
    rows = []
    for y in range(2020, 2027):
        for q in range(1, 5):
            if (y, q) > (2026, 3):
                break
            D = F.full_index(y, q)
            D = D[D.form.isin(forms)]
            busy = D.cik.value_counts()
            D = D[D.cik.map(busy) <= busy_max]      # drop filers/agents that file this form > 50x a quarter
            for cik, d in zip(D.cik, D.date):
                for t in tick.get(str(int(cik)), []):
                    rows.append((t, d))
    X = pd.DataFrame(rows, columns=["sym", "fd"]).drop_duplicates()
    X["fd"] = pd.to_datetime(X.fd)
    X.to_parquet(f"data/research/program/events_{name}.parquet")
    print(len(X), X.fd.min(), X.fd.max())
    print(X.groupby(X.fd.dt.year).size().to_dict())
    return X


if __name__ == "__main__":
    build(sys.argv[1], sys.argv[2].split("|"))
