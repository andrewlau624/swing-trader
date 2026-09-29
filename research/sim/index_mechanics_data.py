"""Data for research/sim/index_mechanics.py (addendum NN): hardcoded public calendars
and the one heavy-lock extraction from the daily panel.

    # heavy: loads the 2015-26 daily panel (~0.5 GB float32), hold the heavy lock
    PYTHONPATH=. .venv/bin/python -m research.sim.index_mechanics_data

Sources (fetched 2026-09-28):
  SP500_CHANGES  Wikipedia "Historical components of the S&P 500", changes table
                 (https://en.wikipedia.org/wiki/Historical_components_of_the_S%26P_500,
                 action=raw). Effective date = first column; announcement date = the date
                 of the cited S&P DJI press release (cite |date= or the yyyymmdd in its URL,
                 earliest). Kept: effective 2015-09 .. 2026-09 with an announcement 1-40 days
                 before the effective date (234 of 262 rows; the rest have no press-release
                 ref or a mis-dated one). Rows: (effective, announced, added, removed).
  RUSSELL_RECON  fourth Friday of June, effective after the close (FTSE Russell recon
                 calendars; LSEG "Russell US Indexes 2026 Reconstitution Key Facts"; from
                 2026 also December: 2026-12-11, rank day 2026-10-30).
"""
from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import numpy as np
import pandas as pd

SCR = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program")
CACHE = SCR / "cache_index_mechanics.pkl"
THEME_PANEL = Path(str(__import__("pathlib").Path(__file__).resolve().parents[2]) + "/data/research/program/add28/theme_panel.pkl")   # 2015-26 open/close/volume

RUSSELL_RECON = ["2016-06-24", "2017-06-23", "2018-06-22", "2019-06-28", "2020-06-26",
                 "2021-06-25", "2022-06-24", "2023-06-23", "2024-06-28", "2025-06-27",
                 "2026-06-26"]

