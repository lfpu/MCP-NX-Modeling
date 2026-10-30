# -*- coding: utf-8 -*-
'''Seventh probe: ParentViewBuilder of ProjectedViewBuilder (needs a sheet + base view).
Usage: python scripts/probe_api7.py > logs/probe7.txt'''
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from nx_mcp.client import call, stop_worker  # noqa: E402


def show(title, r):
    print('== %s -> %d' % (title, r['count']))
    print('   ' + ', '.join(r['names']))


def main():
    stop_worker()
    time.sleep(3)
    call('new_part', path=os.path.join(ROOT, 'examples', 'output', 'probe7.prt'), overwrite=True)
    call('create_block', length=20, width=20, height=20)
    call('create_drawing_sheet', size='A3')
    call('add_base_view', view='front', position=[150, 150])
    for fac, sub in [('DraftingViews.CreateProjectedViewBuilder', 'Parent'),
                     ('DraftingViews.CreateProjectedViewBuilder', 'Placement')]:
        try:
            show('%s %s' % (fac, sub), call('debug_builder_ex', factory=fac, sub=sub))
        except Exception as exc:
            print('== %s %s ERR %s' % (fac, sub, str(exc)[:200]))
    for path in ['NXOpen.Drawings.ParentViewBuilder', 'NXOpen.Drawings.ProjectedViewBuilder']:
        try:
            show(path, call('debug_dir', path=path))
        except Exception as exc:
            print('== %s ERR %s' % (path, str(exc)[:200]))


if __name__ == '__main__':
    main()
