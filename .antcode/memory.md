Copilot said:
项目概况
项目名称：MCP-NX-Modeling
目标：使用 Python 构建 Siemens NX 建模 MCP 服务，供 AntCode、Claude Code 等客户端通过自然语言执行零件建模、几何查询、装配约束、工程图及格式转换。
运行环境：
Siemens NX 2412
NX 内置 Python 3.11
系统 Python 3.12
MCP Python SDK 2.3.0
架构：
main.py、nx_mcp/：运行于系统 Python 的 MCP Server。
nx_worker/：通过 run_journal.exe 启动，常驻 NX 内部。
MCP Server 通过 TCP 127.0.0.1:8765 调用 Worker，复用 NX 会话。
Worker 单线程串行处理命令。
对象 ID：使用 FACE_123、EDGE_45、BODY_7、FEATURE_8 等 NX Tag ID，仅在当前 NX 会话有效。
仓库：已初始化 Git，并推送至公开仓库 lfpu/MCP-NX-Modeling，默认分支 main。
当前状态：原计划 9 项工作已全部完成。最终统计为 77 个 Worker 命令、64 个 MCP Tool，未暴露命令均为预期的 debug_* 探针。
已完成的工作
核心能力
已完成 MCP Server、TCP Client、NX Worker、自动启动、Token 校验、注册分发及 NX 会话复用。
建模操作支持 Undo Mark 和失败回滚；nx_undo_last 最多保留最近 20 步。
删除对象、放弃修改等危险操作要求 confirm=true。
支持 Part 新建、打开、保存、另存、关闭、工作区管理和状态查询。
支持长方体、圆柱、圆锥、球、草图、拉伸、切除、旋转、布尔、圆角、倒斜角、抽壳、镜像、阵列、基准面/轴、特征抑制和重命名。
支持 Body、特征树、表达式、面、边、选择集、相邻面、体积、面积、质心和距离查询。
支持组件添加、平移、面查询，以及 fix、touch、concentric、distance、parallel、perpendicular、angle 装配约束。
支持工程图纸、基本视图、投影视图和 PDF 导出。
支持 STEP、IGES、STL 导出及 STEP 导入。
原生孔

新增 nx_hole_native：

已实测 Simple Through、Simple Blind、Counterbored、Countersink。
均生成原生 NX HOLE PACKAGE。
支持 through、depth、沉孔和锥形沉孔参数。
原生接口失败时默认回退到布尔减孔；fallback=false 可禁止回退。
D10 贯穿 20 mm 实体时移除体积为 1570.7963 mm³，与理论值一致。
草图约束与尺寸

新增：

nx_sketch_add_constraint
nx_sketch_add_dimension

约束支持：

horizontal、vertical、fixed
coincident、tangent
parallel、perpendicular、concentric

尺寸支持：

horizontal、vertical
parallel、perpendicular、angular
radius、diameter

实现要点：

