from __future__ import annotations

import platform
import sys
from pathlib import Path

from inline_snapshot import snapshot


def test_pyinstaller_datas():
    from cran_code.utils.pyinstaller import datas

    project_root = Path(__file__).parent.parent.parent
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    site_packages = f".venv/lib/python{python_version}/site-packages"
    rg_binary = "rg.exe" if platform.system() == "Windows" else "rg"
    has_rg_binary = (project_root / "src/cran_code/deps/bin" / rg_binary).exists()
    datas = [
        (
            Path(path)
            .relative_to(project_root)
            .as_posix()
            .replace(".venv/Lib/site-packages", site_packages),
            Path(dst).as_posix(),
        )
        for path, dst in datas
    ]

    datas = [(p, d) for p, d in datas if "web/static" not in d and "vis/static" not in d]

    expected_datas = [
        (
            f"{site_packages}/dateparser/data/dateparser_tz_cache.pkl",
            "dateparser/data",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/INSTALLER",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/METADATA",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/RECORD",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/REQUESTED",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/WHEEL",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/entry_points.txt",
            "fastmcp/../fastmcp-3.2.4.dist-info",
        ),
        (
            f"{site_packages}/fastmcp/../fastmcp-3.2.4.dist-info/licenses/LICENSE",
            "fastmcp/../fastmcp-3.2.4.dist-info/licenses",
        ),
        (
            "src/cran_code/CHANGELOG.md",
            "cran_code",
        ),
        ("src/cran_code/agents/default/agent.yaml", "cran_code/agents/default"),
        ("src/cran_code/agents/default/coder.yaml", "cran_code/agents/default"),
        ("src/cran_code/agents/default/explore.yaml", "cran_code/agents/default"),
        ("src/cran_code/agents/default/plan.yaml", "cran_code/agents/default"),
        ("src/cran_code/agents/default/system.md", "cran_code/agents/default"),
        ("src/cran_code/agents/okabe/agent.yaml", "cran_code/agents/okabe"),
        ("src/cran_code/prompts/compact.md", "cran_code/prompts"),
        ("src/cran_code/prompts/init.md", "cran_code/prompts"),
        (
            "src/cran_code/skills/kimi-cli-help/SKILL.md",
            "cran_code/skills/kimi-cli-help",
        ),
        (
            "src/cran_code/skills/skill-creator/SKILL.md",
            "cran_code/skills/skill-creator",
        ),
        ("src/cran_code/tools/agent/description.md", "cran_code/tools/agent"),
        ("src/cran_code/tools/ask_user/description.md", "cran_code/tools/ask_user"),
        (
            "src/cran_code/tools/dmail/dmail.md",
            "cran_code/tools/dmail",
        ),
        ("src/cran_code/tools/background/list.md", "cran_code/tools/background"),
        ("src/cran_code/tools/background/output.md", "cran_code/tools/background"),
        ("src/cran_code/tools/background/stop.md", "cran_code/tools/background"),
        (
            "src/cran_code/tools/file/glob.md",
            "cran_code/tools/file",
        ),
        (
            "src/cran_code/tools/file/grep.md",
            "cran_code/tools/file",
        ),
        (
            "src/cran_code/tools/file/read.md",
            "cran_code/tools/file",
        ),
        (
            "src/cran_code/tools/file/read_media.md",
            "cran_code/tools/file",
        ),
        (
            "src/cran_code/tools/file/replace.md",
            "cran_code/tools/file",
        ),
        (
            "src/cran_code/tools/file/write.md",
            "cran_code/tools/file",
        ),
        ("src/cran_code/tools/plan/description.md", "cran_code/tools/plan"),
        ("src/cran_code/tools/plan/enter_description.md", "cran_code/tools/plan"),
        ("src/cran_code/tools/shell/bash.md", "cran_code/tools/shell"),
        (
            "src/cran_code/tools/think/think.md",
            "cran_code/tools/think",
        ),
        (
            "src/cran_code/tools/todo/set_todo_list.md",
            "cran_code/tools/todo",
        ),
        (
            "src/cran_code/tools/web/fetch.md",
            "cran_code/tools/web",
        ),
        (
            "src/cran_code/tools/web/search.md",
            "cran_code/tools/web",
        ),
    ]
    if has_rg_binary:
        expected_datas.append((f"src/cran_code/deps/bin/{rg_binary}", "cran_code/deps/bin"))

    assert sorted(datas) == sorted(expected_datas)


def test_pyinstaller_hiddenimports():
    from cran_code.utils.pyinstaller import hiddenimports

    assert sorted(hiddenimports) == snapshot(
        [
            "cran_code._build_info",
            "cran_code.cli.export",
            "cran_code.cli.info",
            "cran_code.cli.mcp",
            "cran_code.cli.plugin",
            "cran_code.cli.vis",
            "cran_code.cli.web",
            "cran_code.tools",
            "cran_code.tools.agent",
            "cran_code.tools.ask_user",
            "cran_code.tools.background",
            "cran_code.tools.display",
            "cran_code.tools.dmail",
            "cran_code.tools.file",
            "cran_code.tools.file.glob",
            "cran_code.tools.file.grep_local",
            "cran_code.tools.file.plan_mode",
            "cran_code.tools.file.read",
            "cran_code.tools.file.read_media",
            "cran_code.tools.file.replace",
            "cran_code.tools.file.utils",
            "cran_code.tools.file.write",
            "cran_code.tools.plan",
            "cran_code.tools.plan.enter",
            "cran_code.tools.plan.heroes",
            "cran_code.tools.shell",
            "cran_code.tools.test",
            "cran_code.tools.think",
            "cran_code.tools.todo",
            "cran_code.tools.utils",
            "cran_code.tools.web",
            "cran_code.tools.web.fetch",
            "cran_code.tools.web.search",
            "setproctitle",
        ]
    )


def test_pyinstaller_hiddenimports_include_lazy_cli_subcommands():
    from cran_code.cli._lazy_group import LazySubcommandGroup
    from cran_code.utils.pyinstaller import hiddenimports

    expected_hiddenimports = {
        module_name
        for module_name, _attribute_name, _help_text in LazySubcommandGroup.lazy_subcommands.values()
    }

    assert expected_hiddenimports <= set(hiddenimports)