SP500_CHANGES = [
    ("2026-09-21", "2026-09-04", "BE", "TAP"),
    ("2026-09-21", "2026-09-04", "P", "TTD"),
    ("2026-09-21", "2026-09-04", "ILMN", "BLDR"),
    ("2026-08-05", "2026-07-31", "FERG", "EA"),
    ("2026-06-30", "2026-06-23", "", "CAG"),
    ("2026-06-29", "2026-06-23", "HONA", ""),
    ("2026-06-22", "2026-06-05", "MRVL", "POOL"),
    ("2026-06-22", "2026-06-05", "FLEX", "CPB"),
    ("2026-06-02", "2026-05-27", "", "EPAM"),
    ("2026-06-01", "2026-05-27", "FDXF", ""),
    ("2026-05-07", "2026-04-30", "VEEV", "CTRA"),
    ("2026-04-09", "2026-04-06", "CASY", "HOLX"),
    ("2026-03-23", "2026-03-06", "VRT", "MTCH"),
    ("2026-03-23", "2026-03-06", "LITE", "MOH"),
    ("2026-03-23", "2026-03-06", "COHR", "LW"),
    ("2026-03-23", "2026-03-06", "SATS", "PAYC"),
    ("2026-02-09", "2026-02-04", "CIEN", "DAY"),
    ("2025-12-22", "2025-12-05", "CRH", "LKQ"),
    ("2025-12-22", "2025-12-05", "CVNA", "SOLS"),
    ("2025-12-22", "2025-12-05", "FIX", "MHK"),
    ("2025-12-11", "2025-12-08", "ARES", "K"),
    ("2025-09-22", "2025-09-05", "EME", "ENPH"),
    ("2025-09-22", "2025-09-05", "HOOD", "CZR"),
    ("2025-09-22", "2025-09-05", "APP", "MKTX"),
    ("2025-08-28", "2025-08-25", "IBKR", "WBA"),
    ("2025-07-23", "2025-07-18", "XYZ", "HES"),
    ("2025-07-18", "2025-07-14", "TTD", "ANSS"),
    ("2025-07-09", "2025-07-02", "DDOG", "JNPR"),
    ("2025-05-19", "2025-05-12", "COIN", "DFS"),
    ("2025-03-24", "2025-03-07", "DASH", "BWA"),
    ("2025-03-24", "2025-03-07", "TKO", "TFX"),
    ("2025-03-24", "2025-03-07", "WSM", "CE"),
    ("2025-03-24", "2025-03-07", "EXE", "FMC"),
    ("2024-12-23", "2024-12-06", "APO", "QRVO"),
    ("2024-12-23", "2024-12-06", "WDAY", "AMTM"),
    ("2024-12-23", "2024-12-18", "LII", "CTLT"),
    ("2024-11-26", "2024-11-21", "TPL", "MRO"),
    ("2024-10-01", "2024-09-24", "", "BBWI"),
    ("2024-09-30", "2024-09-24", "AMTM", ""),
    ("2024-09-23", "2024-09-06", "PLTR", "AAL"),
    ("2024-09-23", "2024-09-06", "DELL", "ETSY"),
    ("2024-09-23", "2024-09-06", "ERIE", "BIO"),
    ("2024-06-24", "2024-06-07", "KKR", "RHI"),
    ("2024-06-24", "2024-06-07", "CRWD", "CMA"),
    ("2024-06-24", "2024-06-07", "GDDY", "ILMN"),
    ("2024-05-08", "2024-05-03", "VST", "PXD"),
    ("2024-04-03", "2024-03-27", "", "XRAY"),
    ("2024-04-03", "2024-03-27", "", "VFC"),
    ("2024-04-01", "2024-03-27", "SOLV", ""),
    ("2024-03-18", "2024-03-01", "SMCI", "WHR"),
    ("2024-03-18", "2024-03-01", "DECK", "ZION"),
    ("2024-02-01", "2024-01-17", "DAY", "CDAY"),
    ("2023-12-18", "2023-12-01", "UBER", "SEE"),
    ("2023-12-18", "2023-12-01", "JBL", "ALK"),
    ("2023-12-18", "2023-12-01", "BLDR", "SEDG"),
    ("2023-10-18", "2023-10-13", "HUBB", "OGN"),
    ("2023-10-18", "2023-10-13", "LULU", "ATVI"),
    ("2023-10-03", "2023-09-28", "", "DXC"),
    ("2023-10-02", "2023-09-28", "VLTO", ""),
    ("2023-08-25", "2023-08-21", "KVUE", "AAP"),
    ("2023-06-20", "2023-06-02", "PANW", "DISH"),
    ("2023-05-04", "2023-05-01", "AXON", "FRC"),
    ("2023-03-20", "2023-03-03", "FICO", "LUMN"),
    ("2023-03-15", "2023-03-13", "BG", "SBNY"),
    ("2023-03-15", "2023-03-10", "PODD", "SIVB"),
    ("2023-01-05", "2022-12-28", "", "VNO"),
    ("2023-01-04", "2022-12-28", "GEHC", ""),
    ("2022-12-22", "2022-12-19", "STLD", "ABMD"),
    ("2022-12-19", "2022-12-12", "FSLR", "FBHS"),
    ("2022-12-19", "2022-12-12", "", "MBC"),
    ("2022-12-15", "2022-12-12", "MBC", ""),
    ("2022-11-01", "2022-10-27", "ACGL", "TWTR"),
    ("2022-10-12", "2022-10-06", "TRGP", "NLSN"),
    ("2022-10-03", "2022-09-23", "PCG", "CTXS"),
    ("2022-10-03", "2022-09-23", "EQT", "DRE"),
    ("2022-09-19", "2022-09-02", "CSGP", "PVH"),
    ("2022-09-19", "2022-09-02", "INVH", "PENN"),
    ("2022-06-21", "2022-06-03", "", "UA"),
    ("2022-06-21", "2022-06-03", "KDP", "UAA"),
    ("2022-06-21", "2022-06-03", "ON", "IPGP"),
    ("2022-06-08", "2022-06-03", "VICI", "CERN"),
    ("2022-04-11", "2022-04-07", "WBD", "DISCA"),
    ("2022-04-11", "2022-04-07", "", "DISCK"),
    ("2022-04-04", "2022-03-29", "CPT", "PBCT"),
    ("2022-03-02", "2022-02-25", "MOH", "INFO"),
    ("2022-02-15", "2022-02-10", "NDSN", "XLNX"),
    ("2021-12-20", "2021-12-03", "SBNY", "LEG"),
    ("2022-01-10", "2022-01-07", "WTW", "WLTW"),
    ("2021-12-20", "2021-12-03", "SEDG", "HBI"),
    ("2021-12-20", "2021-12-03", "FDS", "WU"),
    ("2021-12-14", "2021-12-07", "EPAM", "KSU"),
    ("2021-09-20", "2021-09-03", "MTCH", "PRGO"),
    ("2021-09-20", "2021-09-03", "CDAY", "UNM"),
    ("2021-09-20", "2021-09-03", "BRO", "NOV"),
    ("2021-08-30", "2021-08-24", "TECH", "MXIM"),
    ("2021-07-21", "2021-07-15", "MRNA", "ALXN"),
    ("2021-06-04", "2021-05-27", "", "HFC"),
    ("2021-06-03", "2021-05-27", "OGN", ""),
    ("2021-05-14", "2021-05-10", "CRL", "FLIR"),
    ("2021-04-20", "2021-04-15", "PTC", "VAR"),
    ("2021-03-22", "2021-03-12", "NXPI", "FLS"),
    ("2021-03-22", "2021-03-12", "PENN", "SLG"),
    ("2021-03-22", "2021-03-12", "GNRC", "XRX"),
    ("2021-03-22", "2021-03-12", "CZR", "VNT"),
    ("2021-02-12", "2021-02-08", "MPWR", "FTI"),
    ("2021-01-21", "2021-01-15", "TRMB", "CXO|| [[Concho Resources]]"),
    ("2021-01-07", "2020-12-30", "ENPH", "TIF"),
    ("2020-12-21", "2020-12-11", "TSLA", "AIV"),
    ("2020-10-12", "2020-10-05", "", "NBL"),
    ("2020-10-09", "2020-10-05", "VNT", ""),
    ("2020-10-07", "2020-10-01", "POOL", "ETFC"),
    ("2020-09-21", "2020-09-04", "ETSY", "HRB"),
    ("2020-09-21", "2020-09-04", "TER", "COTY"),
    ("2020-09-21", "2020-09-04", "CTLT", "KSS"),
    ("2020-06-22", "2020-06-12", "BIO", "ADS"),
    ("2020-06-22", "2020-06-12", "TDY", "HOG|| [[Harley-Davidson]]"),
    ("2020-06-22", "2020-06-12", "TYL", "JWN"),
    ("2020-05-22", "2020-05-18", "WST", "HP"),
    ("2020-05-12", "2020-05-06", "DPZ", "CPRI"),
    ("2020-05-12", "2020-05-06", "DXCM", "AGN"),
    ("2020-04-06", "2020-03-31", "", "M"),
    ("2020-04-06", "2020-03-31", "", "RTN"),
    ("2020-04-03", "2020-03-31", "OTIS", ""),
    ("2020-04-03", "2020-03-31", "CARR", ""),
    ("2020-03-02", "2020-02-27", "IR", "XEC"),
    ("2020-01-28", "2020-01-22", "PAYC", "WCG"),
    ("2019-12-23", "2019-12-13", "LYV", "AMG"),
    ("2019-12-23", "2019-12-13", "ZBRA", "TRIP"),
    ("2019-12-23", "2019-12-13", "STE", "MAC"),
    ("2019-12-09", "2019-12-02", "ODFL", "STI"),
    ("2019-12-05", "2019-11-27", "WRB", "VIAB"),
    ("2019-11-21", "2019-11-18", "NOW", "CELG"),
    ("2019-10-03", "2019-09-20", "LVS", "NKTR"),
    ("2019-09-26", "2019-09-20", "NVR", "JEF"),
    ("2019-09-23", "2019-09-17", "CDW", "TSS"),
    ("2019-08-09", "2019-08-01", "LDOS", "APC"),
    ("2019-08-09", "2019-08-01", "IEX", "FL"),
    ("2019-07-15", "2019-07-09", "TMUS", "RHT"),
    ("2019-07-01", "2019-06-24", "MKTX", "LLL"),
    ("2019-06-11", "2019-06-03", "AMCR", "BMS"),
    ("2019-06-07", "2019-06-03", "BMS", "MAT"),
    ("2019-06-03", "2019-05-28", "DD", "DWDP"),
    ("2019-06-03", "2019-05-28", "CTVA", "FLR"),
    ("2019-04-02", "2019-03-26", "DOW", "BHF"),
    ("2019-03-19", "2019-03-14", "FOXA", "FOXA"),
    ("2019-03-19", "2019-03-14", "FOX", "FOX"),
    ("2019-02-27", "2019-02-21", "WAB", "GT"),
    ("2019-02-15", "2019-02-08", "ATO", "NFX"),
    ("2019-01-18", "2019-01-15", "TFX", "PCG"),
    ("2019-01-02", "2018-12-27", "FRC", "SCG"),
    ("2018-12-03", "2018-11-26", "LW", "COL"),
    ("2018-12-03", "2018-11-26", "MXIM", "AET"),
    ("2018-12-03", "2018-11-26", "FANG", "SRCL"),
    ("2018-11-13", "2018-11-07", "JKHY", "EQT"),
    ("2018-11-06", "2018-10-30", "KEYS", "CA"),
    ("2018-10-11", "2018-10-04", "FTNT", "EVHC"),
    ("2018-10-01", "2018-09-25", "ROL", "ANDV"),
    ("2018-09-14", "2018-09-11", "WCG", "XL"),
    ("2018-08-28", "2018-08-23", "ANET", "GGP"),
    ("2018-07-02", "2018-06-25", "CPRT", "DPS"),
    ("2018-06-20", "2018-06-15", "FLT", "TWX"),
    ("2018-06-18", "2018-06-08", "BR", "RRC"),
    ("2018-06-18", "2018-06-08", "HFC", "AYI"),
    ("2018-06-07", "2018-06-04", "TWTR", "MON"),
    ("2018-06-05", "2018-05-31", "EVRG", "NAVI"),
    ("2018-05-31", "2018-05-25", "ABMD", "WYN"),
    ("2018-04-04", "2018-03-28", "MSCI", "CSRA"),
    ("2018-03-19", "2018-03-09", "TTWO", "SIG"),
    ("2018-03-19", "2018-03-09", "SIVB", "PDCO"),
    ("2018-03-19", "2018-03-09", "NKTR", "CHK"),
    ("2018-03-07", "2018-03-02", "IPGP", "SNI"),
    ("2018-01-03", "2017-12-28", "HII", "BCR"),
    ("2017-10-13", "2017-10-04", "NCLH", "LVLT"),
    ("2017-09-18", "2017-08-24", "CDNS", "SPLS"),
    ("2017-09-01", "2017-08-24", "DWDP", "DOW"),
    ("2017-09-01", "2017-08-24", "SBAC", "DD"),
    ("2017-08-29", "2017-08-24", "Q", "WFM"),
    ("2017-08-08", "2017-07-31", "BHF", "AN"),
    ("2017-07-26", "2017-07-19", "DRE", "RIG"),
    ("2017-07-26", "2017-07-19", "AOS", "BBBY"),
    ("2017-07-26", "2017-07-19", "PKG", "MUR"),
    ("2017-07-26", "2017-07-19", "RMD", "MNK"),
    ("2017-07-26", "2017-07-19", "MGM", "RAI"),
    ("2017-07-07", "2017-06-30", "BKR", "BHI"),
    ("2017-06-19", "2017-06-09", "HLT", "YHOO"),
    ("2017-06-19", "2017-06-09", "ALGN", "TDC"),
    ("2017-06-19", "2017-06-09", "ANSS", "R"),
    ("2017-06-19", "2017-06-12", "RE", "MJN"),
    ("2017-06-02", "2017-05-24", "INFO", "TGNA"),
    ("2017-04-05", "2017-03-29", "IT", "DNB"),
    ("2017-04-04", "2017-03-28", "DXC", "SWN"),
    ("2017-03-20", "2017-03-10", "AMD", "URBN"),
    ("2017-03-20", "2017-03-10", "RJF", "FTR"),
    ("2017-03-20", "2017-03-10", "ARE", "FSLR"),
    ("2017-03-16", "2017-03-13", "SNPS", "HAR"),
    ("2017-03-13", "2017-03-06", "DISH", "LLTC"),
    ("2017-03-02", "2017-02-23", "REG", "ENDP"),
    ("2017-03-01", "2017-02-23", "CBOE", "PBI"),
    ("2017-02-28", "2017-02-23", "INCY", "SE"),
    ("2017-01-05", "2017-01-03", "IDXX", "STJ"),
    ("2016-12-02", "2016-11-29", "MAA", "OI"),
    ("2016-12-02", "2016-11-29", "EVHC", "LM"),
    ("2016-09-30", "2016-09-27", "COTY", "DO"),
    ("2016-09-22", "2016-09-10", "COO", "HOT"),
    ("2016-09-08", "2016-08-31", "CHTR", "EMC"),
    ("2016-09-06", "2016-08-25", "MTD", "TYC"),
    ("2016-07-05", "2016-06-23", "FTV", "CPGX"),
    ("2016-07-01", "2016-06-29", "LNT", "GAS"),
    ("2016-07-01", "2016-06-23", "ALB", "TE"),
    ("2016-06-22", "2016-06-21", "FBHS", "CVC"),
    ("2016-06-03", "2016-05-27", "TDG", "BXLT"),
    ("2016-05-31", "2016-05-24", "AJG", "CCE"),
    ("2016-05-23", "2016-05-18", "LKQ", "ARG"),
    ("2016-05-18", "2016-05-13", "DLR", "TWC"),
    ("2016-05-13", "2016-05-10", "ALK", "SNDK"),
    ("2016-05-03", "2016-04-26", "AYI", "ADT"),
    ("2016-04-18", "2016-04-07", "ULTA", "THC"),
    ("2016-04-04", "2016-03-28", "FL", "CAM"),
    ("2016-03-30", "2016-03-24", "HOLX", "POM"),
    ("2016-03-30", "2016-03-24", "CNC", "ESV"),
    ("2016-03-07", "2016-03-04", "UDR", "GMCR"),
    ("2016-03-04", "2016-03-01", "AWK", "CNX"),
    ("2016-02-22", "2016-02-16", "CXO", "PCL"),
    ("2016-02-01", "2016-01-26", "CFG", "PCP"),
    ("2016-02-01", "2016-01-22", "FRT", "BRCM"),
    ("2016-01-19", "2016-01-15", "EXR", "ACE"),
    ("2016-01-05", "2015-12-28", "WLTW", "FOSL"),
    ("2015-12-29", "2015-12-22", "CHD", "ALTR"),
    ("2015-12-01", "2015-11-23", "CSRA", "CSC"),
    ("2015-11-19", "2015-11-12", "ILMN", "SIAL"),
    ("2015-11-18", "2015-11-09", "SYF", "GNW"),
    ("2015-11-02", "2015-10-27", "HPE", "HCBK"),
    ("2015-10-07", "2015-09-30", "VRSK", "JOY"),
    ("2015-09-02", "2015-08-27", "UAL", "HSP"),
]
ETF_RE = re.compile(r"\b(ETF|ETN|FUND|TRUST|SHARES|PROSHARES|DIREXION|ISHARES|SPDR|INVESCO)\b")
WINDOWS = ("S1", "S3", "S4", "gapA")   # S2 = -S4 window on adds, S5 = -S1 window on deletes


