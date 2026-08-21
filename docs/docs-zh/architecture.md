# 架构

VulnArc 以仓库为核心：Markdown 是持久化的推理记录，YAML 是结构化元数据。Pydantic 负责验证记录，存储层遍历 `metadata.yaml`，生命周期代码强制执行明确的状态转换，Typer 则对外提供轻量命令。项目不包含数据库、扫描器、智能体框架、模型 API 或发布集成。
