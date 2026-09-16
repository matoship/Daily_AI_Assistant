import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from daily_assistant import run as run_module


@pytest.fixture
def main_env(monkeypatch, tmp_path):
    # This UTC instant is already the next calendar day in Adelaide.
    instant = datetime(2026, 9, 15, 16, 0, tzinfo=timezone.utc)

    def fake_zone_info(key):
        assert key == "Australia/Adelaide"
        # Adelaide's offset on this fixed date; no system tzdata required.
        return timezone(timedelta(hours=9, minutes=30))

    class FixedDatetime:
        @classmethod
        def now(cls, tz):
            return instant.astimezone(tz)

    monkeypatch.setattr(run_module, "datetime", FixedDatetime)
    monkeypatch.setattr(run_module, "ZoneInfo", fake_zone_info)
    monkeypatch.setattr(
        run_module, "__file__", str(tmp_path / "src" / "daily_assistant" / "run.py")
    )
    monkeypatch.delenv("CI", raising=False)
    pipeline = Mock(return_value=[])
    render_digest = Mock(return_value="<html>Digest — café</html>")
    render_index = Mock(return_value="<html>Index — café</html>")
    browser = Mock()
    monkeypatch.setattr(run_module, "run", pipeline)
    monkeypatch.setattr(run_module, "render_digest_page", render_digest)
    monkeypatch.setattr(run_module, "render_index", render_index)
    monkeypatch.setattr(run_module.webbrowser, "open_new_tab", browser)
    return SimpleNamespace(
        output_dir=tmp_path / "docs",
        pipeline=pipeline,
        render_digest=render_digest,
        render_index=render_index,
        browser=browser,
    )


@pytest.mark.parametrize(
    "argv, local", [([], False), (["--vllm"], True), (["-v"], True)]
)
def test_main_passes_cli_flag_to_pipeline(main_env, argv, local):
    run_module.main(argv)

    main_env.pipeline.assert_called_once_with(local)


def test_main_writes_digest_and_index_and_opens_browser(main_env):
    item = {"title": "Example", "article_urls": ["https://example.com"]}
    main_env.pipeline.return_value = [Mock(model_dump=Mock(return_value=item))]

    run_module.main([])

    output_dir = main_env.output_dir
    assert json.loads((output_dir / ".digest_2026-09-16.json").read_text()) == [item]
    main_env.render_digest.assert_called_once_with([item], "2026-09-16")
    assert (output_dir / "digest_2026-09-16.html").read_text(encoding="utf-8") == (
        main_env.render_digest.return_value
    )
    main_env.render_index.assert_called_once_with(["2026-09-16"])
    assert (output_dir / "index.html").read_text(encoding="utf-8") == (
        main_env.render_index.return_value
    )
    main_env.browser.assert_called_once_with((output_dir / "index.html").as_uri())


def test_main_appends_items_on_repeated_same_day_runs(main_env):
    first = {"title": "First"}
    second = {"title": "Second"}
    main_env.pipeline.side_effect = [
        [Mock(model_dump=Mock(return_value=first))],
        [Mock(model_dump=Mock(return_value=second))],
    ]

    run_module.main([])
    run_module.main([])

    sidecar = main_env.output_dir / ".digest_2026-09-16.json"
    assert json.loads(sidecar.read_text()) == [first, second]
    main_env.render_digest.assert_called_with([first, second], "2026-09-16")


def test_main_indexes_digest_pages_newest_first(main_env):
    main_env.output_dir.mkdir()
    for filename in ["digest_2026-09-14.html", "notes.html", "digest_2026-09-15.html"]:
        (main_env.output_dir / filename).write_text("existing page")

    run_module.main([])

    main_env.render_index.assert_called_once_with(
        ["2026-09-16", "2026-09-15", "2026-09-14"]
    )


def test_main_writes_empty_digest_without_opening_browser_in_ci(main_env, monkeypatch):
    monkeypatch.setenv("CI", "true")

    run_module.main([])

    assert (
        json.loads((main_env.output_dir / ".digest_2026-09-16.json").read_text()) == []
    )
    assert (main_env.output_dir / "index.html").is_file()
    main_env.browser.assert_not_called()


@pytest.mark.parametrize("argv, exit_code", [(["--help"], 0), (["--unknown"], 2)])
def test_main_exits_before_running_pipeline(main_env, argv, exit_code):
    with pytest.raises(SystemExit) as exc_info:
        run_module.main(argv)

    assert exc_info.value.code == exit_code
    main_env.pipeline.assert_not_called()
    assert not main_env.output_dir.exists()
    main_env.browser.assert_not_called()


def test_main_propagates_pipeline_failure_without_writing_output(main_env):
    main_env.pipeline.side_effect = RuntimeError("pipeline failed")

    with pytest.raises(RuntimeError, match="pipeline failed"):
        run_module.main([])

    assert not main_env.output_dir.exists()
    main_env.render_digest.assert_not_called()
    main_env.browser.assert_not_called()
