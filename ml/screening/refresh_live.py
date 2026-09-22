"""On-demand LIVE refresh for the negative-registry seed CSVs.

Honesty context (see SOURCES.md): the original ~45k real rows were a ONE-TIME capture,
loaded offline so the demo has zero network dependency. This module is the answer to
"is the scraping actually live" — it genuinely re-fetches from the real sources, right
now, over the network, when you run it. It is still NOT scheduled/continuous (that needs
cloud infra — EventBridge/Step Functions per docs/INFRA-AWS.md §3.3) — this is "live" in
the sense of "run this command and it hits the real internet," not "runs by itself."

Fetches via `curl` (stdlib `subprocess`), not `urllib`/`requests` — deliberate: some
execution sandboxes intercept outbound TLS with a proxy cert that Python's default SSL
context won't trust but the OS trust store (which curl uses) does. curl is also what a
real Lambda/Fargate deployment would use just as validly, so this isn't a workaround
specific to any one environment.

Covered here (the sources with no bot-protection, safe to automate today):
  - RBI Alert List (unauthorised forex/ETP platforms) — static HTML table
  - OpenSanctions India name lists (NSE debarred, UAPA, PEP, SEBI) — public bulk CSV

Deliberately NOT covered here (documented, not silently skipped):
  - MahaGST NGTP — the XLSX link embeds the "as on" date and changes each publish;
    needs link-discovery + openpyxl, not yet built.
  - CBDT defaulters — Akamai actively blocks plain HTTP clients; the original capture
    used curl_cffi Chrome TLS-fingerprint impersonation. Not attempted here.
  - data.gov.in MCA — reachable, but the free sample key clamps to 10 rows/request;
    a registered key removes the clamp (see docs/INFRA-AWS.md fix-list). Not wired here
    because the ROI (900 -> 129,694 rows) needs that registration first, not more code.

Output lands in seeds/live/, NOT seeds/real/ — this never silently overwrites the
seed files seed_db.py loads for the running demo. Review the diff, then copy into
seeds/real/ and re-run `python3 seed_db.py` yourself when you're ready.
"""
from __future__ import annotations

import csv
import html
import json
import os
import re
import subprocess
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
REAL = os.path.join(HERE, "seeds", "real")
LIVE = os.path.join(HERE, "seeds", "live")

RBI_URL = "https://www.rbi.org.in/scripts/bs_viewcontent.aspx?Id=4235"

OPENSANCTIONS_DATASETS = [
    # Slugs verified against seeds/real/manifest__opensanctions.json — not guessed.
    ("in_nse_debarred", "nse_debarred", "India National Stock Exchange Debarred Entities"),
    ("in_mha_banned", "uapa_banned", "India UAPA Designated Terrorists/Organisations"),
    ("in_sansad", "pep", "India Lok and Rajya Sabha Members"),
    # "intl_sanction" (list_type) is NOT a per-country dataset slug — it's the 66.5MB
    # consolidated `sanctions.simple.csv` collection filtered client-side to rows whose
    # countries column contains "in". That's a heavier, different fetch shape and isn't
    # rebuilt here — documented as remaining manual, same honesty as MahaGST/CBDT below.
]


def _curl(url: str) -> str:
    """Fetch a URL via curl (system trust store), raise on failure. No retries —
    a failed source should be visible, not silently swallowed."""
    r = subprocess.run(
        ["curl", "-sSL", "--max-time", "25", "-A", "Mozilla/5.0 (SHROFF live-refresh)", url],
        capture_output=True, text=True, timeout=30,
    )
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"curl failed for {url}: rc={r.returncode} stderr={r.stderr[:300]}")
    return r.stdout


