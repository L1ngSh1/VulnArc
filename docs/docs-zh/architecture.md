# 架构

VulnArc 以仓库为核心：Markdown 是持久化的推理记录，YAML 是结构化元数据。Pydantic 负责验证记录，存储层遍历 `metadata.yaml`，生命周期代码强制执行明确的状态转换，Typer 则对外提供轻量命令。项目不包含数据库、扫描器、智能体框架、模型 API 或发布集成。

## 记录、事务与材料校验

VA 案例与 RPT 报告独立保存；职责以[维护约定](../maintenance.md)为准。
RPT 的投稿事实与处理结果使用独立枚举，history 只追加。
本机写入使用 `.vulnarc/write.lock`（POSIX 单机 `fcntl`）、完整暂存目录、原子替换、
SHA-256 指纹冲突检查和字节级备份；恢复要求当前哈希仍等于那次写入结果。
旧反馈不倒退当前状态，更正追加事件；专用 inventory 导入默认零写入预览、逐条应用。

`materials.py` 共用路径、哈希与证据行号检查，不依赖 Typer。
storage 直接调用材料模块，不再导入 CLI 的 va 模块；记录类型的严格度保持不同。
正式代码与安装入口见[安装说明](../installation.md)，日期交付目录不再是开发入口。
