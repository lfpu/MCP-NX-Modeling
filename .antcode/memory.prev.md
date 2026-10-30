Copilot said:
项目概况
项目名称：MCP-NX-Modeling
目标：使用 Python 构建 Siemens NX 建模 MCP 服务，供 AntCode、Claude Code 等客户端通过自然语言调用 NX 完成建模、查询、装配、工程图和格式导入导出。
运行环境：
Siemens NX 2412
NX 内置 Python 3.11
系统 Python 3.12
MCP Python SDK 2.3.0
架构：
main.py、nx_mcp/：运行于系统 Python 的 MCP Server。
nx_worker/：由 run_journal.exe 启动并常驻 NX 内部。
MCP Server 通过 TCP 127.0.0.1:8765 调用 Worker，避免每次 Tool 调用都重启 NX。
对象标识：使用 FACE_123、EDGE_45、BODY_7、FEATURE_8 等 NX Tag ID，仅在当前 NX 会话有效。
代码仓库：已初始化 Git，并推送到公开 GitHub 仓库 lfpu/MCP-NX-Modeling，默认分支为 main。
当前状态：基础建模、高阶特征、查询选择、装配、工程图、测量和格式转换链路已经建立，AntCode 已能正常连接和调用。
已完成的工作
核心架构
完成 MCP Server、TCP Client、NX Worker、Handler 注册和命令分发。
支持 Worker 自动启动、Token 校验、NX 会话复用和单线程串行执行。
Phase 0 NXOpen 技术验证已通过。
建模操作使用 Undo Mark，失败时回滚；nx_undo_last 最多保留最近 20 步。
删除对象、放弃修改等危险操作要求 confirm=true。
建模与查询

已实现：

Part 新建、打开、保存、另存、关闭和状态查询。
长方体、圆柱、圆锥、球。
直线、矩形、圆、圆弧和折线草图。
拉伸、切除、旋转、布尔、孔、圆角、倒斜角、基准面和表达式修改。
抽壳、线性特征阵列、镜像实体、抑制/解抑制、重命名和基准轴。
Body、特征树、表达式、面、边、对象信息和当前选择查询。
按几何条件筛选面/边，以及查询相邻面。
体积、表面积、质心和距离测量。
STEP、IGES、STL 导出及 STEP 导入。
装配与工程图
支持添加、读取、平移装配组件。
支持固定、接触/贴合、同心、距离、平行、垂直和角度装配约束。
已实测固定和贴合约束，贴合后板件底面为 z=10.0000。
支持新建图纸、基本视图、投影视图和导出 PDF。
验证情况
examples/smoke_test.py 基础测试已通过。
examples/smoke_advanced.py 13 项全部通过。
examples/smoke_assembly.py 已通过。
已验证抽壳体积为 22428 mm³。
examples/output/ 中保留了 Part、装配、STEP、IGES、STL、PDF 和日志等实测产物。
NX 2412 兼容处理
NXOpen.Utilities、NXOpen.Assemblies 使用可选导入。
Tag 优先通过 TaggedObjectManager.GetTaggedObject() 解析。
针对枚举显示为数字的情况加入名称反查和几何兜底。
包围盒通过边顶点计算，平面法向优先使用 AskFaceData。
NXOpen Builder 的真实属性和方法通过 probe_api*.py 实机探测，不依赖猜测。
README 和使用说明

README.md 已包含面向 AntCode / Claude Code 使用者的完整教程：

环境安装及 NX_MCP_NXBIN 配置。
AntCode、Claude Code 和 .mcp.json.example 配置。
Worker 自动启动机制。
NX_MCP_WORKSPACE、nx_set_workspace 和路径规则。
Part 创建、体素建模、面边查找、打孔、圆角、保存等自然语言示例。
“底板 + 四孔 + R3 圆角 + 工程图 + PDF”端到端 Demo。
Part 修改、撤销、危险操作确认、装配和格式导出示例。
Worker 重启和常见错误排查。

README 当前已经足以指导首次配置和基本使用，但前半部分的开发路线、Tool 清单和状态说明存在过时内容，需要后续统一整理。

