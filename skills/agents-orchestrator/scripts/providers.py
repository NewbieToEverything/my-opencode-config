#!/usr/bin/env python3
"""Read provider availability; emit only non-credential allowlisted fields."""
import json
import subprocess
import sys

def request(operation):
    result = subprocess.run(["opencode", "api", operation], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(operation + " failed (response suppressed)")
    return json.loads(result.stdout)["data"]

def main():
    try:
        providers = request("provider.list")
        integrations = {x["id"]: x for x in request("integration.list")}
        rows = []
        for p in providers:
            integration = integrations.get(p.get("integrationID", p["id"]), {})
            rows.append({"id": p["id"], "name": p["name"],
                         "activation": p.get("activation"),
                         "configured_connections": len(integration.get("connections", []))})
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    except Exception:
        print("Provider discovery failed; raw responses suppressed.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
