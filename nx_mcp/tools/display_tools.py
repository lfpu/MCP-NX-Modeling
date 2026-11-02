# -*- coding: utf-8 -*-
from typing import List
from nx_mcp.tools._common import run


def register(mcp):
    @mcp.tool(description='给一个或多个实体上色。bodies 为 BODY id 列表；color 为 NX 调色板索引 1~216。apply_to_all_faces=true 时同时覆盖实体各面的颜色；支持撤销。')
    def nx_color_bodies(bodies: List[str], color: int, apply_to_all_faces: bool = True) -> dict:
        return run('color_bodies', bodies=bodies, color=color, apply_to_all_faces=apply_to_all_faces)

    @mcp.tool(description='仅给指定面上色，不改变其他面。faces 为 FACE id 列表，可先用 nx_find_faces 查询；color 为 NX 调色板索引 1~216；支持撤销。')
    def nx_color_faces(faces: List[str], color: int) -> dict:
        return run('color_faces', faces=faces, color=color)
