# -*- coding: utf-8 -*-
from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description=(
        '设置工作区目录。之后 nx_new_part / nx_open_part / nx_save_part_as / 导入导出 / nx_add_component 等的相对路径都相对该目录解析。'
        '路径优先级：绝对路径 > 本工具设置的工作区 > 环境变量 NX_MCP_WORKSPACE；都没有时相对路径会报错。create=true 时自动创建目录。'))
    def nx_set_workspace(path: str, create: bool = False) -> dict:
        return run('set_workspace', path=path, create=create)

    @mcp.tool(description='查看当前工作区目录及其来源（tool / env / 未设置）。')
    def nx_get_workspace() -> dict:
        return run('get_workspace')
