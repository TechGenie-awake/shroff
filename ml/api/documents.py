"""Sample document generation + upload parsing — the "download sample data,
upload it live" demo flow.

Two files, mirroring CONTRACTS.md's actual profile + monthly schema exactly
(so parsing an upload is a near-trivial round-trip, not a new format):
  business_profile.csv — one row, identity fields
  monthly_history.csv  — 24 rows, the same bank/GST/EPFO monthly columns
                          compute_firm_features() already consumes

`generate_sample_zip(identifier)` renders these from the SAME deterministic
simulation live_intake.simulate() uses for the "live lookup" feature, zipped
for download. `parse_uploaded_zip_or_csvs()` reads them back — critically,
the score that comes out reflects whatever is actually IN the uploaded
files, not a re-simulation from the identifier — so editing a row before
re-uploading (e.g. adding bounces) visibly changes the score. That's the
honest "live processing" demo: real parse, real feature computation, real
scoring, on documents that happen to originate from a labeled simulation
pending IDBI's real GSTN/Bank-AA/EPFO sandbox.
"""
from __future__ import annotations

import csv
import io
import zipfile

import pandas as pd

from api.live_intake import LiveIntakeError, resolve_identifier, simulate

PROFILE_FIELDS = [
    "msme_id", "name", "legal_name", "entity_type", "sector", "city",
    "state_code", "pan", "gstin", "cin", "promoter_name", "promoter_pan",
    "promoter_din", "udyam", "incorporated_on", "requested_amount_inr",
]
MONTHLY_FIELDS = [
    "month", "bank_inflow_inr", "bank_outflow_inr", "eod_balance_avg_inr",
    "eod_balance_min_inr", "days_near_zero", "upi_txn_count", "upi_inflow_share",
    "bounce_count", "emi_debit_inr", "self_transfer_inr", "gst_turnover_declared_inr",
    "gst_filed_on_time", "gst_filing_delay_days", "gst_nil_return", "b2b_share",
    "top3_buyer_share", "employees_epfo", "wage_bill_inr",
]

README = """SHROFF — sample MSME documents (SIMULATED, for the live-demo upload flow)

These two files are what a real submission would look like once IDBI's GSTN /
Account Aggregator / EPFO sandbox is wired in: a business identity file and a
24-month bank+GST+EPFO history. Today they're deterministically SIMULATED
from the identifier (business_profile.csv is honest about this).

Try it: edit a few numbers in monthly_history.csv (e.g. raise bounce_count,
or drop bank_inflow_inr for the last few months) and re-upload both files at
/console — the score, band and decision change to match exactly what you
typed, computed by the same monotonic LightGBM pipeline as everything else
in SHROFF. Nothing is re-simulated on upload; the files ARE the source of
truth for the score.
"""


def _csv_bytes(rows: list[dict], fields: list[str]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fields)
    w.writeheader()
    for r in rows:
        w.writerow({k: r.get(k, "") for k in fields})
    return buf.getvalue().encode("utf-8")


def generate_sample_zip(identifier: str, requested_amount_inr: int | None = None) -> tuple[bytes, str]:
    """Returns (zip_bytes, suggested_filename)."""
    profile, monthly, _meta = simulate(identifier, requested_amount_inr)
    profile_csv = _csv_bytes([profile], PROFILE_FIELDS)
    monthly_csv = _csv_bytes(monthly.to_dict(orient="records"), MONTHLY_FIELDS)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("README.txt", README)
        zf.writestr("business_profile.csv", profile_csv)
        zf.writestr("monthly_history.csv", monthly_csv)
    filename = f"shroff-sample-{profile['pan']}.zip"
    return buf.getvalue(), filename


class DocumentParseError(ValueError):
    pass


def _read_csv_bytes(raw: bytes, required_cols: list[str], label: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(io.BytesIO(raw))
    except Exception as e:
        raise DocumentParseError(f"Couldn't read {label} as CSV: {e}")
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise DocumentParseError(f"{label} is missing required column(s): {', '.join(missing)}")
    return df


def parse_uploaded_documents(profile_csv: bytes, monthly_csv: bytes) -> tuple[dict, pd.DataFrame]:
    """Parses exactly what's in the two uploaded files — no re-simulation.
    Raises DocumentParseError with a human-readable message on anything malformed."""
    prof_df = _read_csv_bytes(profile_csv, ["pan"], "business_profile.csv")
    if len(prof_df) == 0:
        raise DocumentParseError("business_profile.csv has no data rows")
    profile = {k: (None if pd.isna(v) else v) for k, v in prof_df.iloc[0].to_dict().items()}

    identifier = str(profile.get("gstin") or profile.get("pan") or "").strip()
    try:
        resolved = resolve_identifier(identifier)
    except LiveIntakeError as e:
        raise DocumentParseError(f"business_profile.csv has an invalid PAN/GSTIN: {e}")
    canonical_id = resolved["gstin"] or resolved["pan"]
    profile["msme_id"] = f"LIVE-{canonical_id}"
    profile["pan"] = resolved["pan"]
    profile["gstin"] = resolved["gstin"]
    profile.setdefault("name", profile.get("legal_name") or canonical_id)
    profile["is_simulated"] = True
    if profile.get("requested_amount_inr") in (None, ""):
        profile["requested_amount_inr"] = 1000000
    else:
        profile["requested_amount_inr"] = int(float(profile["requested_amount_inr"]))

    required_monthly = ["month", "bank_inflow_inr", "bank_outflow_inr", "eod_balance_avg_inr",
                         "eod_balance_min_inr", "top3_buyer_share", "employees_epfo"]
    monthly = _read_csv_bytes(monthly_csv, required_monthly, "monthly_history.csv")
    if len(monthly) < 3:
        raise DocumentParseError(
            f"monthly_history.csv has only {len(monthly)} month(s) — need at least 3 "
            "for the feature engine to compute meaningful trends")
    for col in MONTHLY_FIELDS:
        if col == "month":
            continue
        if col in monthly.columns:
            monthly[col] = pd.to_numeric(monthly[col], errors="coerce").fillna(0.0)
        else:
            monthly[col] = 0.0
    monthly = monthly.sort_values("month").reset_index(drop=True)
    return profile, monthly
