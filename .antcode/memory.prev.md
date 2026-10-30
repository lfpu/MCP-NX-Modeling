Copilot said:
项目概况
项目名称：MCP-NX-Modeling
目标：用 Python 实现可供 AntCode、Claude Code 等客户端调用的 Siemens NX 建模 MCP 服务。
当前环境：
Siemens NX 2412
NX 内置 Python 3.11
系统 Python 3.12
MCP Python SDK 2.3.0
架构：
main.py / nx_mcp/：运行在系统 Python 中的 MCP Server。
nx_worker/：通过 run_journal.exe 启动并常驻于 NX 内部。
MCP Server 通过本地 TCP 127.0.0.1:8765 调用 NX Worker。
此设计避免每次 Tool 调用都重新启动 NX。
对象标识：使用 FACE_123、EDGE_45、BODY_7、FEATURE_8 等基于 NX Tag 的 ID，仅在当前 NX 会话内有效。
状态：Phase 0 至 Phase 7 已实现。语法检查、Tool/Worker 注册一致性检查以及基础零件冒烟测试已通过，但大部分高级 NX Tool 尚未逐项实机验证。
已完成的工作
基础架构与 Phase 0
完成 MCP Server、TCP Client、NX Worker、命令分发、Handler 注册及自动启动机制。
完成 Phase 0 NXOpen 技术验证，生成：
phase0/output/phase0_block.prt
phase0/output/result.json
Worker 未运行时，MCP 层可通过 NX run_journal.exe 自动拉起。
建模操作使用 Undo Mark，失败时回滚；nx_undo_last 最多保留最近 20 步。
删除对象、放弃修改并关闭 Part 等危险操作要求 confirm=true。
Phase 1 至 Phase 7
Part 管理：状态、新建、打开、保存、另存、关闭。
基本体素：长方体、圆柱、圆锥、球。
模型查询：Part 信息、Body、特征树、表达式、面、边、对象详情、NX 界面当前选择。
草图与特征：
直线、矩形、圆、圆弧、折线
拉伸、切除、旋转
通孔、盲孔、沉头孔、锥形沉孔
高级特征：布尔运算、圆角、倒斜角、基准面、修改表达式、孔阵列坐标生成。
几何选择：
按类型、法向、方向、面积、半径、范围、距离和最外侧等条件筛选面或边
查询相邻面
主要在 Worker 的 Python 层筛选，只返回少量结果，减少 LLM Token 消耗
装配：添加组件、读取组件、平移组件。
共实现约 38 个 Worker 命令和 40 处 MCP Tool 调用。
scripts/check_registry.py 已验证 Tool 名称、Worker 命令和参数一致。
针对输出过长问题，将 Feature Handler 拆为：
feat_sweep.py
feat_hole.py
feat_edge.py
feat_misc.py
NX 2412 兼容修复
NXOpen.Utilities 和 NXOpen.Assemblies 改为可选导入，避免 NX 2412 启动时报错。
对象 Tag 解析优先使用 NXOpen.TaggedObjectManager.GetTaggedObject()，并保留兼容回退。
处理 NX 枚举字符串表现为数字的问题，加入枚举名称反查和几何兜底判断。
NX 2412 的 UF.Modeling 没有 AskBoundingBox，现改用边顶点计算包围盒。
平面法向优先使用 AskFaceData，不可用时通过顶点信息兜底。
Worker 为常驻进程，修改代码后必须重启。已新增 scripts/stop_worker.py，冒烟测试也会先关闭旧 Worker。
冒烟测试结果

python examples/smoke_test.py 已成功完成：

创建 120 × 80 × 15 底板
找到 4 条竖直边
创建 R10 圆角
创建四个 Ø8 通孔
创建一个中央 Ø40 通孔
保存为 examples/output/plate.prt

结果文件已生成，但仍建议在 NX GUI 中人工检查圆角和孔的实际几何形状。

