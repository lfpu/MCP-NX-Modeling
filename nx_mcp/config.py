# -*- coding: utf-8 -*-
import glob
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, 'logs')

HOST = os.environ.get('NX_MCP_HOST', '127.0.0.1')
PORT = int(os.environ.get('NX_MCP_PORT', '8765'))
TOKEN = os.environ.get('NX_MCP_TOKEN', '')
AUTOSTART = os.environ.get('NX_MCP_AUTOSTART', '1') != '0'
START_TIMEOUT = int(os.environ.get('NX_MCP_START_TIMEOUT', '120'))
CALL_TIMEOUT = float(os.environ.get('NX_MCP_CALL_TIMEOUT', '180'))


def find_run_journal():
    cands = []
    hint = os.environ.get('NX_MCP_NXBIN')
    if hint:
        cands.append(os.path.join(hint, 'run_journal.exe'))
    base = os.environ.get('UGII_BASE_DIR')
    if base:
        cands.append(os.path.join(base, 'NXBIN', 'run_journal.exe'))
    pf = os.environ.get('ProgramFiles', 'C:/Program Files')
    cands += sorted(glob.glob(os.path.join(pf, 'Siemens', '*', 'NXBIN', 'run_journal.exe')), reverse=True)
    for c in cands:
        if os.path.isfile(c):
            return c
    return None
