# 第一份登记清单 / A minimal intake

这个示例只生成虚构文本和登记 JSON，不需要真实漏洞报告。先按[安装说明](installation.md)
准备 Python 3.12+ 与 `vulnarc`，在同一个 shell 中逐步执行。

This walkthrough creates a fictional report and a minimal intake in a temporary directory.
It does not use your real archive. Keep the directory for as long as you want to read this demo:
the archive links the original report rather than copying it.

## 1. 生成材料和清单 / Create the fixture

```bash
DEMO="$(mktemp -d "${TMPDIR:-/tmp}/vulnarc-demo.XXXXXX")"
export DEMO
python3 - <<'PY'
import hashlib
import json
import os
from pathlib import Path

root = Path(os.environ["DEMO"]).resolve()
report = root / "example.md"
report.write_text("# Example report\n\nFictional material for learning the archive workflow.\n", encoding="utf-8")
fingerprint = hashlib.sha256(report.read_bytes()).hexdigest()
proof = {"type": "existing_report", "path": str(report), "sha256": fingerprint}
intake = {
    "schema": "vulnarc-case-intake-v1",
    "case": {
        "project": "example-project",
        "title": "My first archive / 第一份学习档案",
        "purpose": "study",
        "source_key": "VA:example-project:DEMO-01",
        "category": "learning example",
        "summary": "A fictional report; no vulnerability claim or external submission.",
        "materials": [{"role": "primary_report", "label": "Example report", **{
            "path": str(report), "sha256": fingerprint
        }}],
        "evidence": [proof],
        "learning_notes": ["An archive identifier is not an assigned CVE."],
    },
}
path = root / "intake.json"
path.write_text(json.dumps(intake, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(path)
PY
WS="$DEMO/workspace"
```

清单没有捏造评分、CWE 或外部编号；有可靠来源时再填写。`purpose: study` 表示学习归档。
`source_key` 用于来源识别，必须以 `VA:` 开头；材料使用绝对路径，SHA-256 针对原始文件字节。

## 2. 审阅 → 预览 → 确认 / Review, preview, apply

先打开上一步打印出的 JSON，确认材料与目的。预览不会创建工作区或分配编号：

```bash
vulnarc va register "$DEMO/intake.json" --workspace "$WS"
```

确认预览后再执行这条写入命令。它只写入临时示例工作区：

```bash
vulnarc va register "$DEMO/intake.json" --workspace "$WS" --apply
```

从回执复制实际分配的 ID。下方编号是示例，不保证与运行时年份一致：

```bash
vulnarc va list --workspace "$WS"
vulnarc va show VA-2026-0001 --workspace "$WS"
vulnarc va read VA-2026-0001 --workspace "$WS"
vulnarc va materials VA-2026-0001 --workspace "$WS"
vulnarc va check --workspace "$WS"
```

The sample has no translation; only request one after registering translation material.
VA IDs follow the registration year. Substitute the ID from your receipt in the commands above.

## 3. 换成真实报告前 / Before using a real report

把私有工作区放到公开代码仓库之外，重新核对原件路径、哈希与已有报告中的事实。
主报告用 `primary_report`，已登记翻译用 `translation`。获配 CVE/GHSA 与历史参考案例分别登记，
不因学习了一个 CVE 就声称它是自己的获配编号。评分要注明版本、向量、归属与证据来源。

临时目录被系统清理或手动删除后，示例档案也会失效；真实资料应使用稳定位置。
完整字段以代码中的 `CaseDetails` 为准；后续阅读和五件套说明见 [VA 指南](va-quickstart.md)。
