"""SHROFF Track B — negative-registry screening + PAN-spine entity graph.

Stdlib-only core (sqlite3, csv, json, re, urllib, unicodedata, difflib).
`router.py` is the only module that imports fastapi (available in the shared
ml/ venv at runtime). Keep this __init__ import-free so `screening.registry`
and `screening.graph` stay importable without fastapi installed.
"""
