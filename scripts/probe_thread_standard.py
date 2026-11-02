import json, os, sys, time
ROOT = os.path.abspath('.')
sys.path.insert(0, ROOT)
from nx_mcp.client import call, stop_worker

standards = ['Metric', 'ISO Metric', 'ISO Metric coarse', 'ISO Metric Coarse', 'Metric Coarse', 'GB Metric', 'DIN Metric']
sizes = ['M6', 'M6x1', 'M6 x 1', 'M6X1', 'M6 x 1.0', 'M6X1.0']
stop_worker()
time.sleep(3)
path = os.path.join(ROOT, 'examples', 'output', 'thread_standard_probe.prt')
call('new_part', path=path, overwrite=True)
call('create_block', length=60, width=40, height=20)
face = call('find_faces', type='planar', extreme='top')['faces'][0]['id']
results = []
for standard in standards:
    for size in sizes:
        try:
            value = call('threaded_hole', face=face, positions=[[30, 20, 20]], thread_standard=standard, thread_size=size, tap_drill_diameter=5.0, hole_depth=14.0, thread_depth=12.0, through=False, thread_length_option='custom', left_hand=False)
            results.append({'standard': standard, 'size': size, 'success': True, 'result': value})
            print(json.dumps(results[-1], ensure_ascii=False, default=str))
            with open(os.path.join(ROOT, 'logs', 'thread_standard_probe.json'), 'w', encoding='utf-8') as fp:
                json.dump(results, fp, ensure_ascii=False, indent=2, default=str)
            raise SystemExit(0)
        except Exception as exc:
            results.append({'standard': standard, 'size': size, 'success': False, 'error': str(exc)})
            print(json.dumps(results[-1], ensure_ascii=False))
with open(os.path.join(ROOT, 'logs', 'thread_standard_probe.json'), 'w', encoding='utf-8') as fp:
    json.dump(results, fp, ensure_ascii=False, indent=2)
raise SystemExit(1)
