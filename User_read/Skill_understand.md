1. 阶段 4/5 循环怎么运作——不是每个 issue 都要过 qa+triage
我把这两个 skill 的实际代码翻出来看了，结论是：从 /to-issues 拆出来的 issue 不需要再过 /qa 和 /triage。

/qa：给"用户口头描述一个问题"这种场景用的——你说"这里怪怪的"，它帮你澄清、探查代码、写成规范的 GitHub issue。它解决的是"问题还没被结构化"这个痛点。
/triage：给"issue 已经存在但状态不明"的场景用的状态机——needs-triage → needs-info / ready-for-agent / ready-for-human / wontfix。它的价值在于把一个含糊的 issue 送到 ready-for-agent 状态。
而 /to-issues 产出的 issue，本身在生成的那一刻就已经是 ready-for-agent——vertical slice 的定义就是"贯穿全链路、agent 能独立认领"。让它再走一遍 triage 状态机是绕圈子，因为 triage 存在的意义（把不清楚的 issue 弄清楚）在这里已经被 /to-issues 做完了。

真实的循环是两条进入阶段 5 的车道：


车道 A（计划内）：/to-prd → /to-issues → 直接进阶段 5（/tdd → /review）
车道 B（计划外）：真实用户报 bug / 你自己发现问题 → /qa（写成 issue）→ /triage（判断状态）→ 若 ready-for-agent → 进阶段 5
我之前那张图把"阶段 4"画成必经关卡，不准确——应该是旁路进入点，只服务于计划外冒出来的东西（真实 bug、临时想法），不是每个 issue 的必经流程。抱歉，这个我改正。

2. 完整 skill 对照表
先说一个重要提醒：截图里的仓库比你本地实际装的版本新——commit 显示上游已经把 to-prd/to-issues 合并重命名成 to-spec/to-tickets，setup-matt-pocock-skills 改名 ask-matt，还多了 codebase-design、diagnosing-bugs、domain-modeling、implement、prototype、research、resolving-merge-conflicts、wayfinder 这些我还没读过源码的新 skill。下表只列你本地实际安装、我已读过源码确认行为的这批（用你现在能打的斜杠命令）：

Skill	输入	输出	用在什么时候
/grill-me	一个粗糙的想法/计划	访谈问答文档（如 Grill_Questions.md）	代码写之前，想把产品/设计决策逼问清楚，不需要同步维护 CONTEXT.md
/grill-with-docs	同上，但仓库里已有代码/CONTEXT.md	同上访谈 + 实时写入 CONTEXT.md/docs/adr/	已经有代码骨架、想在讨论的同时把术语和决策沉淀下来
/to-prd	已有对话上下文 + 代码库	一份结构化 PRD，发布到 issue tracker	决策已经定型，要把它变成可执行的规格文档（不重新访谈）
/to-issues	一份 PRD/plan	若干 vertical-slice issue，标 HITL/AFK，带依赖关系	PRD 写完后，把它切成能独立认领的小任务
/qa	用户口头描述的 bug/问题	规范化的 GitHub issue（可能拆成多个）	有人（用户/你自己）随口报告一个问题，需要转成正式 issue
/triage	一个或多个 issue	状态标签 + 下一步动作（agent brief / 需要更多信息 / 不予处理）	有 issue 堆积、状态不明，需要决定谁该处理、什么时候处理
/tdd	一个已认领的 issue	red-green-refactor 循环产出的代码 + 测试	实际写一个 vertical slice 的功能代码
/diagnose	一个难 bug 或性能回归	复现脚本 + 根因假设验证 + 修复 + 回归测试	bug 不好找、不是"看一眼就知道哪错了"的那种
/review	一段 diff + fixed point（commit/branch）	Standards 轴 + Spec 轴两份并行报告	一个 issue 的代码写完，合并前做审查
/request-refactor-plan	一个重构想法	tiny-commit 计划，发布成 issue	想做的不是新功能而是纯重构，需要先规划安全的小步提交
/improve-codebase-architecture	现有代码库 + CONTEXT.md/ADR	HTML 报告：架构改善候选项（浅模块→深模块）	阶段性回头看，不针对单个 issue，找"哪里该重构"的系统性机会
/setup-matt-pocock-skills	仓库现状	CLAUDE.md + docs/agents/*.md	仓库第一次接入这套 skill 体系时，一次性配置
一句话区分容易混淆的几组：

/grill-me vs /grill-with-docs：只差"要不要顺手维护 CONTEXT.md"。
/to-prd vs /request-refactor-plan：前者是"要做新东西"，后者是"要重构已有东西"——模板都类似（Problem/Solution/Decisions/Testing/Out of Scope），但 refactor 版多了"tiny commits 计划"这个核心要求。
/qa vs /triage：qa 负责"把口头问题写成 issue"，triage 负责"决定这个 issue 现在该怎么办"。
/diagnose vs /tdd：diagnose 是找 bug 根因，tdd 是写新行为——diagnose 修完 bug 后才会用 tdd 风格补回归测试。
/review vs /improve-codebase-architecture：review 针对一次 diff，问"这次改得对不对";improve-codebase-architecture 针对整个代码库当下状态，问"结构该不该改"，不针对某次 diff。
3. /to-prd 该拆多大——不是按前后端拆，是按里程碑拆
你问"要不要一次只拆 backend"——这正是 /to-issues 源码里明确警告要避免的**horizontal slice（横切）**反模式：

Each slice delivers a narrow but COMPLETE path through every layer (schema, API, UI, tests)... NOT a horizontal slice of one layer.

按前端/后端拆等于按"层"横切，会导致做完"backend PRD"这一整块之后，前端还完全没有对应实现去验证它——你没法真正 demo 或验证任何东西，这正是 tdd skill 里"不要写完所有测试再写所有实现"同一个道理的反面版本。

正确粒度是按你 Plan_v1.md 里已经写好的里程碑（M1/M2/M3）拆，因为"里程碑"这个单位天然就是端到端的（Set Goal + Topic + 粘贴 Material → 提取 → 确认 → 两种复习模式 → 存档 → mini map，这条链路本来就同时涉及 FastAPI 后端和 Next.js 前端）：

/to-prd 只针对 M1（核心循环） 跑一次，产出一份"M1 PRD"，而不是把 M1+M2+M3 全部塞进一份 PRD。
/to-issues 把这份 M1 PRD 切成 5～10 个 vertical slice，每一个 issue 都会同时touch FastAPI 端点 + Next.js 页面/组件 + 数据库 + 测试——比如"用户粘贴一段 Material，看到提取出的 Concepts 并能确认"就是一个天然的 vertical slice，它逼着你在一个 issue 里就把某个 FastAPI 路由和对应 Next.js 页面都连通。
M1 全部 issue 做完、能跑通核心循环了，再回到 /to-prd 处理 M2，如此往复。
这样每个 issue 完成后都是"可演示、可验证"的一小步，而不是做完一整个 backend 之后才第一次看到东西真的动起来。