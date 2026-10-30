# -*- coding: utf-8 -*-
'''Auto-load every handler module. A broken module is reported in LOAD_ERRORS instead of killing the worker.'''
import importlib
import os
import pkgutil

LOAD_ERRORS = {}


def load_all():
    pkg_dir = os.path.dirname(os.path.abspath(__file__))
    for m in pkgutil.iter_modules([pkg_dir]):
        try:
            importlib.import_module(__name__ + '.' + m.name)
        except Exception as exc:
            LOAD_ERRORS[m.name] = '%s: %s' % (type(exc).__name__, exc)
