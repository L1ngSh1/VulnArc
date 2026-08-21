# VulnArc — 人机协作漏洞研究

**从假设到披露。**

VulnArc 是一个以仓库为核心的研究笔记系统，面向严谨且经过授权的漏洞研究。Markdown 用于保存推理过程，YAML 用于记录生命周期和来源信息，小型 CLI 则用于减少重复工作。**AI 发现不等于漏洞**：在获得可复现证据并通过人工验证之前，所有结论都只能视为假设或候选问题。

## 四个领域

- **研究案例** — 仅在协调披露完成后发布的脱敏记录。
- **漏洞模式** — 从已验证案例中提炼的可复用经验。
- **人类 × AI 实验** — 不捏造数据的透明对比实验。
- **研究方法论** — 攻击面梳理、验证、否定与披露。

```mermaid
flowchart LR
  H[人工研究] --> Y[假设]
  A[外部 AI] --> Y
  Y --> V[人工验证]
  V --> R[已否定]
  V --> D[披露]
  D --> P[公开案例与模式]
```

## 快速开始

```bash
python3.12 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
vulnarc new hypothesis --target example-project --title 'Synthetic authorization question' \
  --origin human --security-boundary 'member -> project'
vulnarc validate
vulnarc stats
```

对于尚未披露的工作，请使用 `--workspace /absolute/path/to/VulnArc-Research`。CLI 永远不会执行提交、推送、发布或上传操作。

## 命令

`validate`、`new hypothesis`、`new experiment`、`new case`、`list`、`status`、`stats` 和 `compare`。

参阅[方法论](methodology.md)、[研究工作流](research-workflow.md)和[工作区模型](workspace-model.md)。