def events() -> pd.DataFrame:
    rows = []
    for eff, ann, add, rem in SP500_CHANGES:
        for kind, sym in (("add", add), ("del", rem)):
            if sym:
                rows.append((pd.Timestamp(eff), pd.Timestamp(ann), kind, sym.replace(".", ".")))
    return pd.DataFrame(rows, columns=["eff", "ann", "kind", "sym"])


def extract():
    P = pickle.load(open(THEME_PANEL, "rb"))
    C, O, V = P["close"], P["open"], P["volume"]
    dates = C.index
    syms = np.array(C.columns)
    meta = json.load(open("data/research/night/asset_meta.json"))
    stock = np.array([not ETF_RE.search((meta.get(s, {}).get("name") or "").upper()) for s in syms])
    Cv, Ov, Vv = C.values.astype("float64"), O.values.astype("float64"), V.values.astype("float64")
    R = np.full_like(Cv, np.nan); R[1:] = Cv[1:] / Cv[:-1] - 1
    vol20 = pd.DataFrame(R).rolling(20, min_periods=15).std().values * np.sqrt(252)
    adv20 = pd.DataFrame(Cv * Vv).rolling(20, min_periods=15).median().values
    nb = pd.DataFrame(np.isfinite(Cv).astype(float)).rolling(120, min_periods=1).sum().values
    col = {s: j for j, s in enumerate(syms)}
    ev = events()
    out = []
    for e in ev.itertuples():
        j = col.get(e.sym)
        a1 = int(np.searchsorted(dates, e.ann, side="right"))           # first session after the news
        t0 = int(np.searchsorted(dates, e.eff, side="left")) - 1        # last session before effective
        rec = dict(eff=e.eff, ann=e.ann, kind=e.kind, sym=e.sym, found=j is not None)
        if j is None or t0 < 25 or t0 + 6 >= len(dates):
            out.append(rec); continue
        t = t0
        if t0 + 1 < len(dates) and dates[t0 + 1] == e.eff:                # Wikipedia may list the trade day
            v0, v1 = Vv[t0, j], Vv[t0 + 1, j]
            if np.isfinite(v1) and (not np.isfinite(v0) or v1 > v0):
                t = t0 + 1
        rec.update(a1=dates[a1], T=dates[t], shifted=t != t0, n_run=t - a1,
                   price=Cv[t - 1, j], adv=adv20[t - 1, j], vol=vol20[max(a1 - 1, 0), j],
                   volT=Vv[t, j] / adv20[t - 1, j] * Cv[t - 1, j] if np.isfinite(adv20[t - 1, j]) else np.nan)
        w = {"S1": (a1, "c", t, "c"), "S3": (t, "c", t + 1, "o"), "S4": (t, "c", t + 5, "c"),
             "gapA": (a1 - 1, "c", a1, "o")}
        # placebo universe: same vol20 decile on the day before the window starts, price > 5, adv >= 20M
        for k, (i0, f0, i1, f1) in w.items():
            if k == "S1" and a1 >= t:
                continue
            p0 = (Cv if f0 == "c" else Ov)[i0]; p1 = (Cv if f1 == "c" else Ov)[i1]
            rec[k] = p1[j] / p0[j] - 1
            b = max(i0 - 1, 0)
            el = stock & (Cv[b] > 5) & (adv20[b] >= 2e7) & (nb[b] >= 120) & np.isfinite(vol20[b])
            el &= np.isfinite(p0) & np.isfinite(p1)
            el[j] = False
            vv = vol20[b]
            ve = vol20[b, j]
            if not np.isfinite(ve) or el.sum() < 100:
                continue
            qs = np.nanquantile(vv[el], np.linspace(0, 1, 11))
            dec = np.clip(np.searchsorted(qs, ve) - 1, 0, 9)
            m = el & (vv >= qs[dec]) & (vv <= qs[dec + 1])
            rec[k + "_pool"] = (p1[m] / p0[m] - 1).astype("float32")
        out.append(rec)
    df = pd.DataFrame(out)
    pickle.dump(df, open(CACHE, "wb"), protocol=4)
    print(df.found.mean(), df.T.notna().sum(), df.shifted.mean())




NCACHE = SCR / "cache_index_mechanics_N.pkl"


def night_v7():
    """V7's night picks (max_corr 0.7, name cap 0.10, as cost_resweep) and the x1.5 L2 variant's
    cap-0.15 sizing. Heavy (night_candidates + panel): run once under the lock."""
    from . import book as B
    N10 = B.night_days(max_corr=0.7, max_name_pct=0.10)
    N15 = B.night_days(max_corr=0.7, max_name_pct=0.15)
    pickle.dump({"N10": N10, "N15": N15}, open(NCACHE, "wb"), protocol=4)
    print(len(N10), len(N15))



D20CACHE = SCR / "cache_index_mechanics_d20.pkl"


def days2020():
    """2020 close-signal night days (crash.days_2020, max_corr 0.7). Heavy (panel2020): lock."""
    from . import crash as CR
    pickle.dump(CR.days_2020(0.7), open(D20CACHE, "wb"), protocol=4)


if __name__ == "__main__":
    import sys
    if "night" in sys.argv:
        night_v7()
    elif "d2020" in sys.argv:
        days2020()
    else:
        extract()
