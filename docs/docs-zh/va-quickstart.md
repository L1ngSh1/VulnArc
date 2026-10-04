# 第一份 VA：从既有报告到本地档案

VA 是内部案例编号，不等于 CVE，也不表示厂商已接受。
当前入口是正式安装包的 `vulnarc va`，不是网页表单。
安装见[统一安装说明](../installation.md)；维护职责见[统一约定](../maintenance.md)。

```bash
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace
vulnarc va register /absolute/path/to/reviewed-intake.json --workspace /absolute/path/to/private-workspace --apply
vulnarc va list --workspace /absolute/path/to/private-workspace
vulnarc va show VA-2026-0001 --workspace /absolute/path/to/private-workspace
vulnarc va read VA-2026-0001 --report primary --workspace /absolute/path/to/private-workspace
vulnarc va read VA-2026-0001 --report translation --workspace /absolute/path/to/private-workspace
vulnarc va materials VA-2026-0001 --workspace /absolute/path/to/private-workspace
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

`metadata.yaml` 管结构化字段和 history；自有 CVE/GHSA 与历史参考编号分开存储。
`learning.md` 管后续手写笔记；`learning_notes` 保留为首次导入的初始内容。
`case.md`、`materials.md`、`timeline.md` 只是在登记时生成的快照，不是实时视图；
校验检查这些文档是否存在，不检查与 YAML 的同步。原报告是正文来源，JSON 是导入依据。
`submitted` 表示登记状态，`submission_basis` 标明用户口径还是平台回执，
`processing_status` 独立记录平台处理结果。按用户口径登记时仍保留回执待补说明。

## 只记编号就能阅读和找到附件

- `read --report primary`（默认）选择 `primary_report`，`--report translation` 选择 `translation`。
- 正文来自原件，不是 `case.md` 摘要。校验和解码使用同一份字节，完整输出 UTF-8 的 `.md`、`.markdown` 或 `.txt`，不加摘要或包装。其他格式在材料入口显示路径，本步没有 PDF/Word 渲染。
- 缺失文件、哈希变化、未登记翻译、同角色多份报告、缺少哈希、非 UTF-8 和终端控制字符均明确报错，不输出未通过校验的正文。
- `materials` 读取当前 YAML，逐项显示角色、标签、绝对路径、登记哈希和校验结果；一项失败仍列出其余材料，最终退出码为 1。
- `show` 保留编号卡，并显示带工作区参数的正文/材料命令及逐项状态；有失败时仍保留入口，退出码为 1，不声称全部校验通过。
- 读取只核对所选报告，坏附件不阻塞好正文；不运行代码块、不解包、不写回元数据、快照、笔记、history 或哈希。完整证据行号/全库检查继续用 `check`。
- 正式 `vulnarc` 继续显式使用 `-w`；兼容 `va read` / `va materials` 保留显式参数 > `VULNARC_WORKSPACE` > 原默认库。选定工作区后，不必记原报告目录。

## 当前边界与后续升级

- 当前支持人工审阅后的 JSON 导入、编号、查阅、哈希校验；还没有交互向导或 VA 更新命令。
- 当前链接原始材料的绝对路径。移动、编辑、删除原件会使校验失败；迁移需要重新链接并留记录。
- 不上传外部平台，不运行报告命令，不联网查验漏洞。
- 笔记编辑命令、`va update`、统一实时时间线、交互登记、检索与网页均尚未实现。
- 正式仓库已整合 VA；日期交付目录仅作历史与回退材料，不继续开发。
- 代码回滚与资料撤销分开处理。封存资料时保留 VA 编号与流水，不回收编号。
