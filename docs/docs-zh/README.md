# VulnArc — 人机协作漏洞研究

**从假设到披露，也能直接归档已有报告。**

VulnArc 用 YAML 保存结构化事实和 history，用 Markdown 保存推理与手写学习笔记。
AI 发现不等于漏洞；结论仍需可复现证据与人工验证。CLI 不自动投稿、提交、推送或上传。

## 从一份已有报告开始

按[唯一正式安装说明](../installation.md)安装正式仓库构建的 wheel，再使用已人工审阅的 JSON 清单。
正式入口是 `vulnarc`；`va` 只是同一安装包的兼容转发入口。

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/VulnArc-Research
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/VulnArc-Research --apply
vulnarc va list --workspace /absolute/path/to/VulnArc-Research
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/VulnArc-Research
vulnarc va read VA-2026-0001 --report primary --workspace /absolute/path/to/VulnArc-Research
vulnarc va read VA-2026-0001 --report translation --workspace /absolute/path/to/VulnArc-Research
vulnarc va materials VA-2026-0001 --workspace /absolute/path/to/VulnArc-Research
vulnarc va check --workspace /absolute/path/to/VulnArc-Research
```

先预览，再 `--apply`。VA 是本地案例编号，不代表 CVE 分配或厂商接受。
重复登记同一清单保留原编号和手写笔记；`read` 按编号输出完整主报告或中文翻译，
`materials` 显示实时材料入口与校验状态，`show` 提示正文和材料命令。
详情统一见[VA 快速指南](va-quickstart.md)与[材料和记录维护约定](../maintenance.md)。

## 当前已实现命令

| 用途 | 命令 |
| --- | --- |
| 新 VA 案例归档 | `va register`、`va list`、`va show`、`va read`、`va materials`、`va check` |
| 已有 RPT 报告维护 | `report add`、`report list`、`report show`、`report update` |
| 专用旧登记清单导入 | `report import-inventory`，特定格式，默认预览 |
| 全库校验、清单和恢复 | `validate`、`list`、`restore` |
| 进阶研究与实验 | `new hypothesis`、`new experiment`、`new case`、`status`、`stats`、`compare` |

**计划项，尚未实现**：笔记编辑命令、VA update、统一实时时间线、交互登记、检索、网页。
VA/RPT 仍是独立模型；新案例使用 VA，不自动创建第二份 RPT，不迁移或重编号旧记录。

## 进阶研究

HYP/EXP 等功能继续保留，登记已有报告不必先走假设与实验流程。
参阅[研究工作流](research-workflow.md)、[方法论](methodology.md)、[架构](architecture.md)
和[工作区模型](workspace-model.md)。旧 RPT 的反馈、更正与备份恢复见[报告维护速查](report-quickstart.md)。

统计口径保持分开：`va list` 给出 VA 案例数；`report list` 与 `stats` 的报告段描述 RPT；
研究指标仍按原研究记录计算。`list` 展示所有元数据记录类型，不是去重后的“漏洞总数”。
