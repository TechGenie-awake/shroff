"""Pure identifier functions for the Indian PAN spine.

PAN  : AAAAA9999A — 5 letters, 4 digits, 1 letter. 4th char encodes entity type.
GSTIN: 15 chars   — 2-digit state code + PAN(10) + entity number + 'Z' slot + checksum.
       Chars 3-12 of a GSTIN ARE the holder's PAN (the deterministic join key).
DIN  : 8 digits, one-per-person-for-life (Companies Act s.155).

Per CONTRACTS.md, checksum digits are NOT enforced anywhere — structure only.
Stdlib only. No side effects. Run `python3 pan.py` for self-tests.
"""

from __future__ import annotations

import re
import unicodedata

# ---------------------------------------------------------------- PAN

PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")

# 4th character of PAN → holder entity type (CBDT scheme)
PAN_ENTITY_TYPES = {
    "A": "Association of Persons (AOP)",
    "B": "Body of Individuals (BOI)",
    "C": "Company",
    "F": "Firm / LLP",
    "G": "Government",
    "H": "Hindu Undivided Family (HUF)",
    "J": "Artificial Juridical Person",
    "L": "Local Authority",
    "P": "Individual",
    "T": "Trust",
}


def _clean(value: str) -> str:
    return re.sub(r"\s+", "", str(value or "")).upper()


def validate_pan(pan: str) -> dict:
    """Structural PAN validation + entity-type decode of the 4th character."""
    v = _clean(pan)
    errors = []
    if len(v) != 10:
        errors.append(f"PAN must be 10 characters, got {len(v)}")
    elif not PAN_RE.match(v):
        errors.append("PAN must match AAAAA9999A (5 letters, 4 digits, 1 letter)")
    entity_code = v[3] if len(v) >= 4 else ""
    entity_type = PAN_ENTITY_TYPES.get(entity_code)
    if not errors and entity_type is None:
        errors.append(f"4th character '{entity_code}' is not a known entity code")
    return {
        "valid": not errors,
        "value": v,
        "entity_code": entity_code if not errors else (entity_code or None),
        "entity_type": entity_type,
        "errors": errors,
    }


# ---------------------------------------------------------------- GSTIN

# GST state codes (Census 2011 scheme used by GSTN)
GST_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar", "11": "Sikkim",
    "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "25": "Daman & Diu", "26": "Dadra & Nagar Haveli and Daman & Diu",
    "27": "Maharashtra", "28": "Andhra Pradesh (old)", "29": "Karnataka",
    "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands", "36": "Telangana",
    "37": "Andhra Pradesh", "38": "Ladakh",
    "97": "Other Territory", "99": "Centre / Other",
}

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z][A-Z0-9][A-Z0-9]$")


def validate_gstin(gstin: str) -> dict:
    """15-char structural GSTIN validation with state-code decode and
    embedded-PAN extraction. Checksum (char 15) is NOT verified (contract)."""
    v = _clean(gstin)
    errors = []
    if len(v) != 15:
        errors.append(f"GSTIN must be 15 characters, got {len(v)}")
    elif not GSTIN_RE.match(v):
        errors.append("GSTIN must match 2 digits + PAN(10) + entity char + 2 alphanumerics")
    state_code = v[:2] if len(v) >= 2 else ""
    state = GST_STATE_CODES.get(state_code)
    if not errors and state is None:
        errors.append(f"unknown GST state code '{state_code}'")
    pan_part = v[2:12] if len(v) == 15 else ""
    pan_check = validate_pan(pan_part) if pan_part else {"valid": False, "entity_type": None}
    if not errors and not pan_check["valid"]:
        errors.append("embedded PAN (chars 3-12) is not structurally valid")
    return {
        "valid": not errors,
        "value": v,
        "state_code": state_code or None,
        "state": state,
        "pan": pan_part or None,
        "pan_entity_type": pan_check.get("entity_type"),
        "entity_number": v[12] if len(v) == 15 else None,
        "errors": errors,
    }


def gstin_to_pan(gstin: str) -> str | None:
    """GSTIN chars 3-12 ARE the PAN. Returns None if not structurally extractable."""
    v = _clean(gstin)
    if len(v) != 15:
        return None
    pan = v[2:12]
    return pan if validate_pan(pan)["valid"] else None


def pan_to_possible_gstin_prefix(pan: str, state_code: str | int | None = None) -> str | None:
    """The 12-char GSTIN prefix a PAN holder's registrations must start with.

    With a state_code → exact prefix, e.g. ('ABCPR3456K', 27) → '27ABCPR3456K'.
    Without → SQL-LIKE pattern '__ABCPR3456K' (any state).
    """
    p = _clean(pan)
    if not validate_pan(p)["valid"]:
        return None
    if state_code is None:
        return "__" + p
    sc = str(state_code).zfill(2)
    if sc not in GST_STATE_CODES:
        return None
    return sc + p


# ---------------------------------------------------------------- DIN

DIN_RE = re.compile(r"^[0-9]{8}$")


def validate_din(din: str) -> dict:
    """DIN: exactly 8 digits (MCA Director Identification Number)."""
    v = _clean(din)
    errors = [] if DIN_RE.match(v) else ["DIN must be exactly 8 digits"]
    return {"valid": not errors, "value": v, "errors": errors}


# ---------------------------------------------------------------- normalizers

# trailing legal-form tokens stripped (repeatedly) from names
_LEGAL_SUFFIXES = {
    "PVT", "LTD", "PRIVATE", "LIMITED", "LLP", "PLC", "OPC", "CO", "COMPANY",
}
_MS_PREFIX_RE = re.compile(r"^M/?S\.?\s+", re.IGNORECASE)
_PUNCT_RE = re.compile(r"[^A-Z0-9 ]+")
_WS_RE = re.compile(r"\s+")


