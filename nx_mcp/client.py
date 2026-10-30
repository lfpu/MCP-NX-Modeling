# -*- coding: utf-8 -*-
'''TCP client for the NX worker. Auto-starts the worker with run_journal.exe when it is not running.
NOTE: stdout is the MCP protocol channel, never print() here.'''
import itertools
import json
import os
import socket
import subprocess
import threading
import time

from nx_mcp import config


class NxWorkerError(Exception):
    pass


_lock = threading.Lock()
_ids = itertools.count(1)
_proc = {'p': None}


def _roundtrip(payload, timeout=None):
    with socket.create_connection((config.HOST, config.PORT), timeout=5) as s:
        s.settimeout(timeout or config.CALL_TIMEOUT)
        s.sendall((json.dumps(payload, ensure_ascii=False) + '\n').encode('utf-8'))
        buf = b''
        while not buf.endswith(b'\n'):
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
    if not buf:
        raise NxWorkerError('NX worker 没有返回数据（连接被关闭）')
    return json.loads(buf.decode('utf-8'))


def _ping():
    try:
        resp = _roundtrip({'id': 0, 'cmd': 'ping', 'token': config.TOKEN}, timeout=10)
        return resp.get('ok', False)
    except OSError:
        return False


def start_worker():
    exe = config.find_run_journal()
    if not exe:
        raise NxWorkerError('找不到 run_journal.exe，请设置环境变量 NX_MCP_NXBIN（例如 C:/Program Files/Siemens/NX2412/NXBIN）')
    script = os.path.join(config.ROOT, 'nx_worker', 'main.py')
    env = dict(os.environ)
    env['NX_MCP_ROOT'] = config.ROOT
    env['NX_MCP_HOST'] = config.HOST
    env['NX_MCP_PORT'] = str(config.PORT)
    env['NX_MCP_TOKEN'] = config.TOKEN
    if not env.get('UGII_BASE_DIR'):
        env['UGII_BASE_DIR'] = os.path.dirname(os.path.dirname(exe))
    os.makedirs(config.LOG_DIR, exist_ok=True)
    log = open(os.path.join(config.LOG_DIR, 'run_journal.log'), 'ab')
    flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    _proc['p'] = subprocess.Popen([exe, script], env=env, stdout=log, stderr=log, stdin=subprocess.DEVNULL, creationflags=flags)
    deadline = time.time() + config.START_TIMEOUT
    while time.time() < deadline:
        if _ping():
            return
        if _proc['p'].poll() is not None:
            raise NxWorkerError('NX worker 启动后立即退出（退出码 %s），详见 logs/run_journal.log 与 logs/nx_worker.log' % _proc['p'].returncode)
        time.sleep(1.0)
    raise NxWorkerError('等待 NX worker 启动超时（%d 秒），请检查 NX 许可证' % config.START_TIMEOUT)


def ensure_worker():
    if _ping():
        return
    if not config.AUTOSTART:
        raise NxWorkerError('NX worker 未运行（%s:%d），请先运行 scripts/start_worker.ps1' % (config.HOST, config.PORT))
    start_worker()


def call(cmd, **params):
    '''Send a command to the worker and return its result dict.'''
    params = {k: v for k, v in params.items() if v is not None}
    with _lock:
        ensure_worker()
        resp = _roundtrip({'id': next(_ids), 'cmd': cmd, 'params': params, 'token': config.TOKEN})
    if not resp.get('ok'):
        err = resp.get('error') or {}
        raise NxWorkerError(err.get('message') or 'NX 命令失败: ' + cmd)
    return resp.get('result')


def stop_worker():
    try:
        _roundtrip({'id': 0, 'cmd': 'shutdown', 'token': config.TOKEN}, timeout=10)
    except OSError:
        pass
