# Installation / 正式安装

The maintained source is the VulnArc repository. Dated delivery directories are historical
snapshots, not development roots. The installed `vulnarc` command is the formal entry point;
`va` only delegates to its VA command group. Version has one declaration in
`src/vulnarc/__init__.py`, used by the build metadata.

正式代码只在 VulnArc 仓库维护；日期交付目录保留为历史快照。
在仓库根目录构建 wheel，安装到独立环境；不设置源码 PYTHONPATH，不借用旧一期环境：

```bash
uv build --wheel --out-dir dist
uv export --frozen --no-emit-project --format requirements-txt --output-file dist/runtime-requirements.txt
uv venv --python 3.12 .venv-release
uv pip install --python .venv-release/bin/python -r dist/runtime-requirements.txt dist/vulnarc-0.2.0-py3-none-any.whl
export PATH="$PWD/.venv-release/bin:$PATH"
vulnarc --help
```

`uv` is a build/install tool, not a runtime dependency. After installation, commands work
outside the source directory. Templates are bundled in the wheel. Developers can instead use
an independent `.venv` and `pip install -e '.[dev]'`; that is not the release installation.

## Workspace selection / 工作区选择

- `vulnarc` continues to require explicit `--workspace` / `-w`; it does not infer a destination
  from `VULNARC_WORKSPACE`.
- The compatibility `va` shortcut preserves the old order: explicit workspace >
  `VULNARC_WORKSPACE` > `$HOME/Workspace/Projects/My-github-projects/VulnArc-Research`.
- Only `va register/show/list/check` inject a default. Both long and short workspace options
  are accepted. Migration does not change the selected data directory.
- The historical launcher now forwards to the installed `va` in this repository's
  `.venv-release/bin`. `VULNARC_VA_BIN` may select another installed `va` executable.
  `VULNARC_PYTHON` and old source PYTHONPATH are no longer used by that forwarder.

正式命令显式选库；兼容入口保留旧默认库和环境变量优先级。登记真实数据时仍显式选库。
旧 VA 源码、旧运行环境与原启动器备份保留用于回退，旧 10 测试版本不接管 VA 数据。
数据备份恢复使用 `vulnarc restore`；代码回退与数据恢复分开处理。
