import pathlib
import subprocess

for plugin_path in pathlib.Path("plugins/").iterdir():
    assert plugin_path.exists()
    if not plugin_path.is_dir():
        continue
    plugin_name = plugin_path.name
    if plugin_name[0] == plugin_name[0].lower():
        continue
    subprocess.run(["pygettext3", "-D", "config.py", "plugin.py"], cwd=plugin_path)
