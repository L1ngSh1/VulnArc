# CI 检查：提交之后，GitHub 在检查什么？

CI 是 Continuous Integration（持续集成）。在这个项目里，可以把它理解成一套自动验收：
你提交 PR，GitHub 就启动临时环境，安装项目、跑测试，再把结果显示在 PR 的 Checks 页面。

绿勾表示这次配置的检查通过；红叉表示某一步失败，需要打开日志看原因。
它不是自动发布，也不是“项目绝对没有漏洞”的证明。

## 现在有哪些检查

| PR 中的检查 | 检查内容 | 红叉后先看什么 |
| --- | --- | --- |
| `quality` | Ruff、自动化测试，以及源码目录外的 wheel 安装测试 | 失败的文件、测试名称和断言 |
| `dependency-audit` | 查询锁定的 Python 运行/开发依赖是否有已公开漏洞 | 包名、当前版本、公告编号与修复版本 |

两项检查在 PR、合并到 main、手动运行时触发。每周一北京时间 09:17 还会安排一次检查，
这样即使代码没变，新公布的依赖漏洞也有机会被发现。GitHub 的定时任务可能延迟。

质量检查按 `uv.lock` 安装依赖；依赖检查从同一份锁文件导出运行与开发依赖，
通过 PyPI 公告数据查询已知问题，不安装或执行待审计的包，也不运行报告或附件。
发现漏洞、依赖收集失败或服务访问失败都会让检查失败，不使用自动修复或忽略漏洞选项。

锁文件未随依赖声明更新时，`--locked` 会报错。应先在本地审阅并更新锁文件，再提交。
安装工具、构建时临时获取的构建依赖不属于这次锁文件审计范围；CI 工具的直接版本单独固定。
这不是源码漏洞扫描，也不检查私有研究库。

## Dependabot 会做什么

它每周检查三类更新：项目的 uv 依赖、CI 工具，以及 GitHub Actions。
有更新时创建 PR，说明更新内容，再由同样的 CI 检查验证。它不会自动替你合并。

项目依赖的小版本/补丁更新会合并到一组，减少通知数量；各类版本更新最多同时保留 3 个 PR。
定时任务和 Dependabot 配置合并到默认分支后才正式生效。
Dependabot 版本更新配置不等于已经启用了仓库的所有 Security 设置。

## CI 自身做了哪些约束

- 工作流令牌只有 `contents: read`，checkout 不保留 Git 凭据。
- 第三方 Actions 固定到完整提交 SHA，后续通过 Dependabot PR 更新。
- 每个任务有超时，同一分支的新检查会取消旧检查。
- PR 使用 `pull_request`，没有运行高权限的 `pull_request_target`。
- 不传入个人 token，不在工作流里自动推送、发布或合并。

## 如何看一次失败

打开 PR → **Checks** → 选择红叉任务 → 展开失败的步骤。

- **测试失败：** 先复现具体测试，确认是代码回归还是测试需要同步。
- **已知依赖漏洞：** 查看公告和修复版本，在单独 PR 更新依赖与锁文件，再重跑。
- **网络或服务失败：** 看超时/连接错误，服务恢复后重试，不把它当成“没有漏洞”。

本地依赖检查可以在独立环境中安装 CI 工具，然后执行：

```bash
python -m pip install -r .github/requirements.txt
uv export --locked --extra dev --no-emit-project --format requirements-txt --output-file /tmp/vulnarc-audit.txt
python -m pip_audit --require-hashes --disable-pip --strict --progress-spinner off -r /tmp/vulnarc-audit.txt
```

审计需要联网查询依赖名称和版本；不上传报告正文。原文读取与材料核对命令仍按原规则工作。

## 绿勾与“禁止合并”是两件事

这个 PR 配置检查，不自动修改仓库的分支保护设置。
要让红叉阻止合并，需要在 main 的 Ruleset/分支保护里，把 `quality` 和 `dependency-audit`
设为 required checks。建议先确认两项在真实 PR 上正常运行，再设置必需检查。

CodeQL、密钥扫描、推送保护和强制人工评审是另外的选项，暂未在这轮配置中启用。
回退时撤销这次配置提交即可；如果以后启用了 required checks，删除任务前先同步调整规则，避免 PR 被卡住。

## References

- [GitHub Actions secure use](https://docs.github.com/en/actions/reference/security/secure-use)
- [pip-audit usage and security model](https://github.com/pypa/pip-audit)
- [Dependabot configuration](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference)
