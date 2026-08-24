"""Non-secret live readiness proof for a LORE demonstration."""

from __future__ import annotations

import json
import sys
from urllib import request


API = "http://127.0.0.1:8000"


def call(path: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{API}{path}",
        data=body,
        headers={"content-type": "application/json"} if body else {},
        method="POST" if body else "GET",
    )
    with request.urlopen(req, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    readiness = call("/api/security/readiness")
    checks.append(("Isolated Privacy Gateway", readiness.get("privacy_gateway_isolated") is True, str(readiness.get("protection_provider"))))
    checks.append(("Fail-closed policy", readiness.get("fail_closed") is True, "enabled" if readiness.get("fail_closed") else "disabled"))
    checks.append(("Credential isolation", readiness.get("credentials_exposed_to_api") is False, "API process has no Protegrity credentials"))
    checks.append(("Model adapter", readiness.get("model_provider") == "nvidia", str(readiness.get("model_provider"))))

    synthetic_email = "judge.synthetic@example.com"
    synthetic_canary = "sk-demo-preflight-canary-7719"
    protected = call(
        "/api/demo/protect",
        {"text": f"Requester: Ada Lovelace email {synthetic_email} account CUST-771900 api_key {synthetic_canary}"},
    )
    serialized = json.dumps(protected, sort_keys=True)
    checks.append(("Discovery + protection", protected.get("provider") == "protegrity" and len(protected.get("categories", [])) >= 3, f"{len(protected.get('categories', []))} entity categories"))
    checks.append(("Protected egress", synthetic_email not in serialized and synthetic_canary not in serialized, "0 raw canary matches"))
    checks.append(("Evidence fingerprint", len(str(protected.get("fingerprint") or "")) == 64, "SHA-256 recorded"))

    ai_review = call(
        "/api/demo/ai",
        {"text": f"Synthetic decision from {synthetic_email} for CUST-771900: replace shared retries with an in-memory queue."},
    )
    ai_serialized = json.dumps(ai_review, sort_keys=True)
    checks.append(("Protected NVIDIA inference", ai_review.get("model_provider") == "nvidia" and len(str(ai_review.get("response") or "")) > 20, "real response received"))
    checks.append(("Output leak scan", synthetic_email not in ai_serialized and "CUST-771900" not in ai_serialized, "0 released synthetic identifiers"))

    attacks = call("/api/attacks").get("scenarios", [])
    checks.append(("Attack Lab catalog", len(attacks) == 8, f"{len(attacks)}/8 scenarios"))
    attack = call("/api/demo/attack", {"scenario_id": "LPA-01"})
    checks.append(("Live prompt attack", attack.get("blocked") is True and attack.get("provider") == "protegrity", str(attack.get("blocked_boundary") or "not blocked")))

    chain = call("/api/security/overview").get("evidence_chain", {})
    checks.append(("Hash-chained receipts", chain.get("valid") is True and int(chain.get("checked_events", 0)) > 0, f"{chain.get('checked_events', 0)} linked events"))

    width = max(len(name) for name, _, _ in checks)
    for name, passed, evidence in checks:
        print(f"{name:<{width}}  {'PASS' if passed else 'FAIL'}  {evidence}")
    failed = [name for name, passed, _ in checks if not passed]
    if failed:
        print(f"\nPreflight failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nLORE preflight passed. No credentials or raw protected values were printed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