添加约束/尺寸前激活草图，完成后执行 LocalUpdate 和 Deactivate。
长度使用毫米单位 NX 系统表达式。
角度输入按度接收，内部使用弧度表达式。
几何通过从 0 开始的 geometry_index 引用。
水平、垂直、重合、水平长度、垂直长度、半径和直径已在 NX 2412 实测通过。
阵列与格式转换
nx_pattern_feature 已支持线性、网格和圆形阵列。
3×2 网格阵列实测生成 6 个 Body。
360° 四实例圆形阵列实测生成 4 个 Body。
STEP 导出修复为 ExistingPart + InputFile + ProcessHoldFlag。
STEP 导入最终采用：
ImportTo=NewPart
FileOpenFlag=true
ProcessHoldFlag=true
对导入后当前工作 Part 执行 SaveAs(output_part)
STEP 导出再导入回环通过，导入前后体积均为 9216 mm³。
倒斜角实测通过。
360° 旋转实测通过，体积为 14074.3351 mm³。
验证结果
examples/smoke_test.py：基础零件测试通过。
examples/smoke_advanced.py：13/13 通过。
examples/smoke_assembly.py：fix + touch 通过，板件底面为 z=10.0000。
examples/smoke_native.py：原生孔、草图约束与尺寸、网格/圆形阵列通过。
scripts/test_remaining_features.py：倒斜角、旋转、STEP 回环通过。
scripts/test_assembly_constraints.py：平行、垂直、距离、角度、同心约束均提交并保存成功。
最终 compileall 与 scripts/check_registry.py 均通过。
关键文件与说明
main.py：MCP 服务入口。
nx_mcp/server.py：兼容 MCP 2.x MCPServer 和 MCP 1.x FastMCP。
nx_mcp/client.py：TCP 调用、错误处理和 Worker 自动启动。
nx_mcp/config.py：NX 路径、端口、Token、工作区及自动启动配置。
nx_mcp/tools/：按 Part、草图、特征、阵列、装配、工程图等分类的 MCP Tool。
nx_worker/ctx.py：Session、Part、Undo、Tag 解析和公共上下文。
nx_worker/geom.py：几何提取及 NX 2412 兼容逻辑。
nx_worker/handlers/feat_hole.py：布尔孔和原生 HOLE PACKAGE。
nx_worker/handlers/sketch.py：草图几何、约束和尺寸。
nx_worker/handlers/pattern.py：线性、网格和圆形特征阵列。
nx_worker/handlers/exchange.py：STEP/IGES/STL 导入导出，包含 NX 2412 批处理兼容修复。
nx_worker/handlers/assembly_cons.py：装配约束。
nx_worker/handlers/debug.py：NX API 实机探针命令，不对 MCP 客户端暴露。
scripts/probe_api*.py、probe_step_*.py：NX 2412 API 探针。
scripts/check_registry.py：检查 Tool、Handler 及参数签名一致性。
scripts/stop_worker.py：修改 Worker 后停止旧进程。
README.md：已更新新增 Tool、实测矩阵、STEP 导入机制、已知限制及最终验证命令。
约定与用户偏好
以 NX 2412 实机探针和日志为准，不猜测 API。
不确定属性或签名时，先写探针，将完整结果保存到 logs/ 后再实现。
修改 nx_worker/ 后必须先停止旧 Worker，避免测试旧代码。
每轮修改后运行：
python -m compileall ...
python scripts/check_registry.py
对应 NX 实机测试
多步骤任务使用 Todo，且同一时间最多一项 in_progress。
用户偏好直接修改并验证，不希望只给设计方案或后台任务。
保持“MCP Server + 常驻 NX Worker”架构，不引入无关抽象。
路径解析顺序：绝对路径 > 显式工作区 > NX_MCP_WORKSPACE，不回退到当前目录。
测试必须校验真实几何、位置、Body 数量或体积，不能只检查命令未报错。
.gitignore 应继续忽略生成的 Part、日志、缓存、虚拟环境和 .antcode/。
未完成 / 下一步

当前既定任务已全部完成，后续可按优先级继续：

新增建模能力
拔模。
剖视图。
工程图尺寸与标注。
原生孔的 Until Next、Until Selected 等更多深度方式。
增强草图接口
提供更稳定的几何查询与索引映射，减少 GetAllGeometry() 顺序变化的影响。
补测相切、平行、垂直、同心、固定和角度尺寸的更多组合。
装配验证
增加多约束组合、过约束和欠约束诊断。
求解后自动返回关键位置、方向和距离校验。
兼容与质量
面上草图目前通过固定基准平面创建，尚不与原面参数化关联。
曲面包围盒主要为边顶点估算，复杂曲面应结合 NX 精确测量。
NX Tag ID 在 Worker 重启或 Part 重开后失效，需重新查询。
可清理或归档大量临时探针脚本、日志和重复测试产物，但保留最终回归脚本。
