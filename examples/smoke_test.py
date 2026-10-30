# -*- coding: utf-8 -*-
'''End-to-end smoke test WITHOUT the MCP SDK: system Python -> TCP -> NX worker -> NX.

Builds a 120x80x15 base plate, R10 vertical-edge fillets, four D8 through holes and a D40 center hole.
Run from the project root:  python examples/smoke_test.py
The worker is auto-started with run_journal.exe (set NX_MCP_NXBIN if NX is not found).
'''
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import time  # noqa: E402

from nx_mcp.client import call, stop_worker  # noqa: E402

OUT = os.path.join(ROOT, 'examples', 'output', 'plate.prt')
L, W, H = 120.0, 80.0, 15.0


def step(title, cmd, **params):
    print('== ' + title)
    res = call(cmd, **params)
    print(json.dumps(res, ensure_ascii=False)[:600])
    return res


def top_face():
    res = call('find_faces', type='planar', extreme='top')
    if not res['faces']:
        raise RuntimeError('top face not found')
    return res['faces'][0]['id']


def main():
    # The NX worker is long-lived and keeps old code loaded: restart it so code edits take effect.
    stop_worker()
    time.sleep(3)
    step('status', 'status')
    step('new part', 'new_part', path=OUT, overwrite=True)
    step('block', 'create_block', length=L, width=W, height=H)

    print('== probe (which NX/UF APIs work)')
    print(json.dumps(call('debug_probe'), ensure_ascii=False, indent=1)[:3500])
    edges = call('find_edges', type='linear', parallel='top')
    ids = [e['id'] for e in edges['edges']]
    print('vertical edges:', len(ids))
    if not ids:
        allv = call('find_edges', limit=12, verbose=True)
        print('DEBUG all edges:', json.dumps(allv, ensure_ascii=False)[:1500])
        raise SystemExit('no vertical edges found, see DEBUG output above')
    step('fillet R10', 'edge_blend', edges=ids, radius=10.0)

    face = top_face()
    pts = [[15, 15, H], [L - 15, 15, H], [15, W - 15, H], [L - 15, W - 15, H]]
    step('4 x D8 through holes', 'create_hole', face=face, positions=pts, diameter=8.0, through=True)
    face = top_face()
    step('center D40 through hole', 'create_hole', face=face, positions=[[L / 2, W / 2, H]], diameter=40.0, through=True)

    step('part info', 'part_info')
    step('save', 'save_part')
    print('DONE ->', OUT)


if __name__ == '__main__':
    main()
