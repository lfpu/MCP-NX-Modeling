# -*- coding: utf-8 -*-
from typing import List, Optional, Union

from nx_mcp.tools._common import run

PointOrId = Union[str, List[float]]


def register(mcp):
    @mcp.tool(description='抽壳：删除 faces 指定的面（开口），其余壁厚为 thickness。faces 为 FACE id 列表，可先用 nx_find_faces 查找（如 extreme="top"）。')
    def nx_shell(faces: List[str], thickness: float) -> dict:
        return run('shell', faces=faces, thickness=thickness)

    @mcp.tool(description='创建固定基准轴。origin 为轴上一点，direction 为方向 [x,y,z]。')
    def nx_create_datum_axis(origin: List[float], direction: List[float]) -> dict:
        return run('create_datum_axis', origin=origin, direction=direction)

    @mcp.tool(description='抑制（suppress=true）或解抑制（false）一个特征，并更新模型。feature 为 FEATURE id。')
    def nx_suppress_feature(feature: str, suppress: bool = True) -> dict:
        return run('suppress_feature', feature=feature, suppress=suppress)

    @mcp.tool(description='重命名对象（特征/实体/草图等），便于之后识别。')
    def nx_rename_object(object_id: str, name: str) -> dict:
        return run('rename_object', object_id=object_id, name=name)

    @mcp.tool(description='实体的体积（mm^3）、表面积（mm^2）和质心。body 省略时用唯一的实体；假定 Part 单位为毫米。')
    def nx_mass_properties(body: Optional[str] = None) -> dict:
        return run('mass_properties', body=body)

    @mcp.tool(description='测量距离。a、b 同为 [x,y,z] 坐标点，或同为对象 id（FACE/EDGE/BODY）。NX 精确测量失败时会退化为包围盒中心距离并给出 warning。')
    def nx_measure_distance(a: PointOrId, b: PointOrId) -> dict:
        return run('measure_distance', a=a, b=b)

    @mcp.tool(description='导出当前显示 Part 为 STEP（.stp）。相对路径相对工作区。已存在的文件默认不覆盖。')
    def nx_export_step(path: str, overwrite: bool = False) -> dict:
        return run('export_step', path=path, overwrite=overwrite)

    @mcp.tool(description='导出当前显示 Part 为 IGES（.igs）。')
    def nx_export_iges(path: str, overwrite: bool = False) -> dict:
        return run('export_iges', path=path, overwrite=overwrite)

    @mcp.tool(description='把 STEP 文件导入成一个新的 .prt（output_part）。导入后用 nx_open_part 打开。')
    def nx_import_step(path: str, output_part: str, overwrite: bool = False) -> dict:
        return run('import_step', path=path, output_part=output_part, overwrite=overwrite)
