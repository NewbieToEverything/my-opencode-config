#!/usr/bin/env python3
"""List enabled model IDs and reasoning variants without provider settings."""
import json
import subprocess
import sys

def main():
    try:
        r = subprocess.run(["opencode", "api", "model.list"], capture_output=True, text=True)
        if r.returncode:
            raise RuntimeError()
        rows = []
        for m in json.loads(r.stdout)["data"]:
            if not m.get("enabled"):
                continue
            rows.append({"providerID": m["providerID"], "id": m["id"],
                         "status": m["status"],
                         "variants": [v["id"] for v in m.get("variants", []) if isinstance(v, dict) and "id" in v]})
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    except Exception:
        print("Model discovery failed; raw responses suppressed.", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
