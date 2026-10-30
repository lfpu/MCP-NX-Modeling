# -*- coding: utf-8 -*-
'''
Phase 0 - NX API technical verification (no MCP yet).

This script must run inside NX's embedded Python host, for example:
  - phase0/run_phase0.ps1  (uses run_journal.exe, headless)
  - NX: File > Execute > NX Open

Chain under test:
  connect session -> new part (mm) -> create 100x60x20 block -> query model
  -> (optional) measure volume -> save .prt -> (optional) reopen -> write result.json

Output directory: env NX_PHASE0_OUT, default <this script dir>/output
'''
import io
import json
import os
import sys
import time
import traceback

try:
    import NXOpen
    import NXOpen.Features
    import NXOpen.GeometricUtilities
except ImportError:
    print('NXOpen not found. Run this script inside NX (run_journal.exe or File > Execute > NX Open).', file=sys.stderr)
    sys.exit(2)

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = os.getcwd()

OUT_DIR = os.environ.get('NX_PHASE0_OUT') or os.path.join(HERE, 'output')
PART_PATH = os.path.join(OUT_DIR, 'phase0_block.prt')
RESULT_PATH = os.path.join(OUT_DIR, 'result.json')

LENGTH, WIDTH, HEIGHT = 100.0, 60.0, 20.0
EXPECTED_VOLUME = LENGTH * WIDTH * HEIGHT
EXPECTED_FACES = 6
EXPECTED_EDGES = 12

_listing = [None]


def log(msg):
    # run_journal echoes the listing window to the console, so write to only one
    # channel to avoid duplicated lines; fall back to print() when no listing window.
    lw = _listing[0]
    if lw is not None:
        try:
            lw.WriteLine(msg)
            return
        except Exception:
            pass
    try:
        print(msg)
    except Exception:
        pass


class Recorder(object):
    '''Runs steps, records status/time/error for each one.'''

    def __init__(self):
        self.steps = []

    def run(self, name, fn, optional=False):
        t0 = time.time()
        entry = {'name': name, 'status': 'ok', 'optional': optional}
        try:
            detail = fn()
            if detail is not None:
                entry['detail'] = detail
            return detail
        except Exception as exc:
            entry['status'] = 'warn' if optional else 'fail'
            entry['error'] = '%s: %s' % (type(exc).__name__, exc)
            entry['traceback'] = traceback.format_exc()
            if not optional:
                raise
            return None
        finally:
            entry['ms'] = int((time.time() - t0) * 1000)
            self.steps.append(entry)
            log('[%s] %s (%d ms)%s' % (entry['status'], name, entry['ms'], (' - ' + entry['error']) if 'error' in entry else ''))


# ---------------------------------------------------------------- steps

def step_session(state):
    session = NXOpen.Session.GetSession()
    state['session'] = session
    try:
        session.ListingWindow.Open()
        _listing[0] = session.ListingWindow
    except Exception:
        pass
    info = {'python': sys.version.split()[0]}
    for key in ('UGII_BASE_DIR', 'UGII_ROOT_DIR', 'UGII_VERSION'):
        try:
            info[key] = session.GetEnvironmentVariableValue(key)
        except Exception:
            info[key] = os.environ.get(key)
    state['nx_info'] = info
    return info


def step_new_part(state):
    session = state['session']
    if os.path.exists(PART_PATH):
        os.remove(PART_PATH)
    part = session.Parts.NewDisplay(PART_PATH, NXOpen.Part.Units.Millimeters)
    state['part'] = part
    work = session.Parts.Work
    return {'path': PART_PATH, 'work_part': work.Name if work is not None else None}


def step_block(state):
    session = state['session']
    part = state['part']
    mark = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, 'Phase0 Block')
    builder = part.Features.CreateBlockFeatureBuilder(NXOpen.Features.Feature.Null)
    try:
        builder.Type = NXOpen.Features.BlockFeatureBuilder.Types.OriginAndEdgeLengths
        builder.SetOriginAndLengths(NXOpen.Point3d(0.0, 0.0, 0.0), str(LENGTH), str(WIDTH), str(HEIGHT))
        builder.BooleanOption.Type = NXOpen.GeometricUtilities.BooleanOperation.BooleanType.Create
        feature = builder.CommitFeature()
    except Exception:
        try:
            session.UndoToMark(mark, None)
        except Exception:
            pass
        raise
    finally:
        builder.Destroy()
    try:
        session.DeleteUndoMark(mark, None)
    except Exception:
        pass
    state['feature'] = feature
    return {
        'name': feature.Name,
        'journal_id': feature.JournalIdentifier,
        'type': feature.FeatureType,
        'size_mm': [LENGTH, WIDTH, HEIGHT],
    }


