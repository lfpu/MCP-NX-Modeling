# -*- coding: utf-8 -*-
'''Entry point executed inside NX:
  run_journal.exe nx_worker/main.py      (headless)
  or NX: File > Execute > NX Open        (blocks the GUI while serving)
Env: NX_MCP_ROOT, NX_MCP_HOST, NX_MCP_PORT, NX_MCP_TOKEN
'''
import os
import sys
import time
import traceback


def _root():
    env = os.environ.get('NX_MCP_ROOT')
    if env:
        return env
    try:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        return os.getcwd()


ROOT = _root()
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

LOG_DIR = os.path.join(ROOT, 'logs')


def _log(msg):
    line = time.strftime('%H:%M:%S ') + str(msg)
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, 'nx_worker.log'), 'a', encoding='utf-8') as fp:
            fp.write(line + '\n')
    except Exception:
        pass


def main():
    try:
        from nx_worker import handlers, server
        from nx_worker import dispatch  # noqa: F401  (registers undo commands)
        handlers.load_all()
        for name, err in handlers.LOAD_ERRORS.items():
            _log('handler load error %s: %s' % (name, err))
        host = os.environ.get('NX_MCP_HOST', '127.0.0.1')
        port = int(os.environ.get('NX_MCP_PORT', '8765'))
        token = os.environ.get('NX_MCP_TOKEN', '')
        server.serve(host, port, token, _log)
    except Exception:
        _log('fatal: ' + traceback.format_exc())
        raise


if __name__ == '__main__':
    main()
