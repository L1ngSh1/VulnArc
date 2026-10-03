# 第一份 VA：从既有报告到本地档案

VA 是内部案例编号，不等于 CVE，也不表示厂商已接受。
当前入口是 CLI，不是网页表单。

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace --apply
vulnarc va list --workspace /absolute/path/to/private-workspace
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/private-workspace
vulnarc va check --workspace /absolute/path/to/private-workspace
```

先整理 JSON 清单，再预览，再 `--apply`。成功落盘、重新读取并核对原件哈希后才显示分配回执。
同一份清单重复登记复用原编号，不覆盖手写笔记；内容变化时提示差异，不暗中覆盖。
失败或删除后的编号不回收，允许跳号。年度使用 Asia/Shanghai。

## 五件套

1. 编号总账：`va list` 从实际元数据生成。
2. 案例卡：`case.md`，评分注明版本、向量和归属。
3. 材料索引：`materials.md`，原件路径与 SHA-256，不复制或执行附件。
4. 时间线：`timeline.md`，区分登记日、计划提交日与实际提交日。
5. 学习笔记：`learning.md`，记录已有结论与工程经验。

`metadata.yaml` 是结构化登记数据；自有 CVE/GHSA 与历史参考编号分开存储。
`submitted` 表示登记状态，`submission_basis` 标明用户口径还是平台回执，
`processing_status` 独立记录平台处理结果。按用户口径登记时仍保留回执待补说明。

## 当前边界与后续升级

- 当前支持人工审阅后的 JSON 导入、编号、查阅、哈希校验；还没有交互向导或 VA 更新命令。
- 当前链接原始材料的绝对路径。移动、编辑、删除原件会使校验失败；迁移需要重新链接并留记录。
- 不上传外部平台，不运行报告命令，不联网查验漏洞。
- 下一步先补 `va update` 与反馈时间线（差异预览、历史、可恢复更新），再做 `va register` 交互向导。
- 最后将这份工程副本合并到主项目并做安装/迁移测试；避免旧 CLI 读取新 `va_case` 类型。
- 代码回滚与资料撤销分开处理。封存资料时保留 VA 编号与流水，不回收编号。
