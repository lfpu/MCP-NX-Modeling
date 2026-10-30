# -*- coding: utf-8 -*-
'''Static consistency check (works without NX or the mcp SDK):
1. every run('cmd') in nx_mcp/tools has a matching @command('cmd') in nx_worker
2. every keyword passed by a tool exists as a parameter of the handler function
3. reports worker commands that no MCP tool exposes
'''
import ast
import glob
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def parse(path):
    with open(path, encoding='utf-8') as fp:
        return ast.parse(fp.read(), path)


def collect_handlers():
    out = {}
    files = glob.glob(os.path.join(ROOT, 'nx_worker', 'handlers', '*.py')) + [os.path.join(ROOT, 'nx_worker', 'dispatch.py')]
    for f in files:
        for node in ast.walk(parse(f)):
            if not isinstance(node, ast.FunctionDef):
                continue
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and getattr(dec.func, 'id', '') == 'command' and dec.args:
                    name = dec.args[0].value
                    params = [a.arg for a in node.args.args]
                    level = dec.args[1].value if len(dec.args) > 1 else 'modify'
                    out[name] = {'params': params, 'level': level, 'file': os.path.basename(f)}
    return out


def collect_calls():
    out = []
    for f in glob.glob(os.path.join(ROOT, 'nx_mcp', 'tools', '*.py')):
        for node in ast.walk(parse(f)):
            if isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'run' and node.args:
                if isinstance(node.args[0], ast.Constant):
                    out.append((node.args[0].value, [k.arg for k in node.keywords], os.path.basename(f)))
    return out


def main():
    handlers = collect_handlers()
    calls = collect_calls()
    errors = []
    used = set()
    for cmd, kws, f in calls:
        used.add(cmd)
        h = handlers.get(cmd)
        if h is None:
            errors.append('%s: run(%r) has no worker command' % (f, cmd))
            continue
        for k in kws:
            if k == 'confirm' and h['level'] == 'dangerous':
                continue
            if k not in h['params']:
                errors.append('%s: run(%r) passes unknown param %r (handler params: %s)' % (f, cmd, k, h['params']))
    unused = sorted(set(handlers) - used)
    print('worker commands : %d' % len(handlers))
    print('mcp tool calls  : %d' % len(calls))
    print('not exposed     : %s' % (', '.join(unused) or '-'))
    if errors:
        print('ERRORS:')
        for e in errors:
            print('  ' + e)
        return 1
    print('OK: tool <-> handler signatures are consistent')
    return 0


if __name__ == '__main__':
    sys.exit(main())
