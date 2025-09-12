#!/usr/bin/env python3

import ast
from pathlib import Path
import json
import re
import sys

pyprojectTemplate = '''
[build-system]
requires = ["setuptools"]

[project]
name = "limnoria-%(name_lowercase)s"
version = "%(version)s"
authors = [
%(authors)s
]
readme = "README.md"
dependencies = [
    "limnoria",%(dependencies)s
]
classifiers = [
    'Environment :: Plugins',
    'Programming Language :: Python :: 3',
    'Topic :: Communications :: Chat',
]

[project.entry-points.'limnoria.plugins']
%(name)s = "limnoria_%(name_lowercase)s"

[tool.setuptools.package-dir]
"limnoria_%(name_lowercase)s" = "."
"limnoria_%(name_lowercase)s.local" = "local/"

[tool.setuptools.package-data]
"limnoria_%(name_lowercase)s" = ["locales/*.po"]
'''.lstrip()

def convert_plugin(path: Path) -> None:
    path = path.resolve()
    assert path.is_dir(), path
    name = path.name

    setuppy_path = path / "setup.py"
    if setuppy_path.exists():
        setuppy = setuppy_path.read_text()
        setuppy = "\n".join(line for line in setuppy.split("\n") if not line.startswith("#")).strip()

        pattern = (
            rf"from supybot.setup import plugin_setup\n"
            rf"\n"
            rf"plugin_setup\(\n"
            rf"""\s*['"]{name}['"],\n"""
            rf"(.*)"
            rf"\)"
        )
        if not (match := re.match(pattern, setuppy, re.DOTALL)):
            raise NotImplementedError("unknown setup.py template")
        setuppy_remainder = match.group(1)

        if not setuppy_remainder:
            dependencies = ""
        elif m := re.match(r"install_requires=(\[[^\]]+\]),?", setuppy_remainder.strip()):
            dependencies = "\n".join(
                f'\n    {json.dumps(dep)},' for dep in ast.literal_eval(m.group(1))
            )
        else:
            raise NotImplementedError(f"setup.py optional arguments: {setuppy_remainder!r}")
    else:
        dependencies = ""


    pluginpy = (path / "plugin.py").read_text()
    authors = "\n".join(
        '    { name = "%s" }' % author
        for author in re.findall(
            r"^# Copyright \(c\) [0-9-]+, (.+)$", pluginpy, re.MULTILINE
        )
    )

    initpy = (path / "__init__.py").read_text()
    if not (m := re.search(r'^__version__ = "(.*)"\s*(#.*)?$', initpy, re.MULTILINE)):
        raise NotImplementedError("Could not parse __init__.py")
    version = m.group(1) or "0.0.0"

    pyproject = pyprojectTemplate % {
        "authors": authors,
        "dependencies": dependencies,
        "name": name,
        "name_lowercase": name.lower(),
        "version": version,
    }
    (path / "pyproject.toml").write_text(pyproject)

def main():
    (exe, *plugin_paths) = sys.argv
    if not plugin_paths:
        print(
            f"Syntax: {exe} <path/to/Plugin1> [<path/to/Plugin2> [...]]",
            file=sys.stderr
        )
        exit(1)
    for plugin_path in plugin_paths:
        try:
            convert_plugin(Path(plugin_path))
        except NotImplementedError as e:
            print(f"Skipping {plugin_path}: {e}")

if __name__ == "__main__":
    main()