MCP 2.3.0 兼容
nx_mcp/server.py 已兼容：
MCP 2.x：MCPServer
MCP 1.x：回退到 FastMCP
scripts/list_tools.py 已在 MCP 2.3.0 环境运行成功，证明 Tool 可完成注册。
尚需继续验证 AntCode 与 MCP Server 的完整 stdio 握手和实际 Tool 调用。
关键文件与说明
main.py：MCP 服务入口。
nx_mcp/server.py：创建 MCP Server，兼容 MCP 1.x/2.x。
nx_mcp/client.py：TCP 请求转发、错误处理及 Worker 自动启动。
nx_mcp/config.py：服务、Worker 和 NX 路径配置。
nx_mcp/tools/：按 Part、Primitive、Query、Selection、Sketch、Feature、Pattern、Assembly 分类的 MCP Tool。
nx_worker/main.py：NX Journal/Worker 入口。
nx_worker/server.py：TCP Worker 服务。
nx_worker/dispatch.py、registry.py：命令分发与注册。
nx_worker/ctx.py：NX Session、Part、Undo、对象 Tag 解析等公共上下文。
nx_worker/geom.py：几何信息提取、枚举兼容、边面判断和包围盒逻辑。
nx_worker/handlers/：具体 NXOpen 操作。
examples/smoke_test.py：直接调用 Worker 的基础实机验证，不依赖 MCP 客户端。
scripts/check_registry.py：检查 MCP Tool 与 Worker Handler 的名称及参数一致性。
scripts/list_tools.py：不启动 NX，仅测试 MCP Tool 注册。
scripts/probe.py、handlers/debug.py：NX API 探针与调试。
scripts/start_worker.ps1、stop_worker.py：启动和关闭常驻 Worker。
.mcp.json.example：MCP 客户端配置示例。
logs/nx_worker.log、logs/run_journal.log：排查 NX 和 Journal 启动问题的主要日志。
shuriken.prt：当前位于项目根目录，暴露了相对路径依赖当前工作目录的问题。
约定与用户偏好
面向用户当前使用的 NX 2412 做兼容，出现错误后依据真实日志逐项调整，不假设其他版本 API 一定一致。
多步骤开发应使用 Todo 分阶段推进，并在修改后立即执行语法检查、注册检查或实机验证。
优先沿用现有 MCP Server + 常驻 NX Worker 架构，不随意引入无关抽象。
文件操作语义应明确：
open_part(path)：必须提供路径。
save_part()：保存回当前 Part 已有路径。
save_part_as(path)：必须提供目标路径。
new_part：建议要求路径或基于显式工作区解析。
NX Part 路径不应隐式依赖 MCP Server 或 NX Worker 的当前工作目录。
工具返回应始终包含规范化后的绝对路径。
修改 nx_worker/ 后，要先停止旧 Worker 再验证，避免继续运行旧代码。
未完成 / 下一步

优先修复工作区路径机制：

新增显式工作区概念。
建议提供 set_workspace(path)、get_workspace()。
路径解析优先级：绝对路径 > Tool 显式设置的工作区 > NX_MCP_WORKSPACE。
没有工作区时，相对路径应报错，不能回退到 cwd。
AntCode 启动服务时应注入当前项目根目录，如通过 NX_MCP_WORKSPACE 或 ${project} 变量。
检查 new_part、open_part、save_part_as 的全部路径处理。

验证 AntCode 与 MCP 2.3.0 服务的 stdio 连接、Tool 列表获取和实际调用。

分阶段实测高级 Tool：

草图与拉伸
切除、旋转、孔
布尔、倒角、基准面、表达式
撤销和危险操作确认
装配功能

稳定后移除或关闭 smoke_test.py 中的大段调试探针输出。

已知限制：
孔目前通过圆柱或圆锥布尔减实现，不是原生 NX Hole Feature。
草图暂不支持几何约束和尺寸标注，只按精确坐标绘制。
未实现特征阵列、镜像、装配约束、工程图。
Worker 单线程，请求串行处理。
曲面包围盒由顶点估算，对圆孔面和圆角面不完全精确。
返回的 units: "1" 是 NX 枚举数字显示问题，目前仅影响可读性。
