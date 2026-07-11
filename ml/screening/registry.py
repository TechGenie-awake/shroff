"""Negative-registry screening core — the `checkIdentifier` interface.

check_identifier(type, value) -> list of hit dicts shaped exactly for the
/api/screen contract:
    {"registry", "list_name", "matched_on", "confidence", "detail",
     "source_url", "is_sample"}

Confidence policy (BUILD-SPEC pillar 3):
  - exact ID joins on PAN / GSTIN / CIN / DIN  -> "high"
  - normalized-exact or fuzzy name matches     -> "advisory" (human-confirm)
    fuzzy = difflib SequenceMatcher ratio >= 0.92 on normalized names.

Stdlib only.
"""

from __future__ import annotations

import os
import re
import sqlite3
from difflib import SequenceMatcher

try:
    from .pan import gstin_to_pan, normalize_name, validate_din, validate_gstin, validate_pan
except ImportError:
    from pan import gstin_to_pan, normalize_name, validate_din, validate_gstin, validate_pan

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.db")

FUZZY_THRESHOLD = 0.92

# source key -> (human list name, source_url). Unknown keys fall back gracefully.
LIST_META = {
    "opensanctions:in_mha_banned": (
        "MHA banned organisations & individuals (UAPA schedules)",
        "https://data.opensanctions.org/datasets/latest/in_mha_banned/"),
    "opensanctions:in_nse_debarred": (
        "NSE/SEBI debarred entities",
        "https://data.opensanctions.org/datasets/latest/in_nse_debarred/"),
    "datagovin:mca_company_master_delhi": (
        "MCA Company Master — Strike Off (data.gov.in)",
        "https://data.gov.in/catalog/company-master-data"),
    "sample:mca_company_master": (
        "MCA struck-off companies register",
        "https://www.mca.gov.in/content/mca/global/en/data-and-reports/company-llp-info.html"),
    "sample:mahagst_nongenuine": (
        "Maharashtra GST non-genuine taxpayers",
        "https://mahagst.gov.in/en/list-of-non-genuine-tax-payers"),
    "sample:cbdt_tax_defaulters": (
        "CBDT income-tax defaulters (arrears)",
        "https://incometaxindia.gov.in/Pages/tax-defaulters.aspx"),
    "sample:mca_directors_struckoff": (
        "MCA directors of struck-off / disqualified directors (s.164(2))",
        "https://www.mca.gov.in/content/mca/global/en/data-and-reports/company-llp-info.html"),
    "sample:cibil_wilful_defaulters": (
        "Wilful defaulters — suit-filed accounts (bank-reported)",
        "https://suit.cibil.com/"),
    "sample:rbi_alert_list": (
        "RBI Alert List — unauthorised forex/ETP platforms",
        "https://rbi.org.in/Scripts/BS_ViewForexAlertList.aspx"),
    "sample:ibbi_cirp": (
        "IBBI CIRP corporate debtors",
        "https://ibbi.gov.in/en/orders/cirp"),
}

VALID_TYPES = ("pan", "gstin", "cin", "din", "name", "account", "vpa")


def _meta(source: str) -> tuple[str, str]:
    return LIST_META.get(source, (source or "unknown registry", ""))


def _hit(registry: str, source: str, matched_on: str, confidence: str,
         detail: str, is_sample) -> dict:
    list_name, url = _meta(source)
    return {
        "registry": registry,
        "list_name": list_name,
        "matched_on": matched_on,
        "confidence": confidence,
        "detail": detail,
        "source_url": url,
        "is_sample": bool(is_sample),
    }


