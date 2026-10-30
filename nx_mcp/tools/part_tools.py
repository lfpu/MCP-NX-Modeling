# -*- coding: utf-8 -*-
from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool()
    def nx_get_status() -> dict:
        '''查询 NX 连接状态、版本、当前工作 Part 和已打开的 Part 列表。会在需要时自动启动 NX worker。'''
        return run('status')

    @mcp.tool()
    def nx_new_part(path: str, units: str = 'mm', overwrite: bool = False) -> dict:
        '''新建 Part 并设为工作 Part。path 为 .prt 完整路径；units 为 mm 或 inch；已存在的文件默认不覆盖。'''
        return run('new_part', path=path, units=units, overwrite=overwrite)

    @mcp.tool()
    def nx_open_part(path: str) -> dict:
        '''打开已有 .prt 文件并设为工作 Part。'''
        return run('open_part', path=path)

    @mcp.tool()
    def nx_save_part() -> dict:
        '''保存当前工作 Part。'''
        return run('save_part')

    @mcp.tool()
    def nx_save_part_as(path: str, overwrite: bool = False) -> dict:
        '''将当前工作 Part 另存为新路径。'''
        return run('save_part_as', path=path, overwrite=overwrite)

    @mcp.tool()
    def nx_close_part(save: bool = True) -> dict:
        '''关闭当前工作 Part。默认先保存；save=false 且有未保存修改时会拒绝。'''
        return run('close_part', save=save)

    @mcp.tool()
    def nx_close_part_discard(confirm: bool = False) -> dict:
        '''【危险】关闭当前 Part 并放弃未保存的修改。必须先征得用户同意，再以 confirm=true 调用。'''
        return run('close_part_discard', confirm=confirm)

    @mcp.tool()
    def nx_undo_last() -> dict:
        '''撤销最近一次成功的建模操作（最多保留最近 20 步）。'''
        return run('undo_last')

    @mcp.tool()
    def nx_undo_history() -> dict:
        '''列出当前可撤销的操作（由旧到新）。'''
        return run('undo_history')
