"""PAN-spine entity graph — the phoenix-fraud detector.

build_graph(pan) implements the CONTRACTS.md walk:
  pan -> company/gstin(s) -> CIN -> directorships -> directors ->
  co-directors -> their other companies (2 hops) + shared-address edges,
cross-checking every node against the negative registries, and returns the
exact /api/graph payload:
  {"nodes":[{id,type,label,flag}], "edges":[{source,target,relation}],
   "phoenix_flag": bool, "narrative": "one paragraph"}

phoenix_flag is true iff a promoter/co-director path (any node beyond the
applicant's own PAN + own companies) reaches a struck-off, wilful-defaulter
or director-of-struck-off node. Stdlib only.
"""

from __future__ import annotations

import os
import sqlite3

try:
    from .pan import normalize_name, validate_pan
except ImportError:
    from pan import normalize_name, validate_pan

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "registry.db")

MAX_NODES = 80
TAINT_FLAGS = {"struck_off", "wilful_defaulter", "director_of_struck_off"}
_FLAG_PRIORITY = ["wilful_defaulter", "struck_off", "director_of_struck_off", "non_genuine"]


def _worst(flags: list[str]) -> str | None:
    for f in _FLAG_PRIORITY:
        if f in flags:
            return f
    return None


def _connect(db_path: str | None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------------------------- per-node registry checks

def _flag_company(conn, cin: str, name: str, status: str | None):
    flags, reasons = [], []
    for r in conn.execute("SELECT status, roc FROM negreg_company_status WHERE cin=?", (cin,)):
        flags.append("struck_off")
        reasons.append(f"status '{r['status']}' on the MCA struck-off register ({r['roc']})")
    if not flags and status and "STR" in status.upper():  # Struck Off / Strike Off in companies table
        flags.append("struck_off")
        reasons.append(f"company status '{status}' in the company master")
    norm = normalize_name(name or "")
    if norm:
        for r in conn.execute(
                "SELECT name_raw, list_type, authority FROM negreg_name WHERE name_norm=?", (norm,)):
            if r["list_type"] == "wilful_defaulter":
                flags.append("wilful_defaulter")
                reasons.append(f"name matches wilful-defaulter list entry '{r['name_raw']}' [{r['authority']}]")
    for r in conn.execute("SELECT status FROM cirp_cases WHERE cin=?", (cin,)):
        reasons.append(f"under IBC insolvency: {r['status']}")  # narrative-only (no contract flag enum)
    return _worst(flags), reasons


def _flag_din(conn, din: str):
    flags, reasons = [], []
    for r in conn.execute("SELECT name, list_type FROM negreg_din WHERE din=?", (din,)):
        flags.append("director_of_struck_off")
        reasons.append(f"DIN on the {r['list_type'].replace('_', '-')} list")
    return _worst(flags), reasons


def _flag_pan(conn, pan: str):
    flags, reasons = [], []
    for r in conn.execute("SELECT name, category FROM negreg_pan WHERE pan=?", (pan,)):
        flags.append("wilful_defaulter")
        reasons.append(f"PAN on negative registry: {r['category']} ({r['name']})")
    return _worst(flags), reasons


# -------------------------------------------------- graph builder

def build_graph(pan: str, db_path: str | None = None) -> dict:
    pan = validate_pan(pan)["value"]
    pan_info = validate_pan(pan)
    conn = _connect(db_path)
    try:
        return _build(conn, pan, pan_info)
    finally:
        conn.close()


def _build(conn, pan: str, pan_info: dict) -> dict:
    nodes: dict[str, dict] = {}
    hops: dict[str, int] = {}
    reasons: dict[str, list] = {}
    edges: list[dict] = []
    edge_seen: set[tuple] = set()

    def add_node(nid, ntype, label, flag, hop, why):
        if nid in nodes:
            if flag and not nodes[nid]["flag"]:
                nodes[nid]["flag"] = flag
            hops[nid] = min(hops[nid], hop)
            return False
        nodes[nid] = {"id": nid, "type": ntype, "label": label, "flag": flag}
        hops[nid] = hop
        reasons[nid] = why or []
        return True

    def add_edge(src, dst, relation):
        key = (src, dst, relation)
        if key not in edge_seen and src in nodes and dst in nodes:
            edge_seen.add(key)
            edges.append({"source": src, "target": dst, "relation": relation})

    # root PAN node — label with owner name if the spine knows it
    owner = conn.execute("SELECT name FROM directors WHERE pan=?", (pan,)).fetchone()
    if not owner:
        owner = conn.execute("SELECT name FROM companies WHERE pan=?", (pan,)).fetchone()
    root_id = f"pan:{pan}"
    root_label = f"{pan}" + (f" · {owner['name']}" if owner else "")
    pflag, pwhy = _flag_pan(conn, pan)
    add_node(root_id, "pan", root_label, pflag, 0, pwhy)

    # blocklisted GSTIN registrations embedding this PAN (chars 3-12)
    for r in conn.execute("SELECT * FROM negreg_gstin WHERE substr(gstin,3,10)=?", (pan,)):
        gid = f"gstin:{r['gstin']}"
        add_node(gid, "gstin", f"{r['gstin']} · {r['trade_name']}", "non_genuine", 0,
                 [f"on '{r['state']}' non-genuine GSTIN list: {r['reason']}"])
        add_edge(root_id, gid, "gstin_of")

    # BFS: company at hop<=2 expands directors + co-located companies;
    # din at hop<=1 expands its other companies. (pan -> co h0 -> din h1 ->
    # co h2 -> din h3 = co-directors, no further — the "2 hops" walk.)
    queue: list[tuple] = []
    for r in conn.execute("SELECT * FROM companies WHERE pan=? ORDER BY cin", (pan,)):
        cid = f"cin:{r['cin']}"
        flag, why = _flag_company(conn, r["cin"], r["name"], r["status"])
        add_node(cid, "company", f"{r['name']} · {r['cin']}", flag, 0, why)
        add_edge(root_id, cid, "pan_of")
        queue.append(("company", r["cin"], 0))
    # individual PAN -> their DIN (one-per-person-for-life) -> directorships
    for r in conn.execute("SELECT * FROM directors WHERE pan=? ORDER BY din", (pan,)):
        did = f"din:{r['din']}"
        flag, why = _flag_din(conn, r["din"])
        add_node(did, "din", f"{r['name']} · DIN {r['din']}", flag, 0, why)
        add_edge(root_id, did, "din_of")
        queue.append(("din", r["din"], 0))

    qi = 0
    while qi < len(queue) and len(nodes) < MAX_NODES:
        ntype, key, hop = queue[qi]
        qi += 1
        if ntype == "company" and hop <= 2:
            cid = f"cin:{key}"
            # directors / co-directors
            for r in conn.execute(
                    "SELECT d.din, d.name, ds.role FROM directorships ds "
                    "JOIN directors d ON d.din = ds.din WHERE ds.cin=? ORDER BY d.din", (key,)):
                did = f"din:{r['din']}"
                flag, why = _flag_din(conn, r["din"])
                if add_node(did, "din", f"{r['name']} · DIN {r['din']}", flag, hop + 1, why):
                    queue.append(("din", r["din"], hop + 1))
                add_edge(did, cid, "director_of")
            # co-located companies (shared registered address)
            addr = conn.execute("SELECT address_norm FROM companies WHERE cin=?", (key,)).fetchone()
            if addr and addr["address_norm"] and len(addr["address_norm"]) > 8:
                for r in conn.execute(
                        "SELECT * FROM companies WHERE address_norm=? AND cin<>? ORDER BY cin LIMIT 6",
                        (addr["address_norm"], key)):
                    ocid = f"cin:{r['cin']}"
                    flag, why = _flag_company(conn, r["cin"], r["name"], r["status"])
                    if add_node(ocid, "company", f"{r['name']} · {r['cin']}", flag, hop + 1, why):
                        queue.append(("company", r["cin"], hop + 1))
        elif ntype == "din" and hop <= 1:
            did = f"din:{key}"
            for r in conn.execute(
                    "SELECT c.* FROM directorships ds JOIN companies c ON c.cin = ds.cin "
                    "WHERE ds.din=? ORDER BY c.cin", (key,)):
                cid = f"cin:{r['cin']}"
                flag, why = _flag_company(conn, r["cin"], r["name"], r["status"])
                if add_node(cid, "company", f"{r['name']} · {r['cin']}", flag, hop + 1, why):
                    queue.append(("company", r["cin"], hop + 1))
                add_edge(did, cid, "director_of")

    # shared-address nodes (only where >=2 graph companies actually share one)
    addr_groups: dict[str, list[str]] = {}
    for nid, n in list(nodes.items()):
        if n["type"] != "company":
            continue
        row = conn.execute("SELECT address_norm FROM companies WHERE cin=?", (nid[4:],)).fetchone()
        if row and row["address_norm"] and len(row["address_norm"]) > 8:
            addr_groups.setdefault(row["address_norm"], []).append(nid)
    shared_addresses = []
    for addr, members in sorted(addr_groups.items()):
        if len(members) >= 2:
            aid = f"addr:{addr}"
            add_node(aid, "address", addr, None, min(hops[m] for m in members) + 1, [])
            for m in members:
                add_edge(m, aid, "registered_at")
            shared_addresses.append((addr, members))

    # phoenix: tainted node reached beyond the applicant's own pan/companies
    phoenix = any(
        n["flag"] in TAINT_FLAGS and hops[nid] >= 1
        for nid, n in nodes.items()
    )

    narrative = _narrative(conn, pan, pan_info, nodes, hops, reasons, edges,
                           shared_addresses, phoenix)
    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "phoenix_flag": phoenix,
        "narrative": narrative,
    }


