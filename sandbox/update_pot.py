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

    for po_path in plugin_path.glob("locales/*.po"):
        subprocess.run(["msgmerge", "--quiet", "--update", po_path, plugin_path / "messages.pot"], stdout=subprocess.DEVNULL)

core_files = pathlib.Path("src/").glob("**/*.py")
subprocess.run(["pygettext3", "-p", "locales/", *core_files])

pot_path = pathlib.Path("locales/messages.pot")
for po_path in pathlib.Path("").glob("locales/*.po"):
    subprocess.run(["msgmerge", "--quiet", "--update", po_path, pot_path], stdout=subprocess.DEVNULL)
