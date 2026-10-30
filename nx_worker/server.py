# -*- coding: utf-8 -*-
'''Single-threaded newline-delimited JSON server running inside NX.

NXOpen must be used from the main thread, so connections are handled one at a time.
Request : {"id":1,"cmd":"create_block","params":{...},"token":"..."}
Response: {"id":1,"ok":true,"result":{...}} | {"id":1,"ok":false,"error":{...}}
'''
import json
import socket
import sys
import traceback

from nx_worker import ctx, handlers
from nx_worker.dispatch import run_command
from nx_worker.registry import COMMANDS

STATE = {'running': True}


def handle_request(req, token):
    rid = req.get('id')
    try:
        if token and req.get('token') != token:
            raise ctx.NxError('token 不匹配')
        cmd = req.get('cmd')
        params = req.get('params') or {}
        if cmd == 'ping':
            result = {
                'python': sys.version.split()[0],
                'commands': sorted(COMMANDS),
                'load_errors': handlers.LOAD_ERRORS,
            }
        elif cmd == 'shutdown':
            STATE['running'] = False
            result = {'bye': True}
        else:
            result = run_command(cmd, params)
        return {'id': rid, 'ok': True, 'result': result}
    except Exception as exc:
        return {
            'id': rid,
            'ok': False,
            'error': {
                'type': type(exc).__name__,
                'message': str(exc),
                'trace': traceback.format_exc()[-1500:],
            },
        }


def _serve_connection(conn, token, log):
    conn.settimeout(None)
    f = conn.makefile('rwb')
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line.decode('utf-8'))
        except Exception as exc:
            resp = {'id': None, 'ok': False, 'error': {'type': 'BadRequest', 'message': str(exc)}}
        else:
            log('cmd=%s' % req.get('cmd'))
            resp = handle_request(req, token)
            if not resp['ok']:
                log('  error: %s' % resp['error']['message'])
        data = json.dumps(resp, ensure_ascii=False, default=str).encode('utf-8') + b'\n'
        f.write(data)
        f.flush()
        if not STATE['running']:
            break


def serve(host, port, token='', log=print):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    srv.settimeout(1.0)
    log('NX worker listening on %s:%d (%d commands)' % (host, port, len(COMMANDS)))
    try:
        while STATE['running']:
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            try:
                _serve_connection(conn, token, log)
            except Exception as exc:
                log('connection error: %s' % exc)
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    finally:
        srv.close()
        log('NX worker stopped')
