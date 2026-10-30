# -*- coding: utf-8 -*-
'''Explicit workspace for resolving relative paths.

Priority: absolute path > workspace set by nx_set_workspace > env NX_MCP_WORKSPACE.
Without a workspace a relative path is an error (never falls back to the process cwd).
'''
import os

from nx_worker import ctx
from nx_worker.registry import command

STATE = {'workspace': None}


def current_workspace():
    ws = STATE['workspace'] or os.environ.get('NX_MCP_WORKSPACE') or ''
    ws = str(ws).strip()
    return os.path.abspath(os.path.expanduser(ws)) if ws else None


def resolve_path(path):
    if path is None or not str(path).strip():
        raise ctx.NxError('path 不能为空')
    p = os.path.expanduser(str(path).strip())
    if os.path.isabs(p):
        return os.path.abspath(p)
    ws = current_workspace()
    if not ws:
        raise ctx.NxError('相对路径 %r 无法解析：未设置工作区。请先调用 nx_set_workspace，或使用绝对路径，或设置环境变量 NX_MCP_WORKSPACE' % path)
    return os.path.abspath(os.path.join(ws, p))


@command('set_workspace', 'session')
def set_workspace(path, create=False):
    p = os.path.abspath(os.path.expanduser(str(path)))
    if not os.path.isdir(p):
        if not create:
            raise ctx.NxError('目录不存在: %s（可设置 create=true 自动创建）' % p)
        os.makedirs(p, exist_ok=True)
    STATE['workspace'] = p
    return {'workspace': p}


@command('get_workspace', 'read')
def get_workspace():
    ws = current_workspace()
    source = 'tool' if STATE['workspace'] else ('env' if ws else None)
    return {'workspace': ws, 'source': source}