def _to_ascii_upper(text: str) -> str:
    t = unicodedata.normalize("NFKD", str(text or ""))
    t = t.encode("ascii", "ignore").decode("ascii")
    return t.upper()


def normalize_name(name: str) -> str:
    """Canonical form for entity-name matching: ASCII upper, 'M/S' prefix and
    punctuation stripped, legal suffixes (PVT/LTD/PRIVATE/LIMITED/LLP/CO...)
    removed from the tail, whitespace collapsed."""
    t = _to_ascii_upper(name)
    t = _MS_PREFIX_RE.sub("", t)
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    tokens = t.split(" ")
    while len(tokens) > 1 and tokens[-1] in _LEGAL_SUFFIXES:
        tokens.pop()
    return " ".join(tokens)


def normalize_address(address: str) -> str:
    """Canonical form for registered-address matching: ASCII upper,
    punctuation stripped, whitespace collapsed."""
    t = _to_ascii_upper(address)
    t = _PUNCT_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip()


# ---------------------------------------------------------------- self-tests

if __name__ == "__main__":
    failures = 0

    def check(label, got, want):
        global failures
        ok = got == want
        if not ok:
            failures += 1
        print(f"  [{'ok' if ok else 'FAIL'}] {label}: got={got!r}" + ("" if ok else f" want={want!r}"))

    print("pan.py self-tests")

    r = validate_pan("ABCPR3456K")          # RAMESH001 — individual
    check("PAN ABCPR3456K valid", r["valid"], True)
    check("PAN ABCPR3456K entity", r["entity_type"], "Individual")
    r = validate_pan("AAECN1234F")          # PHOENIX003 company PAN
    check("PAN AAECN1234F entity", r["entity_type"], "Company")
    check("PAN lowercase+spaces cleaned", validate_pan(" aabcv9876l ")["valid"], True)
    check("PAN bad length invalid", validate_pan("ABCPR3456")["valid"], False)
    check("PAN bad 4th char invalid", validate_pan("ABCXR3456K")["valid"], False)
    check("PAN digits-in-wrong-place invalid", validate_pan("1BCPR3456K")["valid"], False)

    g = validate_gstin("27ABCPR3456K1Z5")   # RAMESH001
    check("GSTIN 27ABCPR3456K1Z5 valid", g["valid"], True)
    check("GSTIN state decode", g["state"], "Maharashtra")
    check("GSTIN embedded PAN", g["pan"], "ABCPR3456K")
    g = validate_gstin("07AAECN1234F1Z2")   # PHOENIX003
    check("GSTIN 07... state", g["state"], "Delhi")
    check("GSTIN 07... pan entity", g["pan_entity_type"], "Company")
    check("GSTIN bad state code invalid", validate_gstin("00ABCPR3456K1Z5")["valid"], False)
    check("GSTIN 14 chars invalid", validate_gstin("27ABCPR3456K1Z")["valid"], False)
    check("GSTIN bad embedded PAN invalid", validate_gstin("27AB1PR3456K1Z5")["valid"], False)

    check("gstin_to_pan", gstin_to_pan("27AABCT5678Q1Z9"), "AABCT5678Q")
    check("gstin_to_pan bad input", gstin_to_pan("garbage"), None)
    check("pan_to_possible_gstin_prefix w/ state", pan_to_possible_gstin_prefix("ABCPR3456K", 27), "27ABCPR3456K")
    check("pan_to_possible_gstin_prefix wildcard", pan_to_possible_gstin_prefix("ABCPR3456K"), "__ABCPR3456K")
    check("pan_to_possible_gstin_prefix bad pan", pan_to_possible_gstin_prefix("NOPE"), None)
    check("roundtrip pan->prefix->pan", gstin_to_pan(pan_to_possible_gstin_prefix("AEXPM4521C", 7) + "1Z9"), "AEXPM4521C")

    check("DIN 08234567 valid", validate_din("08234567")["valid"], True)
    check("DIN 7 digits invalid", validate_din("1234567")["valid"], False)
    check("DIN letters invalid", validate_din("0823456A")["valid"], False)

    check("normalize_name strips Pvt Ltd", normalize_name("Vertex Impex Pvt. Ltd."), "VERTEX IMPEX")
    check("normalize_name strips Private Limited", normalize_name("Nexon Trading Private Limited"), "NEXON TRADING")
    check("normalize_name strips M/s + Co", normalize_name("M/s Suresh Trading Co."), "SURESH TRADING")
    check("normalize_name ampersand", normalize_name("Ramesh Kirana & General Stores"), "RAMESH KIRANA GENERAL STORES")
    check("normalize_name keeps lone token", normalize_name("Limited"), "LIMITED")
    check("normalize_name accents", normalize_name("Café Réal Pvt Ltd"), "CAFE REAL")
    check("normalize_address persona thread",
          normalize_address("14, Karol Bagh Industrial Area, Delhi - 110005"),
          "14 KAROL BAGH INDUSTRIAL AREA DELHI 110005")
    check("normalize_address hash/slash",
          normalize_address("Plot #7/B, MIDC, Andheri (E), Mumbai-400093"),
          "PLOT 7 B MIDC ANDHERI E MUMBAI 400093")

    print(f"pan.py: {'ALL TESTS PASSED' if failures == 0 else f'{failures} FAILURES'}")
    raise SystemExit(0 if failures == 0 else 1)
