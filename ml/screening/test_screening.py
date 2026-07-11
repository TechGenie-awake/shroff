"""Verification suite for the screening module — stdlib only, no fastapi.

Run: python3 test_screening.py   (after python3 seed_db.py)

Covers the CONTRACTS.md demo thread end-to-end:
  (a) Vertex CIN            -> high-confidence struck-off hit
  (b) Trident GSTIN         -> non-genuine hit (SURESH002's distressed buyer)
  (c) RAMESH001 / SURESH002 own identifiers -> CLEAN
  (d) build_graph(AAECN1234F) -> phoenix_flag true with the tainted path
  (e) build_graph(ABCPR3456K) -> clean/minimal graph
plus fuzzy-name advisory matching, check_msme aggregation, and contract-shape
checks on every payload.
"""

import json
import sys

from graph import TAINT_FLAGS, build_graph
from registry import check_identifier, check_msme

FAIL = 0


def check(label, cond, extra=""):
    global FAIL
    if not cond:
        FAIL += 1
    print(f"[{'ok' if cond else 'FAIL'}] {label}{(' — ' + extra) if extra else ''}")


HIT_KEYS = {"registry", "list_name", "matched_on", "confidence", "detail", "source_url", "is_sample"}


def assert_hit_shape(hits):
    return all(HIT_KEYS <= set(h) and h["confidence"] in ("high", "advisory") for h in hits)


print("== (a) Vertex CIN — the struck-off shell ==")
hits = check_identifier("cin", "U74999DL2019PTC356789")
print(json.dumps(hits, indent=2, ensure_ascii=False))
check("Vertex CIN returns hits", len(hits) >= 1)
check("hit shape matches /api/screen contract", assert_hit_shape(hits))
check("high-confidence CIN join on struck-off register",
      any(h["registry"] == "negreg_company_status" and h["confidence"] == "high"
          and h["matched_on"] == "CIN" for h in hits))
check("wilful-defaulter name advisory also surfaces",
      any(h["registry"] == "negreg_name" and h["confidence"] == "advisory" for h in hits))

print("\n== (b) Trident Textiles GSTIN — SURESH002's distressed buyer ==")
hits = check_identifier("gstin", "27AABCT5678Q1Z9")
print(json.dumps(hits, indent=2, ensure_ascii=False))
check("Trident GSTIN hits", len(hits) >= 1)
check("high-confidence GSTIN join on non-genuine list",
      any(h["registry"] == "negreg_gstin" and h["confidence"] == "high"
          and h["matched_on"] == "GSTIN" for h in hits))
check("is_sample chip honest (synthetic mirror)", all(h["is_sample"] for h in hits))

print("\n== (c) persona OWN identifiers must be CLEAN ==")
clean_checks = [
    ("pan", "ABCPR3456K", "RAMESH001 PAN"),
    ("gstin", "27ABCPR3456K1Z5", "RAMESH001 GSTIN"),
    ("pan", "AKLPM8765D", "SURESH002 PAN"),
    ("gstin", "27AKLPM8765D1Z3", "SURESH002 GSTIN"),
    ("pan", "AAECN1234F", "PHOENIX003 Nexon company PAN"),
    ("gstin", "07AAECN1234F1Z2", "PHOENIX003 Nexon GSTIN"),
    ("cin", "U51909DL2025PTC412345", "PHOENIX003 Nexon CIN"),
    ("pan", "AEXPM4521C", "Vikram Malhotra PAN (clean himself)"),
    ("din", "08234567", "Vikram Malhotra DIN (clean himself)"),
]
for t, v, label in clean_checks:
    h = check_identifier(t, v)
    check(f"{label} [{t} {v}] clean", h == [], f"got {len(h)} hits" if h else "")

print("\n== direct-hit sanity: Rakesh DIN + advisory fuzzy name ==")
hits = check_identifier("din", "07654321")
check("Rakesh DIN 07654321 flagged director_of_struck_off",
      any("director of struck off" in h["detail"] and h["confidence"] == "high" for h in hits))
hits = check_identifier("name", "Vertexx Impex Private Limited")  # typo'd on purpose
check("fuzzy name match (>=0.92) is advisory",
      any(h["matched_on"] == "name (fuzzy)" and h["confidence"] == "advisory" for h in hits),
      f"{len(hits)} hits")
hits = check_identifier("name", "Vertex Impex Pvt Ltd")
check("normalized-exact name match is advisory",
      any(h["matched_on"] == "name (normalized exact)" for h in hits))
