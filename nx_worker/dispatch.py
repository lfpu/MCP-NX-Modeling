# -*- coding: utf-8 -*-
'''Command dispatcher with the safety layer (Phase 6 core):
- read/session commands run directly
- modify commands run inside an Undo Mark, rolled back automatically on failure
- dangerous commands need confirm=true
- the last MAX_HISTORY successful modify operations can be undone with undo_last
'''
from collections import deque

import NXOpen

from nx_worker import ctx
from nx_worker.registry import COMMANDS, command

HISTORY = deque()
MAX_HISTORY = 20


def _drop(mark):
    try:
        ctx.session().DeleteUndoMark(mark, None)
    except Exception:
        pass


def run_command(cmd, params):
    entry = COMMANDS.get(cmd)
    if entry is None:
        raise ctx.NxError('未知命令: %s' % cmd)
    level = entry['level']
    fn = entry['fn']
    params = dict(params or {})

    if level == 'dangerous':
        if not params.pop('confirm', False):
            return {
                'needs_confirmation': True,
                'message': '这是危险操作（%s），需要用户明确同意后以 confirm=true 重新调用。' % cmd,
            }
    else:
        params.pop('confirm', None)

    try:
        if level in ('read', 'session'):
            return fn(**params)
    except TypeError as exc:
        raise ctx.NxError('参数错误: %s' % exc)

    session = ctx.session()
    mark = session.SetUndoMark(NXOpen.Session.MarkVisibility.Visible, cmd)
    try:
        result = fn(**params)
    except TypeError as exc:
        _rollback(session, mark)
        raise ctx.NxError('参数错误: %s' % exc)
    except Exception:
        _rollback(session, mark)
        raise
    HISTORY.append((mark, cmd))
    while len(HISTORY) > MAX_HISTORY:
        old, _name = HISTORY.popleft()
        _drop(old)
    return result


def _rollback(session, mark):
    try:
        session.UndoToMark(mark, None)
    except Exception:
        pass
    _drop(mark)


@command('undo_last', 'session')
def undo_last():
    '''Undo the most recent successful modify/dangerous operation.'''
    if not HISTORY:
        raise ctx.NxError('没有可撤销的操作')
    mark, name = HISTORY.pop()
    ctx.session().UndoToMark(mark, None)
    _drop(mark)
    return {'undone': name, 'remaining': len(HISTORY)}


@command('undo_history', 'read')
def undo_history():
    return {'operations': [name for _m, name in HISTORY]}
