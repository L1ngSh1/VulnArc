from typer.testing import CliRunner

from vulnarc.cli import app

runner = CliRunner()


def test_cli_creates_synthetic_hypothesis(tmp_path):
    result = runner.invoke(
        app,
        [
            "new",
            "hypothesis",
            "--workspace",
            str(tmp_path),
            "--target",
            "example-project",
            "--title",
            "Synthetic question",
            "--origin",
            "human",
            "--security-boundary",
            "member -> project",
            "--id",
            "SYNTH-HYP-001",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_path / "hypotheses/SYNTH-HYP-001/metadata.yaml").exists()
    assert (
        "Why This Might Be Wrong"
        in (tmp_path / "hypotheses/SYNTH-HYP-001/hypothesis.md").read_text()
    )
    assert runner.invoke(app, ["validate", "--workspace", str(tmp_path)]).exit_code == 0
