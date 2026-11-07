"""USO-ROLL (N 1117, ceiling only): front-running the oil-ETF / GSCI monthly WTI roll.

Mechanism: USO (pre-2020: 100% front month, 4-day roll ~2 weeks before expiry, Feb 2009 - Apr 2020; from May 2020: first
10 trading days, holdings spread across months, discretionary) and GSCI trackers (5th-9th business day) sell F1 / buy F2
on a published schedule. The forced flow can only move the CALENDAR SPREAD (F2 vs F1); outright oil direction over the
window is not this mechanism. So the ceiling is the perfect-sign bound on the spread:

    bound = 12 windows/yr x E|d log(F2/F1) over window| x notional/equity x 50% capture

No signed outcome is read (ceiling-first). Data: EIA NYMEX WTI contract 1 / contract 2 daily settles (RCLC1/RCLC2,
free, 1985-2024-04; contract 1 rolls at CL expiry ~20th-22nd, so business days 1-10 sit inside one front contract);
ETF form USO vs USL (Yahoo, 2008-12+; USL = equal 12-month ladder). Output data/research/program/uso_roll_out.txt.
"""
from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tme_treasury import fetch_px  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parents[2]
D = ROOT / "data/research/uso_roll"
OUT = ROOT / "data/research/program/uso_roll_out.txt"
CAP = 0.5


def eia() -> pd.DataFrame:
    f1 = pd.read_csv(D / "RCLC1.csv", parse_dates=["date"]).set_index("date")["px"]
    f2 = pd.read_csv(D / "RCLC2.csv", parse_dates=["date"]).set_index("date")["px"]
    df = pd.concat({"f1": f1, "f2": f2}, axis=1).dropna()
    df = df[(df.f1 > 0) & (df.f2 > 0)]  # 2020-04-20 negative settle
    df["s"] = np.log(df.f2 / df.f1)
    return df


def yahoo(t: str) -> pd.Series:
    f = D / f"px_{t}.csv"
    if not f.exists():
        fetch_px(t, "2008-01-01").to_csv(f)
    return pd.read_csv(f, parse_dates=["date"]).set_index("date")["adjclose"].dropna()


def windows(idx: pd.DatetimeIndex, b0: int, b1: int) -> list[tuple[pd.Timestamp, pd.Timestamp]]:
    """(entry close, exit close): close of bday b0-1 -> close of bday b1 (1-based business days of the month)."""
    out = []
    s = pd.Series(idx, index=idx)
    for _, g in s.groupby([idx.year, idx.month]):
        d = list(g)
        if len(d) < b1 + 1:
            continue
        start = d[b0 - 2] if b0 >= 2 else None
        if start is None:
            continue
        out.append((start, d[b1 - 1]))
    return out


def absmove(x: pd.Series, w: list[tuple[pd.Timestamp, pd.Timestamp]]) -> tuple[int, float]:
    m = [abs(x[b] - x[a]) for a, b in w]
    return len(m), float(np.mean(m))


def rand_absmove(x: pd.Series, n: int) -> float:
    return float(x.diff(n).abs().mean())


def main() -> str:
    L = ["USO-ROLL ceiling (N 1117): perfect-sign bound on the WTI calendar spread over published roll windows", "",
         "bound %/yr = 12 x E|d spread over window| x notional/equity x 50%; sign of every window assumed KNOWN", ""]
    df = eia()
    s = df["s"]
    eras = [("1985-2008 (pre-USO 4-day roll; GSCI pre/peri-Mou)", "1985", "2008"),
            ("2009-2015 (USO 4-day roll era, post-Mou)", "2009", "2015"),
            ("2016-2020-03", "2016", "2020-03"),
            ("2020-05..2024-04 (USO 10-day, multi-month)", "2020-05", "2024-04")]
    specs = [("GSCI roll bdays 5-9", 5, 9), ("USO pre-2020 roll ~bdays 7-10", 7, 10),
             ("USO post-2020 bdays 1-10 (from close of prior month)", 1, 10)]
    L.append(f"{'window':52s} {'era':48s} {'n':>4s} {'E|ds| bp':>9s} {'rand bp':>8s} {'bound 1x':>9s} {'2x':>6s} {'3x':>6s}")
    best = 0.0
    for name, b0, b1 in specs:
        for en, a, b in eras:
            x = s.loc[a:b]
            if b0 == 1:  # need prior month's last close: use bday 0 = last bday of previous month
                w = []
                idx = x.index
                ser = pd.Series(idx, index=idx)
                grp = list(ser.groupby([idx.year, idx.month]))
                for i in range(1, len(grp)):
                    prev, cur = list(grp[i - 1][1]), list(grp[i][1])
                    if len(cur) >= b1:
                        w.append((prev[-1], cur[b1 - 1]))
            else:
                w = windows(x.index, b0, b1)
            n, m = absmove(x, w)
            r = rand_absmove(x, b1 - b0 + 1)
            bd = 12 * m * CAP * 100
            best = max(best, bd)
            L.append(f"{name:52s} {en:48s} {n:4d} {m*1e4:9.1f} {r*1e4:8.1f} {bd:8.2f}pp {2*bd:5.2f} {3*bd:5.2f}")
        L.append("")
    # ETF form: long USL / short USO (taxable only; Roth cannot short)
    uso, usl = yahoo("USO"), yahoo("USL")
    sp = (np.log(usl) - np.log(uso)).dropna()
    L.append("ETF form: log(USL) - log(USO) (long deferred ladder / short USO), Reg T: 1x per leg = 2x gross = max")
    for en, a, b in [("2009-2015", "2009", "2015"), ("2016-2020-03", "2016", "2020-03"),
                     ("2020-05..2026", "2020-05", "2026")]:
        x = sp.loc[a:b]
        for name, b0, b1 in [("USO pre-2020 roll ~bdays 7-10", 7, 10), ("GSCI bdays 5-9", 5, 9)]:
            n, m = absmove(x, windows(x.index, b0, b1))
            bd = 12 * m * CAP * 100
            best = max(best, bd)
            L.append(f"  {name:32s} {en:16s} n {n:4d}  E|d| {m*1e4:6.1f}bp  rand {rand_absmove(x, b1-b0+1)*1e4:6.1f}bp"
                     f"  bound {bd:5.2f}pp/yr")
    L += ["", f"max bound across windows/eras/forms at 1x notional: {best:.2f}pp/yr (gate +8pp at $10k)",
          "Roth: no short leg -> only USO outright timing; outright oil direction is not the roll mechanism, so the",
          "mechanism-attributable part is <= the spread bound above. Futures MCL calendar spreads (micro, ~$6-8k notional,",
          "low spread margin) are the only size-up path; not available in the Roth, taxable needs futures approval."]
    txt = "\n".join(L)
    OUT.write_text(txt + "\n")
    return txt


if __name__ == "__main__":
    print(main())
