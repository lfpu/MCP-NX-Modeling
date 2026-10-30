# -*- coding: utf-8 -*-
'''Command registry. Levels: read / session / modify / dangerous.

- read      : only query, no undo mark
- session   : file/session level operations (new/open/save/close), no undo mark
- modify    : changes the model, wrapped in an Undo Mark (auto rollback on failure)
- dangerous : like modify, but requires confirm=true
'''

COMMANDS = {}
LEVELS = ('read', 'session', 'modify', 'dangerous')


def command(name, level='modify'):
    if level not in LEVELS:
        raise ValueError('bad level: ' + level)

    def deco(fn):
        COMMANDS[name] = {'fn': fn, 'level': level}
        return fn

    return deco