def fetch_rbi_alert_list() -> list[dict]:
    """Static HTML table, class='tablebg', columns: #, entity name, website."""
    body = _curl(RBI_URL)
    m = re.search(r"<table[^>]*class=[\"']?tablebg[\"']?.*?</table>", body, re.S | re.I)
    if not m:
        raise RuntimeError("RBI page structure changed — 'tablebg' table not found")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S | re.I)
    out = []
    for row in rows:
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S | re.I)
        if len(cells) < 2:
            continue
        name = html.unescape(re.sub(r"<[^>]+>", "", cells[1])).strip()
        if not name or not name[0].isalpha():
            continue  # skip header / stray rows
        out.append({
            "name_raw": name,
            "list_type": "rbi_alert_list",
            "authority": "RBI Alert List — unauthorised forex/ETP platforms",
        })
    return out


def fetch_opensanctions_names(slug: str, list_type: str, authority: str) -> list[dict]:
    """Public bulk simple-CSV export. We take the `name` column only here — PAN/GSTIN
    extraction from the `identifiers` column is a separate, fragile parser not rebuilt
    in this pass (documented above, not silently attempted)."""
    url = f"https://data.opensanctions.org/datasets/latest/{slug}/targets.simple.csv"
    body = _curl(url)
    reader = csv.DictReader(body.splitlines())
    out = []
    for r in reader:
        name = (r.get("name") or "").strip()
        if not name:
            continue
        out.append({"name_raw": name, "list_type": list_type, "authority": authority})
    return out


def _write_csv(path: str, rows: list[dict], fieldnames: list[str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def _existing_count(filename: str) -> int:
    path = os.path.join(REAL, filename)
    if not os.path.exists(path):
        return 0
    with open(path, newline="", encoding="utf-8") as f:
        return sum(1 for _ in csv.DictReader(f))


def main() -> None:
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = {"fetched_at": fetched_at, "sources": []}

    print(f"[{fetched_at}] live-refreshing negative-registry sources over the real network...")

    # -- RBI Alert List --
    try:
        rbi_rows = fetch_rbi_alert_list()
        _write_csv(os.path.join(LIVE, "names__rbi.csv"), rbi_rows,
                   ["name_raw", "list_type", "authority"])
        before = _existing_count("names__rbi.csv")
        print(f"  RBI Alert List: {len(rbi_rows)} rows live (was {before} in seeds/real/) "
              f"{'— CHANGED' if len(rbi_rows) != before else '— unchanged'}")
        report["sources"].append({"source": "rbi_alert_list", "status": "ok",
                                  "rows_live": len(rbi_rows), "rows_previously_captured": before})
    except Exception as e:
        print(f"  RBI Alert List: FAILED — {e}")
        report["sources"].append({"source": "rbi_alert_list", "status": "failed", "error": str(e)})

    # -- OpenSanctions name datasets --
    all_names: list[dict] = []
    for slug, list_type, authority in OPENSANCTIONS_DATASETS:
        try:
            rows = fetch_opensanctions_names(slug, list_type, authority)
            all_names.extend(rows)
            print(f"  OpenSanctions {slug}: {len(rows)} rows live")
            report["sources"].append({"source": f"opensanctions:{slug}", "status": "ok",
                                      "rows_live": len(rows)})
        except Exception as e:
            print(f"  OpenSanctions {slug}: FAILED — {e}")
            report["sources"].append({"source": f"opensanctions:{slug}", "status": "failed",
                                      "error": str(e)})
    if all_names:
        _write_csv(os.path.join(LIVE, "names__opensanctions.csv"), all_names,
                   ["name_raw", "list_type", "authority"])
        before = _existing_count("names__opensanctions.csv")
        print(f"  OpenSanctions combined: {len(all_names)} rows live "
              f"(was {before} in seeds/real/) "
              f"{'— CHANGED' if len(all_names) != before else '— unchanged'}")

    with open(os.path.join(LIVE, "refresh_report.json"), "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nOutput: {LIVE}/ (NOT loaded into registry.db — seeds/real/ is untouched).")
    print("Review the diff, then copy into seeds/real/ and re-run `python3 seed_db.py`")
    print("yourself when ready. Still one-time-per-run, not scheduled — see module docstring.")


if __name__ == "__main__":
    main()