# -------------------------------------------------- narrative

def _age_phrase(incorporated_on: str | None) -> str:
    if not incorporated_on or len(incorporated_on) < 7:
        return ""
    try:
        y, m = int(incorporated_on[:4]), int(incorporated_on[5:7])
        months = (2026 - y) * 12 + (7 - m)  # vs demo epoch 2026-07
        if 0 <= months <= 240:
            return f", incorporated {incorporated_on[:7]} (~{months} months old)"
    except ValueError:
        pass
    return ""


def _narrative(conn, pan, pan_info, nodes, hops, reasons, edges,
               shared_addresses, phoenix) -> str:
    own_cos = [n for nid, n in nodes.items() if n["type"] == "company" and hops[nid] == 0]
    parts = []

    if own_cos:
        descs = []
        for n in own_cos:
            cin = n["id"][4:]
            row = conn.execute("SELECT incorporated_on FROM companies WHERE cin=?", (cin,)).fetchone()
            nm = n["label"].split(" · ")[0]
            descs.append(f"{nm} (CIN {cin}{_age_phrase(row['incorporated_on'] if row else None)})")
        parts.append(f"PAN {pan} resolves to {'; '.join(descs)}.")
    else:
        et = pan_info.get("entity_type") or "unknown entity type"
        parts.append(f"PAN {pan} ({et}) has no company or GSTIN linkage on the local spine.")

    direct = [n for nid, n in nodes.items() if n["flag"] and hops[nid] == 0]
    for n in direct:
        why = "; ".join(reasons.get(n["id"], [])) or n["flag"].replace("_", " ")
        parts.append(f"DIRECT HIT — {n['label']}: {why}.")

    if phoenix:
        tainted = sorted(
            (n for nid, n in nodes.items() if n["flag"] in TAINT_FLAGS and hops[nid] >= 1),
            key=lambda n: hops[n["id"]])
        for n in tainted:
            why = "; ".join(reasons.get(n["id"], [])) or n["flag"].replace("_", " ")
            if n["type"] == "company":
                # who connects us to this tainted company?
                linkers = [nodes[e["source"]]["label"] for e in edges
                           if e["target"] == n["id"] and e["relation"] == "director_of"
                           and nodes[e["source"]]["type"] == "din"]
                via = f" via director {', '.join(sorted(set(linkers)))}" if linkers else ""
                parts.append(f"The promoter network reaches {n['label']}{via}: {why}.")
            elif n["type"] == "din":
                parts.append(f"Co-director {n['label']} is flagged: {why}.")
        for addr, members in shared_addresses:
            names = [nodes[m]["label"].split(" · ")[0] for m in members]
            parts.append(f"{' and '.join(names)} share the registered address {addr}.")
        parts.append("Phoenix pattern: the applicant is clean on direct checks, but its "
                      "promoter/co-director path reaches struck-off or wilful-defaulter "
                      "entities — refer to manual review.")
    elif not direct:
        parts.append("No negative-registry hits were found on the applicant or within two "
                      "hops of its promoter network. Clean on the PAN spine.")

    return " ".join(parts)


if __name__ == "__main__":
    import json as _json
    print(_json.dumps(build_graph("AAECN1234F"), indent=2, ensure_ascii=False))