def step_query(state):
    part = state['part']
    bodies = list(part.Bodies)
    state['bodies'] = bodies
    out = []
    for b in bodies:
        out.append({
            'journal_id': b.JournalIdentifier,
            'is_solid': bool(b.IsSolidBody),
            'faces': len(b.GetFaces()),
            'edges': len(b.GetEdges()),
        })
    features = [{'name': f.Name, 'journal_id': f.JournalIdentifier} for f in part.Features]
    detail = {'bodies': out, 'features': features}
    if len(bodies) != 1:
        raise AssertionError('expected 1 body, got %d' % len(bodies))
    if out[0]['faces'] != EXPECTED_FACES or out[0]['edges'] != EXPECTED_EDGES:
        raise AssertionError('expected %d faces / %d edges, got %d / %d' % (EXPECTED_FACES, EXPECTED_EDGES, out[0]['faces'], out[0]['edges']))
    return detail


def step_volume(state):
    part = state['part']
    uc = part.UnitCollection
    units = [NXOpen.Unit.Null] * 5
    units[0] = uc.FindObject('SquareMilliMeter')
    units[1] = uc.FindObject('CubicMilliMeter')
    units[2] = uc.FindObject('Kilogram')
    units[3] = uc.FindObject('Newton')
    units[4] = uc.FindObject('MilliMeter')
    mp = part.MeasureManager.NewMassProperties(units, 0.99, [state['bodies'][0]])
    try:
        volume = mp.Volume
    finally:
        mp.Dispose()
    if abs(volume - EXPECTED_VOLUME) > EXPECTED_VOLUME * 0.001:
        raise AssertionError('volume %.3f differs from expected %.3f' % (volume, EXPECTED_VOLUME))
    return {'volume_mm3': volume, 'expected_mm3': EXPECTED_VOLUME}


def step_save(state):
    part = state['part']
    part.Save(NXOpen.BasePart.SaveComponents.TrueValue, NXOpen.BasePart.CloseAfterSave.FalseValue)
    if not os.path.exists(PART_PATH):
        raise IOError('part file not found after save: ' + PART_PATH)
    size = os.path.getsize(PART_PATH)
    if size <= 0:
        raise IOError('part file is empty: ' + PART_PATH)
    return {'path': PART_PATH, 'size_bytes': size}


def step_reopen(state):
    session = state['session']
    session.Parts.CloseAll(NXOpen.BasePart.CloseModified.CloseModified, None)
    base_part, status = session.Parts.OpenBaseDisplay(PART_PATH)
    try:
        status.Dispose()
    except Exception:
        pass
    work = session.Parts.Work
    count = len(list(work.Bodies))
    if count != 1:
        raise AssertionError('after reopen expected 1 body, got %d' % count)
    return {'bodies_after_reopen': count}


# ---------------------------------------------------------------- main

def main():
    rec = Recorder()
    state = {}
    error = None
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        rec.run('connect_session', lambda: step_session(state))
        rec.run('new_part', lambda: step_new_part(state))
        rec.run('create_block', lambda: step_block(state))
        rec.run('query_model', lambda: step_query(state))
        rec.run('measure_volume', lambda: step_volume(state), optional=True)
        rec.run('save_part', lambda: step_save(state))
        rec.run('reopen_part', lambda: step_reopen(state), optional=True)
    except Exception as exc:
        error = '%s: %s' % (type(exc).__name__, exc)

    success = error is None and not any(s['status'] == 'fail' for s in rec.steps)
    result = {
        'success': success,
        'error': error,
        'nx': state.get('nx_info'),
        'part_path': PART_PATH,
        'steps': rec.steps,
    }
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        with io.open(RESULT_PATH, 'w', encoding='utf-8') as fp:
            fp.write(json.dumps(result, ensure_ascii=False, indent=2))
    except Exception as exc:
        log('failed to write result.json: %s' % exc)
    log('PHASE 0 %s' % ('PASSED' if success else 'FAILED'))
    return 0 if success else 1


if __name__ == '__main__':
    code = main()
    if code != 0:
        sys.exit(code)