check("account/vpa types return [] (I4C is bank-gated in production)",
      check_identifier("vpa", "someone@upi") == [] and check_identifier("account", "1234567890") == [])

print("\n== check_msme aggregation ==")
suresh = check_msme({
    "pan": "AKLPM8765D", "gstin": "27AKLPM8765D1Z3",
    "name": "Suresh Trading Co.", "promoter_name": "Suresh Mehta",
})
check("SURESH002 profile itself clean (his RISK is counterparty+cashflow)",
      suresh["clean"], json.dumps(suresh["hits"])[:200])
phoenix_profile = check_msme({
    "pan": "AAECN1234F", "gstin": "07AAECN1234F1Z2", "cin": "U51909DL2025PTC412345",
    "name": "Nexon Trading Pvt Ltd", "promoter_pan": "AEXPM4521C",
    "promoter_din": "08234567", "promoter_name": "Vikram Malhotra",
})
check("PHOENIX003 profile clean on DIRECT screening (that's the point — graph catches it)",
      phoenix_profile["clean"])
vertex_msme = check_msme({"cin": "U74999DL2019PTC356789", "name": "Vertex Impex Pvt Ltd"})
check("Vertex-as-applicant aggregates high hit first",
      not vertex_msme["clean"] and vertex_msme["hits"][0]["confidence"] == "high")

print("\n== (d) build_graph AAECN1234F — the phoenix walk ==")
g = build_graph("AAECN1234F")
node_ids = {n["id"] for n in g["nodes"]}
flags = {n["id"]: n["flag"] for n in g["nodes"]}
check("phoenix_flag is TRUE", g["phoenix_flag"] is True)
check("payload shape", set(g) == {"nodes", "edges", "phoenix_flag", "narrative"})
check("node shape", all(set(n) == {"id", "type", "label", "flag"} for n in g["nodes"]))
check("edge shape", all(set(e) == {"source", "target", "relation"} for e in g["edges"]))
check("Nexon company node present", "cin:U51909DL2025PTC412345" in node_ids)
check("Vikram DIN node present and CLEAN",
      "din:08234567" in node_ids and flags["din:08234567"] is None)
check("Vertex node present and tainted",
      flags.get("cin:U74999DL2019PTC356789") in TAINT_FLAGS)
check("Rakesh DIN tainted director_of_struck_off",
      flags.get("din:07654321") == "director_of_struck_off")
check("shared-address node present",
      "addr:14 KAROL BAGH INDUSTRIAL AREA DELHI 110005" in node_ids)
check("walk edge Vikram->Vertex exists",
      any(e["source"] == "din:08234567" and e["target"] == "cin:U74999DL2019PTC356789"
          for e in g["edges"]))
check("narrative mentions struck-off + shared address + refer",
      "Struck Off" in g["narrative"] and "KAROL BAGH" in g["narrative"]
      and "manual review" in g["narrative"])
print("narrative:", g["narrative"][:400], "...")

print("\n== (e) build_graph ABCPR3456K — clean minimal graph ==")
g = build_graph("ABCPR3456K")
print(json.dumps(g, indent=2, ensure_ascii=False))
check("phoenix_flag false", g["phoenix_flag"] is False)
check("no flagged nodes", all(n["flag"] is None for n in g["nodes"]))
check("minimal (PAN node only — proprietorship, no CIN/DIN)",
      len(g["nodes"]) == 1 and g["nodes"][0]["id"] == "pan:ABCPR3456K")
check("narrative says clean", "Clean" in g["narrative"] or "No negative-registry" in g["narrative"])

print("\n== bonus: graph on a random synthetic struck-off promoter stays coherent ==")
import sqlite3, os
conn = sqlite3.connect(os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.db"))
row = conn.execute(
    "SELECT d.pan FROM directors d JOIN directorships ds ON ds.din=d.din "
    "JOIN negreg_company_status n ON n.cin=ds.cin WHERE n.is_sample=1 AND d.pan IS NOT NULL "
    "AND d.din NOT IN ('08234567','07654321') LIMIT 1").fetchone()
conn.close()
if row:
    g2 = build_graph(row[0])
    check(f"synthetic promoter {row[0]} of a struck-off co produces a flagged graph",
          len(g2["nodes"]) >= 3 and g2["phoenix_flag"],
          f"{len(g2['nodes'])} nodes, phoenix={g2['phoenix_flag']}")
else:
    check("synthetic promoter lookup", False, "no synthetic struck-off director found")

print(f"\n{'ALL SCREENING TESTS PASSED' if FAIL == 0 else str(FAIL) + ' FAILURES'}")
sys.exit(0 if FAIL == 0 else 1)
