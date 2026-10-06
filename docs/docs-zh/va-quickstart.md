# 第一份 VA：从既有报告到本地档案

VA 是内部案例编号，不等于 CVE，也不表示厂商已接受。
当前入口是正式安装包的 `vulnarc va`，不是网页表单。
安装见[统一安装说明](../installation.md)；维护职责见[统一约定](../maintenance.md)。

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

`metadata.yaml` 管结构化字段和 history；自有 CVE/GHSA 与历史参考编号分开存储。
`learning.md` 管后续手写笔记；`learning_notes` 保留为首次导入的初始内容。
`case.md`、`materials.md`、`timeline.md` 只是在登记时生成的快照，不是实时视图；
校验检查这些文档是否存在，不检查与 YAML 的同步。原报告是正文来源，JSON 是导入依据。
`submitted` 表示登记状态，`submission_basis` 标明用户口径还是平台回执，
`processing_status` 独立记录平台处理结果。按用户口径登记时仍保留回执待补说明。

## 登记以后：阅读正文与查找材料

```bash
WS="/absolute/path/to/private workspace"
vulnarc va show VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
vulnarc va materials VA-2026-0001 --workspace "$WS"
# 存在多份翻译时，使用材料清单给出的当前序号：
vulnarc va read VA-2026-0001 --report translation --material 2 --workspace "$WS"
```

- `show` 只读元数据：编号、标题、来源、评分归属、登记/处理状态、材料数量与操作命令。
  命令包含当前实际工作区，并引用空格路径。材料明确标为**未校验**；缺失附件不阻止概览。
  登记成功回执仍保留完整核对语义，两者不混用。
- `read` 缺省选择已登记的 `primary_report`；`--report translation` 选择已登记翻译，
  不按文件名猜测，也不自动翻译。对应角色存在多份时必须加 `--material N`。
  N 是 `materials` 当前从 1 开始的序号，不是持久 ID；越界或角色不一致返回参数错误。
- 管道或 `--raw` 模式的完整 UTF-8 正文走 stdout，不截断、不额外添加末尾换行；编号、角色、原件路径及
  SHA-256 核对结果走 stderr。BOM 按编码标记处理；终端和双向文本控制字符可见化，
  正常 Markdown 换行、制表符保留。哈希针对原始字节，显示的正是这一次核对的字节。
- 所选报告原件缺失、路径非绝对、哈希缺失/变化或读取失败时，不输出正文；无关附件
  损坏不阻断另一份正常报告。二进制（含 NUL）、非文本格式或非 UTF-8 给出类型问题和原件位置。
- `materials` 逐项列出序号、角色、标签、原件路径和真实校验结果；单项失败仍显示完整清单。
  哈希通过只表示原件字节一致，不表示它可作为文本阅读，也不表示漏洞已复验。
- 三个命令不改档案、快照、手写笔记，不创建锁、缓存或历史事件；不执行代码/HTML/链接，
  不打开浏览器、不解包、不调用 pager、不联网。PDF、Word、图片先从材料列表找到原件。

### 终端阅读版面

终端内自动把 Markdown 排版到正文边框中；编号、原件与校验状态在独立信息栏（stderr）。
标题、粗体、列表、引用、表格和代码块正常显示；长表格单元格与代码行自动折行，不用省略号
吞掉内容。默认按当前终端宽度排版，两侧各留 2 列，不再固定最多 100 列。
`--width 90` 可指定较窄的阅读宽度（40–200），并在窗口内居中；窄窗口仍自动缩小。
段落之间多留一行，章节标题前增加留白，信息栏与正文之间空一行；代码块、表格数据行、
紧凑列表内部保持原有结构，不逐行插空白。调整窗口后重新运行，会使用新的终端尺寸。

```bash
vulnarc va read VA-2026-0001 --pretty --workspace "$WS"
vulnarc va read VA-2026-0001 --pretty --width 90 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
vulnarc va read VA-2026-0001 --raw --workspace "$WS"
```

顶部显示当前报告与切换参数；中文报告若已登记为 `translation`，使用 `--report translation`
切换，使用 `--report primary` 返回主报告。顶部是命令提示，不是点击按钮；不猜测语言、
不生成翻译。`--pretty` 强制排版，`--raw` 强制原文，两者互斥。重定向/管道缺省仍为原文，
信息继续走 stderr；不生成额外报告副本。
日常阅读只执行所需的一条命令；避免整组执行后用 `--raw` 把排版视图覆盖。交互 zsh 中可
复制不带 `#` 注释的命令，不需要为阅读功能修改全局 shell 配置。链接保持文本，关闭终端超链接；不调用 pager 或浏览器。
本次把现有 Typer 已带入的 Rich 声明为直接依赖，锁定包集合和版本保持不变。

退出码：成功为 0；案例不存在、元数据异常、原件或文本读取异常为 1；未知选项、非法材料
序号、角色冲突、多候选待选择为 2。材料清单有一项错误则返回 1，但清单仍完整。
`show` 成功不是完整性结论；`check` 继续严格检查全库原件、引用行号和快照文件存在性。

## 当前边界与后续升级

- 当前支持人工审阅后的 JSON 导入、编号、概览、完整正文阅读、材料列表与哈希校验；还没有交互向导或 VA 更新命令。
- 当前链接原始材料的绝对路径。移动、编辑、删除原件会使校验失败；迁移需要重新链接并留记录。
- 不上传外部平台，不运行报告命令，不联网查验漏洞。
- 笔记编辑命令、`va update`、统一实时时间线、交互登记、检索与网页均尚未实现。
- 正式仓库已整合 VA；日期交付目录仅作历史与回退材料，不继续开发。
- 代码回滚与资料撤销分开处理。封存资料时保留 VA 编号与流水，不回收编号。
