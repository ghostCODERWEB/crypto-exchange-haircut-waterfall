"""Apply asset valuation haircuts and allocate recoverable estate by creditor seniority with exact unit reconciliation."""

from .common import (
    number,
    integer,
    identity,
    records,
    chronology,
    allocate,
    result,
    validate_document,
)
from decimal import Decimal


def _analyze(d):
    assets = records(d["assets"], "id")
    estate = 0
    asset_rows = []
    for a in assets:
        gross = integer(a["value"])
        haircut = integer(a["haircut_bps"], maximum=10000)
        recoverable = gross * (10000 - haircut) // 10000
        estate += recoverable
        asset_rows.append({"id": a["id"], "gross": gross, "recoverable": recoverable})
    claims = records(d["claims"], "id")
    paid = {c["id"]: 0 for c in claims}
    remaining = estate
    for rank in sorted(set(integer(c["rank"]) for c in claims)):
        weights = {
            c["id"]: integer(c["amount"])
            for c in claims
            if c["rank"] == rank and integer(c["amount"]) > 0
        }
        if weights:
            amount = min(remaining, sum(weights.values()))
            paid.update(allocate(amount, weights))
            remaining -= amount
    rows = [
        {
            "id": c["id"],
            "claim": c["amount"],
            "recovery": paid[c["id"]],
            "loss": c["amount"] - paid[c["id"]],
        }
        for c in claims
    ]
    return {
        "assets": asset_rows,
        "estate": estate,
        "claims": rows,
        "distributed": sum(paid.values()),
        "surplus": remaining,
        "total_loss": sum(r["loss"] for r in rows),
    }


def analyze(document):
    validate_document(document)
    try:
        return result(_analyze(document))
    except (KeyError, TypeError, ArithmeticError, RecursionError) as error:
        raise ValueError("invalid domain input: " + str(error)) from error