def _connect(db_path: str | None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ------------------------------------------------------------ per-type checks

def _check_pan(conn, pan: str) -> list[dict]:
    hits = []
    for r in conn.execute("SELECT * FROM negreg_pan WHERE pan=?", (pan,)):
        amt = f"; arrears ₹{r['amount_inr']:,}" if r["amount_inr"] else ""
        hits.append(_hit("negreg_pan", r["source"], "PAN", "high",
                         f"{r['name']} — {r['category']}{amt}", r["is_sample"]))
    # PAN-spine: any blocklisted GSTIN embedding this PAN (chars 3-12) is the
    # same legal entity — deterministic string identity, still a "high" join.
    for r in conn.execute("SELECT * FROM negreg_gstin WHERE substr(gstin,3,10)=?", (pan,)):
        hits.append(_hit("negreg_gstin", r["source"], "PAN embedded in GSTIN", "high",
                         f"GSTIN {r['gstin']} ({r['trade_name']}, {r['state']}) — {r['reason']}",
                         r["is_sample"]))
    return hits


def _check_gstin(conn, gstin: str) -> list[dict]:
    hits = []
    for r in conn.execute("SELECT * FROM negreg_gstin WHERE gstin=?", (gstin,)):
        hits.append(_hit("negreg_gstin", r["source"], "GSTIN", "high",
                         f"{r['trade_name']} ({r['state']}) — {r['reason']}", r["is_sample"]))
    pan = gstin_to_pan(gstin)
    if pan:
        for r in conn.execute("SELECT * FROM negreg_pan WHERE pan=?", (pan,)):
            hits.append(_hit("negreg_pan", r["source"], "PAN (derived from GSTIN chars 3-12)",
                             "high", f"{r['name']} — {r['category']}", r["is_sample"]))
    return hits


def _check_cin(conn, cin: str) -> list[dict]:
    hits = []
    names_to_screen = []
    for r in conn.execute("SELECT * FROM negreg_company_status WHERE cin=?", (cin,)):
        hits.append(_hit("negreg_company_status", r["source"], "CIN", "high",
                         f"{r['name']} — status {r['status']} ({r['roc']})", r["is_sample"]))
        names_to_screen.append(r["name"])
    for r in conn.execute("SELECT * FROM cirp_cases WHERE cin=?", (cin,)):
        hits.append(_hit("cirp_cases", r["source"], "CIN", "high",
                         f"{r['company_name']} — {r['status']} (IBC insolvency)", r["is_sample"]))
        names_to_screen.append(r["company_name"])
    row = conn.execute("SELECT name FROM companies WHERE cin=?", (cin,)).fetchone()
    if row:
        names_to_screen.append(row["name"])
    seen = set()
    for nm in names_to_screen:
        norm = normalize_name(nm)
        if norm and norm not in seen:
            seen.add(norm)
            hits.extend(_check_name(conn, nm, _skip_status_tables=True))
    return hits


def _check_din(conn, din: str) -> list[dict]:
    return [
        _hit("negreg_din", r["source"], "DIN", "high",
             f"{r['name']} — {r['list_type'].replace('_', ' ')}", r["is_sample"])
        for r in conn.execute("SELECT * FROM negreg_din WHERE din=?", (din,))
    ]


def _fuzzy_candidates(conn, norm: str):
    """Cheap pre-filter: name length within ±35% of the query."""
    lo, hi = int(len(norm) * 0.65), int(len(norm) * 1.35) + 1
    return conn.execute(
        "SELECT * FROM negreg_name WHERE length(name_norm) BETWEEN ? AND ?", (lo, hi))


def _check_name(conn, name: str, _skip_status_tables: bool = False) -> list[dict]:
    norm = normalize_name(name)
    if not norm:
        return []
    hits = []
    exact = set()
    for r in conn.execute("SELECT * FROM negreg_name WHERE name_norm=?", (norm,)):
        exact.add(r["name_raw"])
        hits.append(_hit("negreg_name", r["source"], "name (normalized exact)", "advisory",
                         f"'{r['name_raw']}' — {r['list_type'].replace('_', ' ')} [{r['authority']}]",
                         r["is_sample"]))
    sm = SequenceMatcher()
    sm.set_seq2(norm)
    for r in _fuzzy_candidates(conn, norm):
        if r["name_norm"] == norm or r["name_raw"] in exact:
            continue
        sm.set_seq1(r["name_norm"])
        if sm.real_quick_ratio() < FUZZY_THRESHOLD or sm.quick_ratio() < FUZZY_THRESHOLD:
            continue
        ratio = sm.ratio()
        if ratio >= FUZZY_THRESHOLD:
            hits.append(_hit("negreg_name", r["source"], "name (fuzzy)", "advisory",
                             f"'{r['name_raw']}' ~ '{name}' (similarity {ratio:.2f}) — "
                             f"{r['list_type'].replace('_', ' ')} [{r['authority']}]",
                             r["is_sample"]))
    if not _skip_status_tables:
        # normalized-exact against struck-off register names (advisory — name-only)
        for r in conn.execute("SELECT * FROM negreg_company_status"):
            if normalize_name(r["name"]) == norm:
                hits.append(_hit("negreg_company_status", r["source"], "company name (normalized)",
                                 "advisory", f"{r['name']} — status {r['status']} ({r['roc']})",
                                 r["is_sample"]))
    return hits


# ------------------------------------------------------------ public API

def check_identifier(id_type: str, value: str, db_path: str | None = None) -> list[dict]:
    """Screen one identifier against every applicable local registry.

    Types: pan | gstin | cin | din | name | account | vpa.
    account/vpa have no free public registry — production wires the I4C
    Suspect Registry / RBI DPIP bank APIs here; local result is [].
    """
    t = (id_type or "").strip().lower()
    if t not in VALID_TYPES:
        raise ValueError(f"unknown identifier type '{id_type}' (expected one of {VALID_TYPES})")
    if t == "name":
        v = str(value or "").strip()
    else:
        v = re.sub(r"\s+", "", str(value or "")).upper()
    if not v:
        return []
    conn = _connect(db_path)
    try:
        if t == "pan":
            return _check_pan(conn, validate_pan(v)["value"])
        if t == "gstin":
            return _check_gstin(conn, validate_gstin(v)["value"])
        if t == "cin":
            return _check_cin(conn, v)
        if t == "din":
            return _check_din(conn, validate_din(v)["value"])
        if t == "name":
            return _check_name(conn, v)
        return []  # account / vpa — I4C/DPIP bank-gated feeds in production
    finally:
        conn.close()


# profile-dict key -> identifier type
_PROFILE_FIELDS = [
    ("pan", "pan"), ("gstin", "gstin"), ("cin", "cin"), ("din", "din"),
    ("promoter_pan", "pan"), ("promoter_din", "din"),
    ("name", "name"), ("legal_name", "name"), ("promoter_name", "name"),
]


def check_msme(profile: dict, db_path: str | None = None) -> dict:
    """Aggregate screening across every identifier + name on an MSME profile.

    Returns {"checked": True, "inputs": [...], "hits": [...], "clean": bool};
    each hit carries an extra "input_field" telling which profile field fired.
    """
    inputs, hits, seen = [], [], set()
    for field, id_type in _PROFILE_FIELDS:
        value = profile.get(field)
        if not value:
            continue
        inputs.append({"field": field, "type": id_type, "value": str(value)})
        for h in check_identifier(id_type, str(value), db_path=db_path):
            key = (h["registry"], h["matched_on"], h["detail"])
            if key in seen:
                continue
            seen.add(key)
            h["input_field"] = field
            hits.append(h)
    order = {"high": 0, "advisory": 1}
    hits.sort(key=lambda h: order.get(h["confidence"], 2))
    return {"checked": True, "inputs": inputs, "hits": hits, "clean": not hits}


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(check_identifier("cin", "U74999DL2019PTC356789"), indent=2, ensure_ascii=False))
