# 记录与材料维护约定 / Record and material ownership

此页是维护职责的统一说明入口；它描述当前行为，不承诺未来同步功能。
This is the canonical maintenance contract for current behavior, not a live-sync promise.

| 对象 / Object | 当前职责 / Current responsibility |
| --- | --- |
| VA | 新案例使用 VA；同一案例不自动创建第二份 RPT。New cases use VA, without an automatic duplicate RPT. |
| RPT | 旧 RPT 继续用 `report` 原命令维护；不转换、不合并存储模型。Existing RPTs keep their report commands and model. |
| `metadata.yaml` | 结构化字段与 append-only history 的正式事实位置。Source of structured fields and append-only history. |
| `learning.md` | 登记后手写学习笔记；重复登记保留现有内容。Handwritten follow-up notes; identical registration preserves them. |
| 原报告 / Original report | 正文来源，只引用和校验，不执行、不移动。Body source; referenced and checked, not executed or moved. |
| 登记 JSON / Intake JSON | 人工审阅后的导入依据，不是另一份持续维护的元数据。Reviewed import input, not a second metadata store. |
| `case.md`, `materials.md`, `timeline.md` | 登记时生成的快照；不是 YAML/history 的实时视图。Registration snapshots, not live projections of YAML/history. |
| `learning_notes` | 保留旧数组，用于首次生成学习笔记；不删除字段、不重生成手写内容。Retained initial-import notes, not a replacement for handwritten notes. |

## 校验规则 / Validation rules

Report permits workspace-relative or absolute material paths and optional SHA-256, including
legacy RPT records without hashes and note-only evidence. VA requires absolute source paths
and hashes for every material, evidence, rating source and reference-case source.
Both use the same underlying path, hash and evidence-line checks. Existing write-time checks,
post-write reopens and error order are retained; shared code does not weaken either rule set.

Report 允许相对工作区路径、可选哈希与纯文字依据；VA 的材料及各类来源必须有绝对路径和哈希。
两者共用底层材料校验，但保留规则差异。VA 校验只核对生成文档存在，不比较快照是否与 YAML 同步。
原件移动、编辑或删除会使相应校验失败；本轮不做真实材料迁移。

## 统计与后续功能 / Counts and future work

VA 案例数由 `vulnarc va list` 给出，RPT 报告数由 `report list` / `stats` 的报告段给出。
研究记录使用原 `list` / `stats` 入口；全库清单包括不同 kind，不能当作一个去重漏洞数。
VA and RPT counts are distinct; neither changes research validation/rejection denominators.

正文阅读、笔记编辑命令、VA update、统一实时时间线、交互登记、检索与网页仍是计划项。
Body reading, note editing commands, VA update, a unified live timeline, interactive intake,
search and a web UI are not implemented. No schema upgrade, conversion or ID reuse is introduced.

相关入口：[安装](installation.md) · [VA 中文](docs-zh/va-quickstart.md) ·
[VA English](va-quickstart.md) · [旧 RPT](docs-zh/report-quickstart.md)。
