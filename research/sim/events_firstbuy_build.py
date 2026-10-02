from research.sim.outside_box import insider_buys
import pandas as pd
A = insider_buys()
print(A.fd.min(), A.fd.max(), len(A))
X = A[A.insider].sort_values("fd")
# first officer/director purchase filing at the issuer after >= 730 days with none (any insider row counts as history)
H = A.sort_values("fd")
rows = []
first_seen = H.groupby("sym").fd.min()
for s, g in X.groupby("sym"):
    allf = H[H.sym == s].fd.values
    for d in g.fd.drop_duplicates():
        prev = allf[allf < d.to_datetime64()]
        last = pd.Timestamp(prev.max()) if len(prev) else pd.Timestamp("2020-01-01")
        if (d - last).days >= 730:
            rows.append((s, d))
E = pd.DataFrame(rows, columns=["sym", "fd"]).drop_duplicates()
print(len(E), E.fd.min(), E.fd.max()); print(E.groupby(E.fd.dt.year).size())
E.to_parquet("data/research/program/events_firstbuy.parquet")
