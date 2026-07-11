"""FastAPI router for the screening module — thin wrappers only.

Mounted by ml/api/main.py via the guarded import in CONTRACTS.md:
    from screening.router import router as screening_router
    app.include_router(screening_router)

fastapi is imported here ONLY (it lives in the shared ml/ venv at runtime);
registry.py / graph.py / pan.py stay stdlib-importable for tests.
DB path resolves relative to __file__ inside registry.py / graph.py.
"""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query

try:
    from .graph import build_graph
    from .pan import validate_pan
    from .registry import DB_PATH, VALID_TYPES, check_identifier
except ImportError:  # mounted with ml/ on sys.path instead of as a package
    from graph import build_graph
    from pan import validate_pan
    from registry import DB_PATH, VALID_TYPES, check_identifier

router = APIRouter(prefix="/api", tags=["screening"])


def _require_db() -> None:
    if not os.path.exists(DB_PATH):
        raise HTTPException(
            status_code=503,
            detail="registry.db not built — run `python3 ml/screening/seed_db.py`",
        )


@router.get("/screen")
def screen(
    type: str = Query(..., description="pan|gstin|cin|din|name|account|vpa"),
    value: str = Query(..., min_length=1),
) -> dict:
    """Screen one identifier against every local negative registry."""
    _require_db()
    t = type.strip().lower()
    if t not in VALID_TYPES:
        raise HTTPException(status_code=422,
                            detail=f"type must be one of {sorted(VALID_TYPES)}")
    hits = check_identifier(t, value)
    return {"query": {"type": t, "value": value}, "hits": hits}


@router.get("/graph/{pan}")
def graph(pan: str) -> dict:
    """PAN-spine entity graph with phoenix detection (2-hop walk)."""
    _require_db()
    check = validate_pan(pan)
    if not check["valid"]:
        raise HTTPException(status_code=422,
                            detail=f"invalid PAN '{pan}': {'; '.join(check['errors'])}")
    return build_graph(check["value"])
