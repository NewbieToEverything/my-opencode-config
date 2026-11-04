#!/usr/bin/env python3
"""Bounded, allowlisted Hermes inventory/history reads; no raw stderr output."""
import argparse
import json
import subprocess
import sys

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    m = sub.add_parser('models')
    m.add_argument('--provider', help='Optional exact provider slug')
    h = sub.add_parser('last-message')
    h.add_argument('--session', required=True, help='Exact session ID selected by user/task scope')
    a = p.parse_args()
    try:
        if a.action == 'models':
            code = '''import json
from hermes_cli.inventory import load_picker_context, build_models_payload
payload = build_models_payload(load_picker_context(), include_unconfigured=False)
for row in payload['providers']:
    print('HERMES_INVENTORY:' + json.dumps({'provider':row.get('slug'), 'models':row.get('models', [])}, ensure_ascii=False))
'''
            r = subprocess.run(['hermes', '--run-module', 'code'], input='exec(' + repr(code) + ')\n', capture_output=True, text=True, timeout=45)
            if r.returncode:
                raise RuntimeError()
            rows = []
            for line in r.stdout.splitlines():
                marker = 'HERMES_INVENTORY:'
                if marker in line:
                    row = json.loads(line.split(marker, 1)[1])
                    if not a.provider or row['provider'] == a.provider:
                        rows.append(row)
            if not rows:
                raise RuntimeError()
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            r = subprocess.run(['hermes', 'sessions', 'export', '--session-id', a.session, '--format', 'jsonl', '--lineage', 'single', '--yes', '-'], capture_output=True, text=True, timeout=30)
            if r.returncode:
                raise RuntimeError()
            sessions = []
            for line in r.stdout.splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if item.get('id') == a.session:
                    sessions.append(item)
            if len(sessions) != 1:
                raise RuntimeError()
            messages = [m for m in sessions[0].get('messages', []) if m.get('role') in ['user', 'assistant'] and m.get('content')]
            if not messages:
                raise RuntimeError()
            # Stored ordering is used within this exact transcript, not across sessions.
            last = messages[-1]
            print(json.dumps({'session_id': a.session, 'source': sessions[0].get('source'), 'role': last.get('role'), 'timestamp': last.get('timestamp'), 'content': last.get('content')}, ensure_ascii=False, indent=2))
    except Exception:
        print('Hermes read failed or returned no matching data; raw responses suppressed.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
