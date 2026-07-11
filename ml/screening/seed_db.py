"""Build ml/screening/registry.db — negative registries + PAN-spine graph tables.

Strategy (per CONTRACTS.md / BUILD-SPEC pillar 3):
  1. REAL GOVERNMENT DATA (is_sample=0), loaded offline from seeds/real/*.csv
     (captured once from live sources — see SOURCES.md + seeds/real/manifest__*.json):
       - MahaGST Non-Genuine Taxpayers (~11.4k GSTINs) + OpenSanctions GSTINs
       - SEBI/NSE debarred PANs + CBDT arrears defaulters
       - OpenSanctions UAPA/NSE/SEBI/PEP names + RBI Alert List
       - data.gov.in MCA Company Master (Strike-Off CINs)
     Every row is re-validated (structure) and RESERVED-filtered on load.
  2. SYNTHETIC SAMPLES (is_sample=1), deterministic (seed=42), only for the
     graph director universe (no free bulk source) and genuinely-gated feeds
     (MCA disqualified DINs, IBBI CIRP, CIBIL wilful-defaulter names).
  3. THE PERSONA THREAD from seeds/persona_thread.json — exact CONTRACTS.md ids.

Run: python3 seed_db.py          (stdlib only; rebuilds registry.db from CSVs)
"""

from __future__ import annotations

import csv
import json
import os
import random
import sqlite3
import sys
import time

try:
    from .pan import normalize_address, normalize_name, validate_gstin, validate_pan
except ImportError:
    from pan import normalize_address, normalize_name, validate_gstin, validate_pan

HERE = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(HERE, "registry.db")
SEEDS = os.path.join(HERE, "seeds")

# Identifiers reserved by CONTRACTS.md — synthetic rows must NEVER collide.
RESERVED = {
    "ABCPR3456K", "27ABCPR3456K1Z5",                    # RAMESH001 (clean)
    "AKLPM8765D", "27AKLPM8765D1Z3",                    # SURESH002 (clean)
    "AAECN1234F", "07AAECN1234F1Z2", "U51909DL2025PTC412345",  # PHOENIX003 Nexon (clean directly)
    "AEXPM4521C", "08234567",                           # Vikram Malhotra (clean himself)
    "AABCV9876L", "U74999DL2019PTC356789", "07654321",  # Vertex / Rakesh (tainted by design)
    "27AABCT5678Q1Z9", "AABCT5678Q",                    # Trident Textiles (tainted by design)
}

SCHEMA = """
DROP TABLE IF EXISTS negreg_company_status;
DROP TABLE IF EXISTS negreg_gstin;
DROP TABLE IF EXISTS negreg_pan;
DROP TABLE IF EXISTS negreg_din;
DROP TABLE IF EXISTS negreg_name;
DROP TABLE IF EXISTS cirp_cases;
DROP TABLE IF EXISTS companies;
DROP TABLE IF EXISTS directors;
DROP TABLE IF EXISTS directorships;

CREATE TABLE negreg_company_status (cin TEXT, name TEXT, status TEXT, roc TEXT, source TEXT, is_sample INTEGER);
CREATE TABLE negreg_gstin  (gstin TEXT, trade_name TEXT, state TEXT, reason TEXT, source TEXT, is_sample INTEGER);
CREATE TABLE negreg_pan    (pan TEXT, name TEXT, category TEXT, amount_inr INTEGER, source TEXT, is_sample INTEGER);
CREATE TABLE negreg_din    (din TEXT, name TEXT, list_type TEXT, source TEXT, is_sample INTEGER);
CREATE TABLE negreg_name   (name_norm TEXT, name_raw TEXT, list_type TEXT, authority TEXT, source TEXT, is_sample INTEGER);
CREATE TABLE cirp_cases    (cin TEXT, company_name TEXT, status TEXT, source TEXT, is_sample INTEGER);

CREATE TABLE companies     (cin TEXT PRIMARY KEY, name TEXT, pan TEXT, address_norm TEXT, incorporated_on TEXT, status TEXT);
CREATE TABLE directors     (din TEXT PRIMARY KEY, name TEXT, pan TEXT);
CREATE TABLE directorships (din TEXT, cin TEXT, role TEXT, from_date TEXT, to_date TEXT);

CREATE INDEX idx_ncs_cin   ON negreg_company_status(cin);
CREATE INDEX idx_ng_gstin  ON negreg_gstin(gstin);
CREATE INDEX idx_np_pan    ON negreg_pan(pan);
CREATE INDEX idx_nd_din    ON negreg_din(din);
CREATE INDEX idx_nn_norm   ON negreg_name(name_norm);
CREATE INDEX idx_cirp_cin  ON cirp_cases(cin);
CREATE INDEX idx_co_pan    ON companies(pan);
CREATE INDEX idx_co_addr   ON companies(address_norm);
CREATE INDEX idx_ds_din    ON directorships(din);
CREATE INDEX idx_ds_cin    ON directorships(cin);
"""

