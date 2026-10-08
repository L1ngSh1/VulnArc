# VulnArc 🗂️
### 漏洞报告归档与研究笔记

[👉 English Version](../../README.md)

![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![License](https://img.shields.io/badge/License-Apache--2.0-green)

---

## 📌 项目介绍

**VulnArc** 是一个用于整理漏洞报告与安全研究资料的本地归档工具。
它以 **`VA-2026-0001`** 这样的案例编号，将报告正文、证据附件、提交记录和学习笔记关联起来。

一份报告往往会留下多个版本，还有翻译、截图和后续反馈。
时间一长，很容易只记得做过这个研究，却找不到当时提交了哪一版、评分依据放在哪里。
VulnArc 希望把这些资料整理成可以随时回看的案例，既用于归档自己的研究，也用于学习已经公开的漏洞。

目前支持：

- 登记已有报告，分配独立的 VA 案例编号
- 记录 CWE 分类、CVSS 评分及 CVE/GHSA 编号，并保留来源依据
- 在终端阅读主报告和已登记翻译
- 通过 SHA-256 核对原始材料是否发生变化
- 生成案例卡、材料索引和时间线快照
- 为每份案例保留可继续编辑的学习笔记

VA 是本地档案编号。实际获配的外部编号与学习时引用的历史案例分开记录，
本地登记不代表向厂商提交报告，也不代表获得 CVE。

---

## 🧩 工作流程

```text
已有报告与相关材料
│
▼
人工审阅的 JSON 登记清单
│
▼
预览 → 确认登记
│
▼
VA-YYYY-NNNN
│
├── 案例概览
├── 主报告 / 已登记翻译
├── 材料位置与完整性核对
└── 时间线快照与学习笔记
```

项目使用 **YAML + Markdown** 保存档案，不依赖数据库。
结构化字段与历史记录保存在 `metadata.yaml`，笔记和案例文档可以直接用文本编辑器阅读。
原报告保留在原位置，通过路径与哈希关联。

一份登记完成的案例包含：

```text
VA-2026-0001/
├── metadata.yaml    # 结构化信息、材料引用与历史记录
├── case.md          # 案例卡
├── materials.md     # 材料索引
├── timeline.md      # 时间线快照
└── learning.md      # 手写学习笔记
```

案例卡、材料索引和时间线是登记时生成的快照；日常查询与核对以当前元数据为准。
私有案例库放在公开代码仓库之外，代码与研究资料分别维护。

---

## ⚡ 快速开始

### 安装

运行环境为 **Python 3.12+**，构建和安装步骤见[安装说明](../installation.md)。

```bash
vulnarc --help
```

### 登记一份报告

第一次使用可以先跑[完整示例](../va-intake-example.md)：它会生成一份虚构报告和可用的 JSON 清单。
换成自己的资料时，先审阅清单中的原件、评分与来源信息。

将下面的路径替换为你的私有工作区和清单文件，先查看预览：

```bash
WS="/absolute/path/to/VulnArc-Research"
vulnarc va register /absolute/path/to/intake.json --workspace "$WS"
```

确认后执行登记：

```bash
vulnarc va register /absolute/path/to/intake.json --workspace "$WS" --apply
```

完成后，终端会显示分配的 VA 编号。同一份清单重复登记会复用原编号，并保留已有笔记。

### 回来看报告

使用回执里的实际编号；下方以 `VA-2026-0001` 为例。

```bash
vulnarc va list --workspace "$WS"
vulnarc va show VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --report translation --workspace "$WS"
```

终端会排版显示标题、段落、表格和代码块。想看原始文本时追加 `--raw`；
翻译选项读取的是已经登记的翻译文件。

查找附件、核对材料：

```bash
vulnarc va materials VA-2026-0001 --workspace "$WS"
vulnarc va check --workspace "$WS"
```

`show` 展示概览，`read` 核对所选报告，`materials` 逐项核对原件。
移动或修改原件后，需要审阅并维护对应引用。完整用法见 [VA 使用指南](va-quickstart.md)。

---

## 📂 项目结构

```text
VulnArc/
├── src/vulnarc/      # 命令行入口与应用逻辑
│   ├── va.py        # VA 登记与查询命令
│   ├── reading.py   # 报告选择与校验后读取
│   ├── display.py   # 终端阅读排版
│   ├── materials.py # 共用材料校验
│   ├── models.py    # 记录模型
│   └── storage.py   # 工作区存储
├── schemas/         # 导出的记录结构定义
├── templates/       # 研究文档模板
├── tests/           # 自动化测试
├── docs/            # 使用说明与设计文档
└── pyproject.toml   # 包与依赖配置
```

项目还保留了假设、实验等研究流程，以及已有 RPT 记录的维护功能。
它们与 VA 归档流程分别使用，详见[研究工作流](research-workflow.md)和 [RPT 维护说明](report-quickstart.md)。

---

## 🛠️ 开发进展

报告登记、终端阅读和材料核对已经实现。
接下来考虑增加一个**以键盘操作为主的终端工作台**：左侧选择案例，右侧阅读报告，
在概览、正文、翻译和材料之间切换，减少反复输入命令的操作。

工作台目前处于[设计阶段](../workbench-design.md)，尚未实现。
检索、交互登记和 VA 更新命令留待后续逐步完善。

---

## 📖 文档导航

- [安装](../installation.md)
- [第一份登记清单示例](../va-intake-example.md)
- [VA 使用指南](va-quickstart.md)
- [档案与材料维护约定](../maintenance.md)
- [架构说明](architecture.md) · [工作区模型](workspace-model.md)
- [参与贡献](../../CONTRIBUTING.md) · [披露约定](../../DISCLOSURE.md)

- [CI 与依赖检查说明](../ci.md)

## 📄 许可证

本项目采用 [Apache-2.0](../../LICENSE) 许可证。
