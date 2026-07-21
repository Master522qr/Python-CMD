from pathlib import Path
import subprocess
import sys


def register(shell, addon_dir: Path, scripts_dir: Path):
    def hello(args):
        launcher = scripts_dir / "hello_script.py"
        subprocess.run([sys.executable, str(launcher), *args], check=False)

    shell.register("hello", hello, "Команда из аддона HelloAddon")
