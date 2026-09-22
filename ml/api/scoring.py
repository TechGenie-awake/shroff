"""Scoring engine: loads artifacts + data ONCE at startup, scores by msme_id from parquet.

Deterministic core — every number here comes from the trained bundle, never from an LLM.
"""
from __future__ import annotations

import json
import os
import uuid
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd

from features.build import FEATURE_NAMES, GROUPS, build_features, compute_firm_features
from train.scorecard import band_for_score, pd_to_score

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # ml/
DATA = os.path.join(ROOT, "data")
ARTIFACTS = os.path.join(ROOT, "artifacts")


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


class Engine:
    def __init__(self) -> None:
        self.bundle = joblib.load(os.path.join(ARTIFACTS, "model_bundle.joblib"))
        self.monthly = pd.read_parquet(os.path.join(DATA, "monthly.parquet"))
        self.profiles = pd.read_parquet(os.path.join(DATA, "msmes.parquet")).set_index(
            "msme_id", drop=False)
        self.counterparties = pd.read_parquet(os.path.join(DATA, "counterparties.parquet"))
        with open(os.path.join(DATA, "personas.json")) as fh:
            self.personas = json.load(fh)
        with open(os.path.join(ARTIFACTS, "metrics.json")) as fh:
            self.metrics = json.load(fh)
        # counterparty aggregates for feature parity with training
        bym = self.counterparties.groupby(["msme_id", "month"], sort=False).agg(
            top1=("share", "max"), cnt=("counterparty_gstin", "nunique"))
        self.cp_agg = bym.groupby(level="msme_id").mean()
        self.score_pop_ref = self._build_score_population_ref()
        self.loaded = True

    def _build_score_population_ref(self) -> np.ndarray:
        """Sorted array of the FULL population's combined calibrated 12-mo PD
        (personas excluded, same population train.py evaluates against) —
        computed once at startup via the already-trained bundle, not a
        retrain. Powers "this score ranks better than X% of the population"
        on the Model & Score tab. Lower PD = healthier, so the array is
        sorted ascending and a percentile is 1 - (rank of this PD / N)."""
        try:
            feats = pd.read_parquet(os.path.join(DATA, "features.parquet"))
        except FileNotFoundError:
            return np.array([])
        pop = self.profiles[self.profiles["is_persona"] == 0]
        X = feats.loc[feats.index.intersection(pop.index), FEATURE_NAMES]
        if len(X) == 0:
            return np.array([])
        b = self.bundle
        sub_arr = np.column_stack([
            b["sub_models"][g].predict_proba(X[b["group_features"][g]])[:, 1] for g in GROUPS
        ])
        raw_meta = b["meta"].predict_proba(_logit(sub_arr))[:, 1]
        pd_cal = b["calibrator"].predict(raw_meta)
        return np.sort(pd_cal)

    # ---------------- data access ----------------
    def has(self, msme_id: str) -> bool:
        return msme_id in self.profiles.index

    def profile(self, msme_id: str) -> dict:
        row = self.profiles.loc[msme_id].to_dict()
        return {k: (None if pd.isna(v) else v) for k, v in row.items()}

    def monthly_rows(self, msme_id: str) -> pd.DataFrame:
        return self.monthly[self.monthly["msme_id"] == msme_id].sort_values("month")

    def persona_meta(self, msme_id: str) -> dict | None:
        for p in self.personas:
            if p["id"] == msme_id:
                return p
        return None

    def consent(self, msme_id: str) -> dict:
        p = self.persona_meta(msme_id)
        if p and "consent_artefact" in p:
            return p["consent_artefact"]
        # non-persona firms: ReBIT-style template artefact (same shape as personas.json)
        prof = self.profile(msme_id)
        cid = str(uuid.uuid5(uuid.NAMESPACE_URL, f"shroff-consent-{msme_id}"))
        return {
            "ver": "2.0.0", "txnid": str(uuid.uuid5(uuid.NAMESPACE_URL, f"txn-{msme_id}")),
            "consentId": cid, "ConsentHandle": str(uuid.uuid5(uuid.NAMESPACE_URL, f"h-{msme_id}")),
            "status": "ACTIVE", "createTimestamp": "2026-06-28T10:15:00.000Z",
            "ConsentDetail": {
                "consentStart": "2026-06-28T10:15:00.000Z",
                "consentExpiry": "2027-06-28T10:15:00.000Z",
                "consentMode": "STORE", "fetchType": "PERIODIC",
                "consentTypes": ["PROFILE", "SUMMARY", "TRANSACTIONS"],
                "fiTypes": ["DEPOSIT", "GSTR1_3B"],
                "DataConsumer": {"id": "FIU-SHROFF-IDBI", "type": "FIU"},
                "Customer": {"id": f"{msme_id.lower()}@aa"},
                "Purpose": {"code": "103",
                            "refUri": "https://api.rebit.org.in/aa/purpose/103.xml",
                            "text": "Aggregated statement information for loan underwriting"},
            },
            "is_sample": True,
        }

    # ---------------- features + scoring ----------------
    def features_for(self, msme_id: str, overrides: dict[str, float] | None = None) -> pd.DataFrame:
        g = self.monthly_rows(msme_id)
        t1 = c1 = None
        if msme_id in self.cp_agg.index:
            t1 = self.cp_agg.loc[msme_id, "top1"]
            c1 = self.cp_agg.loc[msme_id, "cnt"]
        f = compute_firm_features(g, t1, c1)
        x = pd.DataFrame([f])[FEATURE_NAMES]
        if overrides:
            for k, v in overrides.items():
                if k not in FEATURE_NAMES:
                    raise KeyError(k)
                x.loc[:, k] = float(v)
        return x

    def score_features(self, x: pd.DataFrame) -> dict:
        b = self.bundle
        sub_probs = {g: float(b["sub_models"][g].predict_proba(x[b["group_features"][g]])[:, 1][0])
                     for g in GROUPS}
        arr = np.array([[sub_probs[g] for g in GROUPS]])
        raw_meta = float(b["meta"].predict_proba(_logit(arr))[:, 1][0])
        pd_cal = float(b["calibrator"].predict([raw_meta])[0])
        score = pd_to_score(pd_cal)
        band = band_for_score(score)
        sub_scores = {}
        for g in GROUPS:
            ref = b["pop_ref"][g]
            pct_below = np.searchsorted(ref, sub_probs[g], side="left") / len(ref)
            sub_scores[g] = int(round(100 * (1 - pct_below)))  # higher = healthier
        score_percentile = None
        if len(self.score_pop_ref):
            # healthier (lower PD) than this borrower, same "higher = healthier"
            # convention as sub_scores above: rank = count of population with
            # PD <= this one (as-good-or-better); the complement is how much
            # of the population this borrower outranks.
            rank_as_good_or_better = np.searchsorted(self.score_pop_ref, pd_cal, side="right")
            n = len(self.score_pop_ref)
            score_percentile = round(100 * (n - rank_as_good_or_better) / n, 1)
        return {"sub_probs": sub_probs, "raw_meta": raw_meta, "pd_12m": pd_cal,
                "score": score, "band": band, "sub_scores": sub_scores,
                "score_percentile": score_percentile,
                "population_n": int(len(self.score_pop_ref))}

    def model_info(self) -> dict:
        return {"version": self.bundle["version"],
                "auc": self.bundle["metrics"]["auc"],
                "ks": self.bundle["metrics"]["ks"],
                "trained_on": self.metrics.get("trained_on", "synthetic-v1")}


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    return Engine()
