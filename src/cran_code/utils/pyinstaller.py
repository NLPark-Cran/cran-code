from __future__ import annotations

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

from cran_code.cli._lazy_group import LazySubcommandGroup

lazy_cli_hiddenimports = [
    module_name
    for module_name, _attribute_name, _help_text in (LazySubcommandGroup.lazy_subcommands.values())
]

hiddenimports = (
    collect_submodules("cran_code.tools")
    + lazy_cli_hiddenimports
    + ["setproctitle", "cran_code._build_info"]
)
datas = (
    collect_data_files(
        "cran_code",
        includes=[
            "agents/**/*.yaml",
            "agents/**/*.md",
            "deps/bin/**",
            "prompts/**/*.md",
            "skills/**",
            "tools/**/*.md",
            "web/static/**",
            "vis/static/**",
            "CHANGELOG.md",
        ],
        excludes=[
            "tools/*.md",
        ],
    )
    + collect_data_files(
        "dateparser",
        includes=["**/*.pkl"],
    )
    + collect_data_files(
        "fastmcp",
        includes=["../fastmcp-*.dist-info/*"],
    )
)