OUTCOMES: list[dict] = []


def record(source: str, ok: bool, rows: int, note: str) -> None:
    OUTCOMES.append({"source": source, "ok": ok, "rows": rows, "note": note})
    print(f"  [{'REAL' if ok else 'FAIL'}] {source}: {rows} rows — {note}")


# ------------------------------------------------------------ real sources

REAL = os.path.join(SEEDS, "real")   # captured-from-live gov data, one CSV per source


def _read_csv(name: str) -> list[dict]:
    path = os.path.join(REAL, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_real_csvs(conn: sqlite3.Connection) -> None:
    """Load REAL government data (is_sample=0) captured to seeds/real/*.csv.

    Provenance is documented in seeds/real/manifest__*.json and SOURCES.md. The
    build stays fully offline/deterministic (no network) — the live capture was a
    one-time step (headless-browser + TLS-impersonation network inspection), and
    every row is re-validated + RESERVED-filtered here as defense in depth.
    """
    # -- negreg_company_status  (data.gov.in MCA Company Master, real Strike-Off CINs)
    n = 0
    for r in _read_csv("company_status__datagov.csv"):
        cin = (r.get("cin") or "").strip().upper()
        if len(cin) != 21 or cin in RESERVED:
            continue
        conn.execute("INSERT INTO negreg_company_status VALUES (?,?,?,?,?,0)",
                     (cin, (r.get("name") or "").strip(), (r.get("status") or "Strike Off").strip(),
                      (r.get("roc") or "").strip(), "datagovin:mca_company_master"))
        n += 1
    record("real:datagov_company_status", n > 0, n, "MCA Strike-Off CINs across RoCs (data.gov.in OGD)")

    # -- companies graph background (real CINs; no directors in this dataset)
    n = 0
    for r in _read_csv("companies__datagov.csv"):
        cin = (r.get("cin") or "").strip().upper()
        if len(cin) != 21 or cin in RESERVED:
            continue
        conn.execute("INSERT OR IGNORE INTO companies VALUES (?,?,?,?,?,?)",
                     (cin, (r.get("name") or "").strip(), (r.get("pan") or "").strip() or None,
                      normalize_address(r.get("address_norm") or ""),
                      (r.get("incorporated_on") or "")[:10], (r.get("status") or "").strip()))
        n += 1
    record("real:datagov_companies", n > 0, n, "graph background rows (real MCA CINs)")

    # -- negreg_gstin  (MahaGST NGTP ~11.4k + OpenSanctions India-linked GSTINs)
    n = 0
    for src_file, src in (("gstin__mahagst.csv", "mahagst:ngtp"),
                          ("gstin__opensanctions.csv", "opensanctions:india")):
        for r in _read_csv(src_file):
            g = (r.get("gstin") or "").strip().upper()
            if not validate_gstin(g)["valid"] or g in RESERVED:
                continue
            conn.execute("INSERT INTO negreg_gstin VALUES (?,?,?,?,?,0)",
                         (g, (r.get("trade_name") or "").strip(), (r.get("state") or "").strip(),
                          (r.get("reason") or "").strip(), src))
            n += 1
    record("real:gstin", n > 0, n, "MahaGST non-genuine taxpayers + OpenSanctions (real GSTINs)")

    # -- negreg_pan  (CBDT tax defaulters + OpenSanctions/SEBI-NSE real PANs)
    n = 0
    for src_file, src in (("pan__cbdt.csv", "cbdt:tax_defaulters"),
                          ("pan__opensanctions.csv", "opensanctions:india")):
        for r in _read_csv(src_file):
            p = (r.get("pan") or "").strip().upper()
            if not validate_pan(p)["valid"] or p in RESERVED:
                continue
            amt = (r.get("amount_inr") or "").strip()
            conn.execute("INSERT INTO negreg_pan VALUES (?,?,?,?,?,0)",
                         (p, (r.get("name") or "").strip(), (r.get("category") or "").strip(),
                          int(amt) if amt.isdigit() else None, src))
            n += 1
    record("real:pan", n > 0, n, "CBDT arrears defaulters + SEBI/NSE debarred (real PANs)")

    # -- negreg_name  (OpenSanctions watchlists + RBI Alert List)
    n = 0
    for src_file, src in (("names__opensanctions.csv", "opensanctions:india"),
                          ("names__rbi.csv", "rbi:alert_list")):
        for r in _read_csv(src_file):
            raw = (r.get("name_raw") or "").strip()
            norm = normalize_name(raw)
            if not norm:
                continue
            conn.execute("INSERT INTO negreg_name VALUES (?,?,?,?,?,0)",
                         (norm, raw, (r.get("list_type") or "").strip(),
                          (r.get("authority") or "").strip(), src))
            n += 1
    record("real:name", n > 0, n, "OpenSanctions (UAPA/NSE/SEBI/PEP) + RBI Alert List (real names)")


# ------------------------------------------------------------ synthetic universe

FIRST = ["RAJESH", "SUNIL", "AMIT", "PRAKASH", "DEEPAK", "MANOJ", "ANIL", "VIJAY",
         "SANJAY", "ASHOK", "RAVI", "MUKESH", "DINESH", "RAKESH", "SURESH", "NARESH",
         "KAVITA", "SUNITA", "MEENA", "POOJA", "ANITA", "REKHA", "SEEMA", "NEHA"]
LAST = ["SHARMA", "VERMA", "GUPTA", "AGARWAL", "JAIN", "SINGH", "PATEL", "SHAH",
        "MEHTA", "KHANNA", "KAPOOR", "MALHOTRA", "BANSAL", "GOEL", "MITTAL", "ARORA",
        "REDDY", "NAIR", "IYER", "DESAI", "JOSHI", "TRIVEDI", "CHAWLA", "SAXENA"]
CO_A = ["SHREE", "OM", "BALAJI", "GANPATI", "KRISHNA", "SAI", "LAXMI", "AMBEY",
        "SHIVAM", "GLOBAL", "NATIONAL", "SUPREME", "ROYAL", "PARAMOUNT", "EASTERN",
        "WESTERN", "UNITED", "PRIME", "APEX", "STERLING", "ZENITH", "PINNACLE"]
CO_B = ["TRADING", "IMPEX", "EXPORTS", "TEXTILES", "AGRO", "INFRA", "STEELS",
        "POLYMERS", "ELECTRONICS", "LOGISTICS", "VENTURES", "COMMODITIES",
        "ENTERPRISES", "MERCANTILE", "OVERSEAS", "INDUSTRIES", "FOODS", "CHEMICALS"]
STATES = [("DL", "07", "RoC-Delhi", "Delhi"), ("MH", "27", "RoC-Mumbai", "Maharashtra"),
          ("KA", "29", "RoC-Bangalore", "Karnataka"), ("GJ", "24", "RoC-Ahmedabad", "Gujarat"),
          ("TN", "33", "RoC-Chennai", "Tamil Nadu"), ("UP", "09", "RoC-Kanpur", "Uttar Pradesh"),
          ("WB", "19", "RoC-Kolkata", "West Bengal"), ("HR", "06", "RoC-Delhi", "Haryana")]
STREETS = ["MG ROAD", "INDUSTRIAL AREA PHASE 1", "NEHRU PLACE", "ANDHERI EAST",
           "SECTOR 62 NOIDA", "PEENYA INDUSTRIAL AREA", "SALT LAKE SECTOR V",
           "GIDC VATVA", "OKHLA PHASE 2", "GUINDY INDUSTRIAL ESTATE"]

rng = random.Random(42)
_used: set[str] = set(RESERVED)


def _uniq(gen) -> str:
    for _ in range(1000):
        v = gen()
        if v not in _used:
            _used.add(v)
            return v
    raise RuntimeError("id space exhausted")


def synth_person() -> str:
    return f"{rng.choice(FIRST)} {rng.choice(LAST)}"


def synth_company_name() -> str:
    return f"{rng.choice(CO_A)} {rng.choice(CO_B)} PRIVATE LIMITED"


def synth_pan(kind: str) -> str:
    return _uniq(lambda: "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3))
                 + kind + rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ")
                 + f"{rng.randint(0, 9999):04d}" + rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"))


def synth_cin(state: str, year: int) -> str:
    return _uniq(lambda: f"U{rng.randint(1000, 99999):05d}{state}{year}PTC{rng.randint(1, 999999):06d}")


def synth_din() -> str:
    return _uniq(lambda: f"{rng.randint(100000, 10999999):08d}")


def synth_gstin(state_code: str, pan: str) -> str:
    return _uniq(lambda: f"{state_code}{pan}{rng.randint(1, 9)}Z{rng.choice('0123456789ABCDEFGHJKLMNPQRSTUVWXYZ')}")


def seed_synthetic(conn: sqlite3.Connection) -> None:
    """is_sample=1 rows mirroring the real schemas, deterministic (seed 42)."""

    # -- graph universe: companies with directors/directorships (real sources
    #    give no director data), some of them tainted, so arbitrary PAN walks work
    n_struck_linked = 0
    for i in range(60):
        st, gst_code, roc, _ = rng.choice(STATES)
        year = rng.randint(2008, 2024)
        cin = synth_cin(st, year)
        name = synth_company_name()
        pan = synth_pan("C")
        addr = f"{rng.randint(1, 400)} {rng.choice(STREETS)} {rng.randint(110001, 700100)}"
        struck = rng.random() < 0.35
        status = "Strike Off" if struck else "Active"
        conn.execute("INSERT OR IGNORE INTO companies VALUES (?,?,?,?,?,?)",
                     (cin, name, pan, addr, f"{year}-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}", status))
        dins = []
        for _ in range(rng.randint(1, 3)):
            din, dname, dpan = synth_din(), synth_person(), synth_pan("P")
            conn.execute("INSERT OR IGNORE INTO directors VALUES (?,?,?)", (din, dname, dpan))
            conn.execute("INSERT INTO directorships VALUES (?,?,?,?,?)",
                         (din, cin, "Director", f"{year}-06-01", None if not struck else f"{year+rng.randint(2,6)}-03-31"))
            dins.append((din, dname))
        if struck:
            n_struck_linked += 1
            conn.execute("INSERT INTO negreg_company_status VALUES (?,?,?,?,?,1)",
                         (cin, name, "Strike Off", roc, "sample:mca_company_master"))
            if rng.random() < 0.5:
                din, dname = rng.choice(dins)
                conn.execute("INSERT INTO negreg_din VALUES (?,?,?,?,1)",
                             (din, dname, "director_of_struck_off", "sample:mca_directors_struckoff"))

    # NOTE: struck-off companies, non-genuine GSTINs, CBDT PAN defaulters and the
    # RBI Alert List are now loaded as REAL data in load_real_csvs() (is_sample=0);
    # their synthetic mirrors were removed. Only genuinely-gated feeds stay sample.

    # -- DIN blocklist (~100, is_sample=1): MCA disqualified/struck-off director lists
    #    are gated (per-RoC portal forms / throttled DMS docs) — no clean free bulk.
    have = conn.execute("SELECT COUNT(*) FROM negreg_din").fetchone()[0]
    for _ in range(max(0, 100 - have)):
        conn.execute("INSERT INTO negreg_din VALUES (?,?,?,?,1)",
                     (synth_din(), synth_person(),
                      rng.choice(["director_of_struck_off", "disqualified_164_2"]),
                      "sample:mca_directors_struckoff"))

    # -- wilful-defaulter names (~60, is_sample=1): CIBIL suit-filed list is
    #    captcha-gated with no bulk export (the phoenix demo row comes from the
    #    persona thread; these give the list_type breadth).
    for _ in range(60):
        raw = synth_company_name() if rng.random() < 0.7 else synth_person()
        conn.execute("INSERT INTO negreg_name VALUES (?,?,?,?,?,1)",
                     (normalize_name(raw), raw.title(), "wilful_defaulter",
                      "TransUnion CIBIL suit-filed wilful defaulters (bank-reported)",
                      "sample:cibil_wilful_defaulters"))

    # -- ~100 CIRP cases (is_sample=1): IBBI exposes only per-CIN document search,
    #    no free bulk corporate-debtor list (browser-confirmed).
    for _ in range(100):
        st, _, _, _ = rng.choice(STATES)
        conn.execute("INSERT INTO cirp_cases VALUES (?,?,?,?,1)",
                     (synth_cin(st, rng.randint(2000, 2020)), synth_company_name(),
                      rng.choice(["CIRP ongoing", "Resolution plan approved",
                                  "Liquidation ordered", "Withdrawn u/s 12A"]),
                      "sample:ibbi_cirp"))

    record("synthetic:universe", True, 0,
           f"graph universe 60 cos ({n_struck_linked} struck-off w/ directors) + "
           "gated DIN/wilful/CIRP samples, all is_sample=1, seed=42")


def seed_personas(conn: sqlite3.Connection) -> None:
    """Exact CONTRACTS.md demo thread — inserted LAST so nothing can shadow it."""
    with open(os.path.join(SEEDS, "persona_thread.json")) as f:
        t = json.load(f)
    for c in t["companies"]:
        conn.execute("INSERT OR REPLACE INTO companies VALUES (?,?,?,?,?,?)",
                     (c["cin"], c["name"], c["pan"], c["address_norm"],
                      c["incorporated_on"], c["status"]))
    for d in t["directors"]:
        conn.execute("INSERT OR REPLACE INTO directors VALUES (?,?,?)",
                     (d["din"], d["name"], d["pan"]))
    for ds in t["directorships"]:
        conn.execute("INSERT INTO directorships VALUES (?,?,?,?,?)",
                     (ds["din"], ds["cin"], ds["role"], ds["from_date"], ds["to_date"]))
    for r in t["negreg_company_status"]:
        conn.execute("INSERT INTO negreg_company_status VALUES (?,?,?,?,?,?)",
                     (r["cin"], r["name"], r["status"], r["roc"], r["source"], r["is_sample"]))
    for r in t["negreg_name"]:
        conn.execute("INSERT INTO negreg_name VALUES (?,?,?,?,?,?)",
                     (r["name_norm"], r["name_raw"], r["list_type"], r["authority"],
                      r["source"], r["is_sample"]))
    for r in t["negreg_din"]:
        conn.execute("INSERT INTO negreg_din VALUES (?,?,?,?,?)",
                     (r["din"], r["name"], r["list_type"], r["source"], r["is_sample"]))
    for r in t["negreg_gstin"]:
        conn.execute("INSERT INTO negreg_gstin VALUES (?,?,?,?,?,?)",
                     (r["gstin"], r["trade_name"], r["state"], r["reason"],
                      r["source"], r["is_sample"]))
    record("persona:demo_thread", True, sum(len(v) for k, v in t.items() if isinstance(v, list)),
           "Vertex/Nexon/Vikram/Rakesh/Trident — exact CONTRACTS.md ids")


def assert_personas(conn: sqlite3.Connection) -> None:
    """Hard invariants — fail the build if the demo thread is broken."""
    q = lambda sql, *a: conn.execute(sql, a).fetchone()
    assert q("SELECT 1 FROM negreg_company_status WHERE cin='U74999DL2019PTC356789'"), "Vertex CIN missing from negreg"
    assert q("SELECT 1 FROM negreg_name WHERE name_norm='VERTEX IMPEX' AND list_type='wilful_defaulter'"), "Vertex wilful-defaulter name missing"
    assert q("SELECT 1 FROM negreg_din WHERE din='07654321'"), "Rakesh DIN missing"
    assert q("SELECT 1 FROM negreg_gstin WHERE gstin='27AABCT5678Q1Z9'"), "Trident GSTIN missing"
    a1 = q("SELECT address_norm FROM companies WHERE cin='U74999DL2019PTC356789'")
    a2 = q("SELECT address_norm FROM companies WHERE cin='U51909DL2025PTC412345'")
    assert a1 and a2 and a1[0] == a2[0] == "14 KAROL BAGH INDUSTRIAL AREA DELHI 110005", "shared address broken"
    assert q("SELECT COUNT(*) FROM directorships WHERE cin='U74999DL2019PTC356789'")[0] == 2, "Vertex needs 2 directorships"
    # clean-by-contract identifiers must have ZERO direct rows anywhere
    for pan in ("ABCPR3456K", "AKLPM8765D", "AAECN1234F", "AEXPM4521C"):
        assert not q("SELECT 1 FROM negreg_pan WHERE pan=?", pan), f"{pan} must be clean"
    for g in ("27ABCPR3456K1Z5", "27AKLPM8765D1Z3", "07AAECN1234F1Z2"):
        assert not q("SELECT 1 FROM negreg_gstin WHERE gstin=?", g), f"{g} must be clean"
    assert not q("SELECT 1 FROM negreg_din WHERE din='08234567'"), "Vikram DIN must be clean"
    assert not q("SELECT 1 FROM negreg_company_status WHERE cin='U51909DL2025PTC412345'"), "Nexon CIN must be clean"
    print("  persona invariants: ALL OK")


def main() -> int:
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(SCHEMA)

    print("== real government data (is_sample=0, captured to seeds/real/) ==")
    load_real_csvs(conn)

    print("== synthetic samples (is_sample=1, deterministic) — graph spine + gated feeds ==")
    seed_synthetic(conn)

    print("== persona thread ==")
    seed_personas(conn)
    conn.commit()
    assert_personas(conn)

    print("== row counts ==")
    for t in ("negreg_company_status", "negreg_gstin", "negreg_pan", "negreg_din",
              "negreg_name", "cirp_cases", "companies", "directors", "directorships"):
        total, real = conn.execute(
            f"SELECT COUNT(*), COALESCE(SUM(CASE WHEN is_sample=0 THEN 1 ELSE 0 END),'-') "
            f"FROM {t}" if t.startswith(("negreg", "cirp")) else
            f"SELECT COUNT(*), '-' FROM {t}").fetchone()
        print(f"  {t:24s} {total:6d} rows (real: {real})")

    with open(os.path.join(SEEDS, "seed_report.json"), "w") as f:
        json.dump({"built_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "outcomes": OUTCOMES}, f, indent=2)
    conn.close()
    print(f"registry.db written → {DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
