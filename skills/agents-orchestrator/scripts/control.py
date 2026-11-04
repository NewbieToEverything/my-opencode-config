#!/usr/bin/env python3
"""Bounded OpenCode v2 control. No shell interpolation or raw error output."""
import argparse
import json
import subprocess
import sys

def call(operation, sid=None, body=None, timeout=30):
    args = ['opencode', 'api', operation]
    if sid:
        args += ['--param', 'sessionID=' + sid]
    if body is not None:
        args += ['--data', json.dumps(body, ensure_ascii=False)]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise RuntimeError('API timeout; delivery may have occurred. Inspect inbox/messages before retrying.')
    if r.returncode:
        raise RuntimeError('API failed; raw response suppressed. Reconcile state before retrying.')
    return json.loads(r.stdout) if r.stdout.strip() else {}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    c = sub.add_parser('create')
    c.add_argument('--directory', required=True)
    c.add_argument('--title', required=True)
    c.add_argument('--provider', default='opencode')
    c.add_argument('--model', default='deepseek-v4.1-flash-free')
    c.add_argument('--variant', default='max')
    for action in ['inspect', 'inbox', 'messages', 'send', 'wait', 'interrupt']:
        q = sub.add_parser(action)
        q.add_argument('--session', required=True)
        if action == 'send':
            q.add_argument('--file', required=True, help='UTF-8 task file; never pass secrets')
            q.add_argument('--delivery', choices=['queue', 'steer'], default='queue')
        if action == 'wait':
            q.add_argument('--timeout', type=int, default=30)
    a = p.parse_args()
    try:
        if a.action == 'create':
            from pathlib import Path
            directory = Path(a.directory).resolve(strict=True)
            if not directory.is_dir():
                raise RuntimeError('Project location is not a directory')
            models = call('model.list')['data']
            model = next((m for m in models if m['providerID'] == a.provider and m['id'] == a.model and m.get('enabled')), None)
            if model is None or a.variant not in [v.get('id') for v in model.get('variants', [])]:
                raise RuntimeError('Model/variant not advertised; no substitution performed')
            result = call('session.create', body={'title': a.title, 'location': {'directory': str(directory)}, 'model': {'providerID': a.provider, 'id': a.model, 'variant': a.variant}})
        else:
            # Never silently create a missing target, even for a send.
            session = call('session.get', a.session)['data']
            if session['id'] != a.session:
                raise RuntimeError('Session identity mismatch')
            if a.action == 'inspect':
                result = {'data': {k: session.get(k) for k in ['id', 'title', 'location', 'model', 'outcome', 'time']}}
            elif a.action == 'send':
                from pathlib import Path
                text = Path(a.file).read_text(encoding='utf-8')
                if not text.strip():
                    raise RuntimeError('Empty task')
                receipt = call('session.prompt', a.session, {'text': text, 'delivery': a.delivery})['data']
                result = {'id': receipt['id'], 'sessionID': receipt['sessionID'], 'delivery': receipt.get('delivery'), 'time': receipt.get('time')}
            elif a.action == 'wait':
                call('experimental.session.wait', a.session, timeout=a.timeout)
                result = {'idle': True, 'note': 'Idle does not prove success; inspect outcome and artifacts.'}
            elif a.action == 'interrupt':
                result = call('session.interrupt', a.session)
            else:
                result = call({'inbox': 'session.inbox.list', 'messages': 'session.message.list'}[a.action], a.session)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as e:
        # Do not print exception text from API JSON or file contents.
        if isinstance(e, RuntimeError):
            print(str(e), file=sys.stderr)
        else:
            print('Control operation failed; private details suppressed.', file=sys.stderr)
        return 1
    return 0

if __name__ == '__main__':
    sys.exit(main())
