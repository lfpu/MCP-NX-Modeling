Copilot said:
项目概况
项目名称：MCP-NX-Modeling
目标：用 Python 实现 Siemens NX 建模 MCP 服务，供 AntCode、Claude Code 等客户端调用。
运行环境：
Siemens NX 2412
NX 内置 Python 3.11
系统 Python 3.12
MCP Python SDK 2.3.0
架构：
main.py 和 nx_mcp/ 是 MCP Server，运行在系统 Python 中。
nx_worker/ 通过 run_journal.exe 启动，常驻在 NX 内部。
两者通过 TCP 127.0.0.1:8765 通信，所以不用每次调用 Tool 都重启 NX。
对象 ID：使用基于 NX Tag 的 FACE_123、EDGE_45、BODY_7、FEATURE_8，只在当前 NX 会话中有效。
当前状态：共 64 个 Worker 命令、62 个 MCP Tool。
examples/smoke_test.py 已通过。
examples/smoke_advanced.py 13 项全部通过。
examples/smoke_assembly.py 已通过。
AntCode 已能正常调用该服务。
已完成的工作

基础架构

已完成 MCP Server、TCP Client、Worker、命令分发、Handler 注册和 Worker 自动拉起。
Phase 0 的 NXOpen 验证已完成。
建模操作带 Undo Mark：失败时回滚，nx_undo_last 最多保留 20 步。
危险操作必须传 confirm=true。

Phase 1–7

Part 管理：状态、新建、打开、保存、另存、关闭。
基本体素：长方体、圆柱、圆锥、球。
查询：Part、Body、特征树、表达式、面、边、对象详情、当前选择。
草图：直线、矩形、圆、圆弧、折线。
特征：拉伸、切除、旋转、4 种孔、布尔、圆角、倒斜角、基准面、修改表达式、孔阵列坐标。
几何选择：可按类型、法向、面积、半径、范围、距离、最外侧等条件筛选，也能查询相邻面。筛选在 Worker 里完成，以减少 Token 消耗。
装配：添加组件、读取组件、平移组件。

本次新增

工作区：新增 nx_set_workspace 和 nx_get_workspace。相对路径只相对工作区解析；没有工作区时直接报错，不再回退到 cwd。
高阶特征：抽壳、线性特征阵列、镜像实体、抑制与解抑制、重命名、基准轴。
草图：可以在已有平面上建草图，在其上拉伸和切除已验证。
测量：体积、表面积、质心、距离；面到面距离使用 NX 精确测量。
导入导出：支持 STEP、IGES、STL 导出和 STEP 导入。
装配：新增 nx_component_faces 和 nx_add_constraint。约束类型包括固定、接触、同心、距离、平行、垂直、角度，其中只实测了固定和贴合。
工程图：新建图纸、基本视图、投影视图、导出 PDF。
几何校验：例如抽壳体积为 22428 mm³；装配贴合后板件底面 z = 10.0000。
README：已更新实测状态和开发经验。

NX 2412 兼容处理

NXOpen.Utilities 和 NXOpen.Assemblies 改为可选导入。
Tag 解析优先使用 TaggedObjectManager.GetTaggedObject()。
当枚举显示为数字时，通过枚举名反查和几何判断兜底。
包围盒改为用边顶点计算。
平面法向优先使用 AskFaceData，否则用顶点兜底。
Builder 属性名用 probe_api*.py 探测后再写代码。
关键文件与说明

MCP 层

main.py：服务入口。
nx_mcp/server.py：兼容 MCP 2.x 的 MCPServer 和 1.x 的 FastMCP。
nx_mcp/client.py：TCP 转发、错误处理、自动拉起 Worker。
nx_mcp/config.py：配置。
nx_mcp/tools/：各类 Tool。本次新增 workspace_tools、advanced_tools、mirror_tools、pattern_feature_tools、assembly_constraint_tools、drawing_tools。

Worker 层

nx_worker/main.py、server.py、dispatch.py、registry.py：Worker 入口、TCP 服务、命令分发和注册。
ctx.py：Session、Part、Undo、Tag 解析等公共上下文。
geom.py：几何信息提取和兼容处理。
nx_worker/handlers/：具体 NXOpen 操作。
本次新增：workspace、feat_adv、measure、exchange、mirror、pattern、assembly_cons、drawing。
debug.py 中包含 API 探针。

测试与脚本

examples/smoke_test.py：基础零件冒烟测试。
examples/smoke_advanced.py：高阶功能冒烟测试，输出到 examples/output/adv/。
examples/smoke_assembly.py：装配冒烟测试，输出到 examples/output/asm/。
scripts/check_registry.py：检查 Tool 与 Handler 的名称和参数是否一致。
scripts/list_tools.py：不启动 NX，只验证 Tool 注册。
scripts/probe_api*.py：NX API 探针。
scripts/start_worker.ps1、scripts/stop_worker.py：启动和停止 Worker。

日志

logs/nx_worker.log、logs/run_journal.log：排查问题的主要日志。
logs/probe*.txt：探针输出。

其他

.mcp.json.example：MCP 客户端配置示例。
shuriken.prt：位于根目录，是早期 cwd 路径问题的遗留文件，可以清理。
约定与用户偏好
只针对 NX 2412 做兼容，依据真实日志和探针结果修复，不假设 API 名称。
探针输出要先写入文件再读取。没读到结果时不能声称已确认，要明确区分事实和推断。
多步任务用 Todo 分阶段推进，同一时间只能有一项 in_progress。
每次修改后都要运行 compileall、check_registry，并跑实机冒烟测试。
修改 nx_worker/ 后，必须先停掉旧 Worker 再验证。
沿用现有架构，不引入无关抽象。
路径规则：
解析优先级为：绝对路径 > 工作区 > NX_MCP_WORKSPACE。
不回退到 cwd。
返回结果中使用规范化的绝对路径。
文件操作的语义要明确：
open_part(path) 和 save_part_as(path) 必须提供路径。
save_part() 保存回原路径。
冒烟测试的期望值要认真计算，避免把期望值算错误判为代码问题。
未完成 / 下一步

AntCode 联调

在 AntCode 的 MCP 配置中把 NX_MCP_WORKSPACE 注入为项目根目录。
端到端验证新增 Tool：让 AI 做一个带孔、圆角、抽壳的零件，再出工程图并导出 PDF。

待补测

装配约束：同心、距离、平行、垂直、角度。
圆形阵列和网格阵列。
STEP 导入。
倒斜角、旋转。
撤销和危险操作确认。

待完善

移除 smoke_test.py 中的大段调试输出。
完善 README 中的使用示例。

已知限制

孔通过布尔减实现，不是原生 Hole Feature。
草图没有约束和尺寸标注。在面上建草图时使用的是由该面生成的基准平面，与面不关联，面改动后草图不会跟着变。
尚未实现：拔模、剖视图、尺寸标注。
Worker 单线程，请求串行处理。
曲面包围盒是估算值。
返回中的 units: "1" 是 NX 枚举显示问题，只影响可读性。
