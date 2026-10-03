# 已有报告登记：一页速查

旧 RPT 继续保留 Markdown + YAML 和研究命令。`report` 不要求假设、来源或安全边界；只必答项目与标题。所有命令显式传 `--workspace`，未知事实留 `unknown`。没有自动访问平台或投稿动作。

```sh
WS=/absolute/path/to/VulnArc-Research
# 登记：不填写就以中文提示项目、标题；ID 留空会在锁内自动分配
vulnarc report add -w "$WS" --project demo --title '已有报告' \
  --id RPT-DEMO-001 --original /absolute/path/to/original.md
# 已提交但没有编号：使用已有登记或回执，不用编造编号、日期
vulnarc report add -w "$WS" --project demo --title '补天登记' \
  --channel 补天 --submission submitted --evidence-type local_ledger \
  --evidence-path /absolute/path/to/ledger.md --submitted-at-raw '约 09-28/29'
# 查看
vulnarc report list -w "$WS" --project demo --status pending_review
vulnarc report show RPT-DEMO-001 -w "$WS"
# 一次当前反馈：状态、依据、时间线一次原子写入，正文原封不动
vulnarc report update RPT-DEMO-001 -w "$WS" --raw-status Duplicate \
  --evidence-type receipt --evidence '回执说明重复' --note '已登记反馈'
# 补记旧反馈：只追加历史，不倒退当前值
vulnarc report update RPT-DEMO-001 -w "$WS" --raw-status Informative \
  --historical --date-raw 2026-09-29 --note '补记第一轮反馈'
# 更正旧事件：旧事件不删除；EVENT_ID 来自 report show
vulnarc report update RPT-DEMO-001 -w "$WS" --corrects EVENT_ID \
  --raw-status Duplicate --reason '原台账状态文字更正'
# 确需校正当前值时，再加 --apply-current；确认提示可用 --yes 代替
vulnarc report update RPT-DEMO-001 -w "$WS" --status pending_review \
  --apply-current --reason '后续反馈转工程验证' --yes
vulnarc validate -w "$WS"
vulnarc stats -w "$WS"
# 恢复本次误改：BACKUP_ID 来自 update/status 的输出
vulnarc restore BACKUP_ID -w "$WS"
```

新案例优先使用 VA；本页用于旧 RPT 的原命令维护，不为 VA 自动生成第二份报告。
共同职责见[维护约定](../maintenance.md)，安装见[统一说明](../installation.md)。

**时间与状态**：建档时间不是提交时间。`submitted_at` / `status_at` 可空；原始模糊日期单独保留。带日期的反馈早于当前依据，或日期先后无法确定时，默认只记历史；显式 `--apply-current --reason` 并确认后才校正当前字段。`Pending program review`、转工程验证映射 `pending_review`，未知原文映射 `unknown`。Duplicate、Informative 不改变研究对象；resolved 不推断公开、CVE 或赏金。

**材料与缺项**：`--related`、`--research-ref`、`--missing` 可重复；原件只引用并计算 SHA-256，不搬走。列表展示提交事实、处理状态、更新时间与缺项。相同渠道与外部编号提示关联原档，标题相同只提示。校验检查 ID、外部编号、材料路径/哈希及研究引用；报告统计与研究指标分开。

**写入和恢复**：重复 ID 一律失败；创建完整暂存档再发布。更新使用本机锁和元数据指纹，外部编辑冲突会中止；备份位于 `$WS/.vulnarc/backups/BACKUP_ID/`。恢复校验备份和当前版本哈希，后续修改不会被覆盖。`.vulnarc` 中的锁、暂存和备份不参与扫描。恢复为字节级恢复，不伪造旧时间线；恢复动作本身保留反向备份。只保证同一台机器的协作工具写入与常见失败清理，不承诺共享网络盘或断电持久性。

**本次专用转换**：仅接受本轮 inventory 格式；默认 dry-run，先 `--sample` 三类样例，再最多 8 条。实际源状态键保存为 `local_status_raw`，没有平台逐字反馈就让 `platform_status_raw` 留空；不补猜最新结果。同来源同清单内容跳过，清单变化或编号冲突会报告。apply 每条独立提交，预先检查全部可识别冲突；中途失败可能留下已成功条目，重试会跳过它们。

```sh
vulnarc report import-inventory /absolute/path/to/inventory.json -w "$WS" --sample
vulnarc report import-inventory /absolute/path/to/inventory.json -w "$WS" --limit 8
# 真实工作区的 --apply 需另行确认；先在副本演练
```