关键文件与说明
main.py：MCP 服务入口。
nx_mcp/server.py：兼容 MCP 2.x MCPServer 和 MCP 1.x FastMCP。
nx_mcp/client.py：TCP 调用、错误处理和 Worker 自动启动。
nx_mcp/config.py：NX 路径、端口、Token、工作区和自动启动配置。
nx_mcp/tools/：MCP Tool 定义，按 Part、体素、查询、选择、草图、特征、阵列、装配约束、工程图等分类。
nx_worker/ctx.py：NX Session、Part、Undo、Tag 解析和公共上下文。
nx_worker/geom.py：几何提取及 NX 2412 兼容逻辑。
nx_worker/dispatch.py、registry.py：命令分发和 Handler 注册。
nx_worker/handlers/：具体 NXOpen 实现。
examples/smoke_test.py：基础零件测试。
examples/smoke_advanced.py：高阶功能测试。
examples/smoke_assembly.py：装配测试。
scripts/check_registry.py：检查 MCP Tool、Worker 命令和参数一致性。
scripts/list_tools.py：无需启动 NX 即可检查 Tool 注册。
scripts/start_worker.ps1、stop_worker.py：启动和关闭 Worker。
scripts/probe_api*.py：NX 2412 API 实机探针。
logs/probe*.txt：探针输出。
logs/nx_worker.log、run_journal.log：主要运行日志。
phase0/：NXOpen 技术验证脚本和输出。
images/：README 使用的 MCP 和零件示意图。
约定与用户偏好
以 NX 2412 实机日志和探针结果为准，不猜测其他版本 API。
探针必须将完整输出写入日志并读取后，才能确认接口属性或方法签名。
多步骤任务使用 Todo，且同一时间只能有一项 in_progress。
修改后立即执行 compileall、scripts/check_registry.py 和对应实机冒烟测试。
修改 nx_worker/ 后必须先停止旧 Worker，避免测试旧代码。
保持“MCP Server + 常驻 NX Worker”架构，不引入无关抽象。
路径解析顺序：绝对路径 > 显式工作区 > NX_MCP_WORKSPACE，禁止回退到当前工作目录。
Tool 返回规范化绝对路径。
open_part(path)、save_part_as(path) 必须显式提供路径；save_part() 保存到现有路径。
冒烟测试需要按真实几何、位置和体积校验，避免期望值错误导致误判。
用户偏好直接修改项目并执行验证，不希望只给方案。
.gitignore 应忽略生成的 Part、日志、测试输出、缓存、虚拟环境及整个 .antcode/ 目录。
未完成 / 下一步
第一优先级：补齐原生建模能力
继续基于 probe8.txt、probe9.txt 探测实例对象和真实方法签名。
实现原生 nx_hole_native：
简单孔
沉孔
锥形沉孔
Through Body、Until Next、Until Selected、Value 深度限制
在目标面上正确定位
原生接口失败时可回退到现有布尔减孔
实现草图约束：
水平、垂直、重合、相切、平行、正交、同心、固定
实现草图尺寸：
长度、半径、直径
补全圆形阵列和网格阵列。
新增 examples/smoke_native.py，停止旧 Worker 后执行实机验证。
README 整理
更新过时的 Phase 路线状态。
补齐工程图、测量、工作区、格式转换、装配约束等 Tool 清单。
明确区分：
已实现且实机通过
已实现但尚未完整实机验证
尚未实现
修复损坏的 AntCode 仓库链接。
新功能完成后补入使用教程和端到端 Demo。
待补测与已知限制
补测同心、距离、平行、垂直和角度装配约束。
补测 STEP 导入、倒斜角、旋转、撤销和危险操作确认。
执行 AntCode 建模、保存、工程图及 PDF 导出的完整端到端 Demo。
当前孔主要通过圆柱或圆锥布尔减实现，并非原生 NX Hole Feature。
草图约束和尺寸尚未形成正式 Tool。
面上草图通过目标面生成基准平面，暂不与原面保持关联。
尚未实现拔模、剖视图和工程图尺寸标注。
曲面包围盒仍为顶点估算值。
units: "1" 是 NX 枚举显示问题，仅影响可读性。
把这份项目记忆压缩到 4000 字以内
检查并修正项目记忆中的冲突和过时信息
按优先级重新整理未完成事项
