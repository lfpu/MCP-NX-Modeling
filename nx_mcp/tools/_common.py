# -*- coding: utf-8 -*-
from nx_mcp.client import NxWorkerError, call


def run(cmd, **params):
    '''Call a worker command and always return a dict with success=true/false.'''
    try:
        res = call(cmd, **params)
        out = {'success': True}
        if isinstance(res, dict):
            out.update(res)
        else:
            out['result'] = res
        return out
    except NxWorkerError as exc:
        return {'success': False, 'error': str(exc)}
    except Exception as exc:
        return {'success': False, 'error': '%s: %s' % (type(exc).__name__, exc)}
