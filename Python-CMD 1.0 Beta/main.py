from __future__ import annotations

import ctypes
import datetime as dt
import getpass
import hashlib
import json
import os
import platform
import re
import shlex
import shutil
import socket
import subprocess
import sys
import textwrap
import time
import urllib.parse
import webbrowser
from pathlib import Path
from typing import Callable

APP_NAME = "Python CMD"
VERSION = "1.0 beta"
AUTHOR = "t.me/Py_CMD"
GITHUB = "https://github.com/Master522qr/Python-CMD/tree/main?tab=readme-ov-file"
BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
ADDONS_DIR = BASE_DIR / "addons"
SCRIPTS_DIR = BASE_DIR / "scripts"

DEFAULT_CONFIG = {
    "language": "EU",
    "prompt": "PY-CMD> ",
    "text_color": "default",
    "allow_shell": False
}

COLORS = {
    "default": "\033[0m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
}

MESSAGES = {
    "RU": {
        "ready": "Python is running CMD\nYour PC is now ready",
        "unknown": "Неизвестная команда. Введите help.",
        "admin_yes": "Права администратора: да",
        "admin_no": "Права администратора: нет",
        "bye": "Завершение работы.",
        "need_arg": "Не хватает аргумента.",
        "not_found": "Не найдено.",
        "disabled": "Функция отключена в config.json.",
    },
    "EU": {
        "ready": "Python is running CMD\nYour PC is now ready",
        "unknown": "Unknown command. Type help.",
        "admin_yes": "Administrator privileges: yes",
        "admin_no": "Administrator privileges: no",
        "bye": "Goodbye.",
        "need_arg": "Missing argument.",
        "not_found": "Not found.",
        "disabled": "This feature is disabled in config.json.",
    }
}


def enable_ansi() -> None:
    if os.name == "nt":
        os.system("")


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        CONFIG_FILE.write_text(json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False), encoding="utf-8")
        return DEFAULT_CONFIG.copy()
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        cfg = DEFAULT_CONFIG.copy()
    for key, value in DEFAULT_CONFIG.items():
        cfg.setdefault(key, value)
    return cfg


def save_config(cfg: dict) -> None:
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


def is_admin() -> bool:
    try:
        if os.name == "nt":
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def human_size(value: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024
    return str(value)


def terminal_width() -> int:
    return max(40, shutil.get_terminal_size(fallback=(80, 24)).columns)


class CenteredWriter:
    """Centers every line printed by Python CMD."""

    def __init__(self, stream):
        self.stream = stream
        self.buffer = ""

    def write(self, value):
        value = str(value)
        self.buffer += value
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            self.stream.write(line.center(terminal_width()) + "\n")
        return len(value)

    def flush(self):
        if self.buffer:
            self.stream.write(self.buffer.center(terminal_width()))
            self.buffer = ""
        self.stream.flush()

    def isatty(self):
        return self.stream.isatty()

    @property
    def encoding(self):
        return getattr(self.stream, "encoding", "utf-8")


class Shell:
    def __init__(self) -> None:
        enable_ansi()
        self.config = load_config()
        self.commands: dict[str, tuple[Callable[[list[str]], None], str]] = {}
        self.running = True
        self.history: list[str] = []
        self.loaded_addons: list[str] = []
        self.register_builtin_commands()
        self.load_addons()

    @property
    def lang(self) -> str:
        return self.config.get("language", "RU")

    def t(self, key: str) -> str:
        return MESSAGES.get(self.lang, MESSAGES["RU"]).get(key, key)

    def register(self, name: str, handler: Callable[[list[str]], None], description: str) -> None:
        self.commands[name.lower()] = (handler, description)

    def center_print(self, text: str = "") -> None:
        width = terminal_width()
        for line in str(text).splitlines() or [""]:
            print(line.center(width))

    def banner(self) -> None:
        self.center_print(self.t("ready"))
        self.center_print(f"[author : {AUTHOR}]")
        self.center_print(f"Our GitHub - {GITHUB}")
        self.center_print("Type help / Введите help")
        print()

    def run(self) -> None:
        self.banner()
        while self.running:
            color = COLORS.get(self.config.get("text_color", "default"), COLORS["default"])
            reset = COLORS["default"]
            try:
                prompt = self.config.get("prompt", "PY-CMD> ")
                raw = input(f"{color}{prompt}{reset}").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not raw:
                continue
            self.history.append(raw)
            self.execute(raw)
        print(self.t("bye"))

    def execute(self, raw: str) -> None:
        try:
            parts = shlex.split(raw, posix=os.name != "nt")
        except ValueError as exc:
            print(f"Parse error: {exc}")
            return
        if not parts:
            return
        command = parts[0].lower()
        args = parts[1:]

        if command.endswith(".js"):
            self.run_js_file(command, args)
            return

        item = self.commands.get(command)
        if item:
            try:
                item[0](args)
            except Exception as exc:
                print(f"Command error: {exc}")
            return

        if self.config.get("allow_shell"):
            subprocess.run(raw, shell=True, check=False)
        else:
            print(self.t("unknown"))

    def register_builtin_commands(self) -> None:
        items = [
            ("help", self.cmd_help, "Показать список команд"),
            ("py-cmd", self.cmd_info, "Информация о готовности и версии"),
            ("ccb-bit", self.cmd_pc_info, "Основная информация о компьютере"),
            ("wa-fi_info", self.cmd_wifi_info, "Безопасная информация о Wi‑Fi"),
            ("fon-app", self.cmd_processes, "Список запущенных процессов"),
            ("lang-ru", lambda a: self.cmd_language(["RU"]), "Установить русский язык"),
            ("lang-eu", lambda a: self.cmd_language(["EU"]), "Установить английский язык"),
            ("addons-all", self.cmd_addons, "Показать загруженные аддоны"),
            ("addons-reload", self.cmd_addons_reload, "Перезагрузить аддоны"),
            ("vap", self.cmd_vap, "Клонировать публичный GitHub-репозиторий"),
            ("text", self.cmd_text, "Цвет текста: text style COLOR"),
            ("exit", self.cmd_exit, "Выйти"),
            ("clear", self.cmd_clear, "Очистить экран"),
            ("cls", self.cmd_clear, "Очистить экран"),
            ("echo", self.cmd_echo, "Вывести текст"),
            ("date", self.cmd_date, "Текущая дата"),
            ("time", self.cmd_time, "Текущее время"),
            ("datetime", self.cmd_datetime, "Дата и время"),
            ("whoami", self.cmd_whoami, "Текущий пользователь"),
            ("hostname", self.cmd_hostname, "Имя компьютера"),
            ("os-info", self.cmd_os_info, "Информация об ОС"),
            ("cpu-info", self.cmd_cpu_info, "Информация о процессоре"),
            ("memory-info", self.cmd_memory_info, "Информация о памяти"),
            ("disk-info", self.cmd_disk_info, "Информация о дисках"),
            ("ip-local", self.cmd_ip_local, "Локальный IP"),
            ("dns-lookup", self.cmd_dns_lookup, "DNS-запрос домена"),
            ("ping", self.cmd_ping, "Проверить доступность узла"),
            ("ports", self.cmd_ports, "Показать локальные слушающие порты"),
            ("pwd", self.cmd_pwd, "Текущая папка"),
            ("cd", self.cmd_cd, "Сменить папку"),
            ("ls", self.cmd_ls, "Список файлов"),
            ("dir", self.cmd_ls, "Список файлов"),
            ("tree", self.cmd_tree, "Дерево каталогов"),
            ("mkdir", self.cmd_mkdir, "Создать каталог"),
            ("touch", self.cmd_touch, "Создать пустой файл"),
            ("cat", self.cmd_cat, "Показать текстовый файл"),
            ("write", self.cmd_write, "Записать текст в файл"),
            ("append", self.cmd_append, "Добавить текст в файл"),
            ("copy", self.cmd_copy, "Копировать файл"),
            ("move", self.cmd_move, "Переместить файл"),
            ("rename", self.cmd_move, "Переименовать файл"),
            ("delete", self.cmd_delete, "Удалить файл"),
            ("rmdir", self.cmd_rmdir, "Удалить пустую папку"),
            ("find", self.cmd_find, "Найти файлы"),
            ("file-info", self.cmd_file_info, "Информация о файле"),
            ("hash", self.cmd_hash, "SHA-256 файла или текста"),
            ("open", self.cmd_open, "Открыть файл или URL"),
            ("env", self.cmd_env, "Показать переменные окружения"),
            ("env-get", self.cmd_env_get, "Получить переменную окружения"),
            ("python-version", self.cmd_python_version, "Версия Python"),
            ("node-version", self.cmd_node_version, "Версия Node.js"),
            ("run-py", self.cmd_run_py, "Запустить локальный .py файл"),
            ("run-js", self.cmd_run_js, "Запустить локальный .js файл"),
            ("calc", self.cmd_calc, "Безопасный калькулятор"),
            ("random", self.cmd_random, "Случайное число"),
            ("uuid", self.cmd_uuid, "Создать UUID"),
            ("base64-encode", self.cmd_b64e, "Кодировать Base64"),
            ("base64-decode", self.cmd_b64d, "Декодировать Base64"),
            ("url-encode", self.cmd_urle, "URL-кодирование"),
            ("url-decode", self.cmd_urld, "URL-декодирование"),
            ("json-format", self.cmd_json_format, "Форматировать JSON-файл"),
            ("history", self.cmd_history, "История команд"),
            ("uptime", self.cmd_uptime, "Время работы системы"),
            ("admin-check", self.cmd_admin_check, "Проверить права администратора"),
            ("config-show", self.cmd_config_show, "Показать конфигурацию"),
            ("prompt-set", self.cmd_prompt_set, "Изменить приглашение"),
            ("shell-on", self.cmd_shell_on, "Разрешить системные команды"),
            ("shell-off", self.cmd_shell_off, "Запретить системные команды"),
            ("github", lambda a: webbrowser.open(GITHUB), "Открыть GitHub"),
            ("telegram", lambda a: webbrowser.open("https://t.me/Py_CMD"), "Открыть Telegram"),
        ]
        for name, fn, desc in items:
            self.register(name, fn, desc)

    def load_addons(self) -> None:
        """
        Каждый аддон находится в своей папке:

        addons/
          AddonName/
            addon.py
            scripts/
            README.txt

        addon.py автоматически подключается при запуске Python CMD.
        """
        ADDONS_DIR.mkdir(exist_ok=True)
        self.loaded_addons = []

        for addon_dir in sorted(ADDONS_DIR.iterdir()):
            if not addon_dir.is_dir() or addon_dir.name.startswith("_"):
                continue

            entry_file = addon_dir / "addon.py"
            scripts_dir = addon_dir / "scripts"

            if not entry_file.exists():
                print(f"Addon {addon_dir.name}: addon.py not found")
                continue

            scripts_dir.mkdir(exist_ok=True)

            try:
                namespace = {
                    "__file__": str(entry_file),
                    "__name__": f"addon_{addon_dir.name}",
                    "ADDON_DIR": addon_dir,
                    "SCRIPTS_DIR": scripts_dir,
                }
                exec(entry_file.read_text(encoding="utf-8"), namespace)
                register = namespace.get("register")

                if not callable(register):
                    print(
                        f"Addon {addon_dir.name}: register(shell, addon_dir, scripts_dir) not found"
                    )
                    continue

                register(self, addon_dir, scripts_dir)
                self.loaded_addons.append(addon_dir.name)
                print(f"Addon loaded: {addon_dir.name}")
            except Exception as exc:
                print(f"Addon {addon_dir.name}: {exc}")

    def need(self, args: list[str], count: int = 1) -> bool:
        if len(args) < count:
            print(self.t("need_arg"))
            return False
        return True

    def cmd_help(self, args):
        width = max(len(name) for name in self.commands)
        for name in sorted(self.commands):
            print(f"{name.ljust(width)}  {self.commands[name][1]}")

    def cmd_info(self, args):
        print(f"{APP_NAME} {VERSION}")
        print("Status: READY")
        print(f"Python: {platform.python_version()}")

    def cmd_pc_info(self, args):
        print(f"OS: {platform.platform()}")
        print(f"Architecture: {platform.machine()}")
        print(f"Processor: {platform.processor() or 'unknown'}")
        print(f"Hostname: {socket.gethostname()}")
        print(f"User: {getpass.getuser()}")
        print(f"Python: {platform.python_version()}")
        self.cmd_memory_info([])
        self.cmd_disk_info([])

    def cmd_wifi_info(self, args):
        print("Показывается только безопасная информация о подключении; сохранённые пароли не извлекаются.")
        if os.name == "nt":
            subprocess.run(["netsh", "wlan", "show", "interfaces"], check=False)
        else:
            tool = shutil.which("nmcli")
            if tool:
                subprocess.run([tool, "-f", "ACTIVE,SSID,SIGNAL,SECURITY", "dev", "wifi"], check=False)
            else:
                print("nmcli не найден.")

    def cmd_processes(self, args):
        if os.name == "nt":
            subprocess.run(["tasklist"], check=False)
        else:
            subprocess.run(["ps", "-eo", "pid,user,comm,%cpu,%mem"], check=False)

    def cmd_language(self, args):
        lang = args[0].upper()
        if lang not in {"RU", "EU"}:
            print("Use RU or EU")
            return
        self.config["language"] = lang
        save_config(self.config)
        print(f"Language: {lang}. Restart is optional.")

    def cmd_addons(self, args):
        if self.loaded_addons:
            for name in self.loaded_addons:
                print(name)
        else:
            print("No addons.")

    def cmd_addons_reload(self, args):
        self.load_addons()
        print("Addons reloaded.")

    def cmd_vap(self, args):
        if not self.need(args):
            print("vap https://github.com/OWNER/REPO [folder]")
            return
        url = args[0]
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.netloc.lower() != "github.com":
            print("Разрешены только публичные HTTPS-ссылки github.com.")
            return
        if not shutil.which("git"):
            print("Git is not installed.")
            return
        target = args[1] if len(args) > 1 else Path(parsed.path).stem
        answer = input(f"Clone {url} into {target}? [y/N]: ").strip().lower()
        if answer == "y":
            subprocess.run(["git", "clone", "--depth", "1", url, target], check=False)

    def cmd_text(self, args):
        if len(args) < 2 or args[0].lower() != "style":
            print("text style red")
            print("Colors:", ", ".join(COLORS))
            return
        color = args[1].lower()
        if color not in COLORS:
            print("Unknown color.")
            return
        self.config["text_color"] = color
        save_config(self.config)
        print(f"{COLORS[color]}Text color changed.{COLORS['default']}")

    def cmd_exit(self, args): self.running = False
    def cmd_clear(self, args): os.system("cls" if os.name == "nt" else "clear")
    def cmd_echo(self, args): print(" ".join(args))
    def cmd_date(self, args): print(dt.date.today().isoformat())
    def cmd_time(self, args): print(dt.datetime.now().strftime("%H:%M:%S"))
    def cmd_datetime(self, args): print(dt.datetime.now().isoformat(sep=" ", timespec="seconds"))
    def cmd_whoami(self, args): print(getpass.getuser())
    def cmd_hostname(self, args): print(socket.gethostname())
    def cmd_os_info(self, args): print(platform.platform())
    def cmd_cpu_info(self, args):
        print(platform.processor() or platform.machine())
        print(f"Cores: {os.cpu_count()}")

    def cmd_memory_info(self, args):
        try:
            if os.name == "nt":
                import ctypes
                class MEMORYSTATUSEX(ctypes.Structure):
                    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                                ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
                stat = MEMORYSTATUSEX()
                stat.dwLength = ctypes.sizeof(stat)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
                print(f"RAM total: {human_size(stat.ullTotalPhys)}")
                print(f"RAM free: {human_size(stat.ullAvailPhys)}")
            else:
                mem = {}
                for line in Path("/proc/meminfo").read_text().splitlines():
                    key, value = line.split(":", 1)
                    mem[key] = int(value.strip().split()[0]) * 1024
                print(f"RAM total: {human_size(mem['MemTotal'])}")
                print(f"RAM available: {human_size(mem['MemAvailable'])}")
        except Exception as exc:
            print(exc)

    def cmd_disk_info(self, args):
        roots = [Path(p.anchor) for p in [Path.cwd()]]
        if os.name == "nt":
            roots = [Path(f"{c}:\\") for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if Path(f"{c}:\\").exists()]
        for root in roots:
            total, used, free = shutil.disk_usage(root)
            print(f"{root}: total {human_size(total)}, used {human_size(used)}, free {human_size(free)}")

    def cmd_ip_local(self, args):
        try:
            print(socket.gethostbyname(socket.gethostname()))
        except socket.gaierror:
            print("127.0.0.1")

    def cmd_dns_lookup(self, args):
        if self.need(args):
            for item in socket.getaddrinfo(args[0], None):
                print(item[4][0])

    def cmd_ping(self, args):
        if self.need(args):
            flag = "-n" if os.name == "nt" else "-c"
            subprocess.run(["ping", flag, "4", args[0]], check=False)

    def cmd_ports(self, args):
        if os.name == "nt":
            subprocess.run(["netstat", "-ano"], check=False)
        else:
            subprocess.run(["ss", "-lntup"], check=False)

    def cmd_pwd(self, args): print(Path.cwd())
    def cmd_cd(self, args):
        if self.need(args):
            os.chdir(Path(args[0]).expanduser())

    def cmd_ls(self, args):
        path = Path(args[0]).expanduser() if args else Path.cwd()
        for p in sorted(path.iterdir(), key=lambda x: (x.is_file(), x.name.lower())):
            mark = "/" if p.is_dir() else ""
            print(p.name + mark)

    def cmd_tree(self, args):
        root = Path(args[0]).expanduser() if args else Path.cwd()
        max_depth = int(args[1]) if len(args) > 1 else 3
        print(root)
        for p in sorted(root.rglob("*")):
            try:
                depth = len(p.relative_to(root).parts)
            except ValueError:
                continue
            if depth <= max_depth:
                print("  " * depth + p.name + ("/" if p.is_dir() else ""))

    def cmd_mkdir(self, args):
        if self.need(args):
            Path(args[0]).expanduser().mkdir(parents=True, exist_ok=True)

    def cmd_touch(self, args):
        if self.need(args):
            Path(args[0]).expanduser().touch(exist_ok=True)

    def cmd_cat(self, args):
        if self.need(args):
            print(Path(args[0]).expanduser().read_text(encoding="utf-8", errors="replace"))

    def cmd_write(self, args):
        if self.need(args, 2):
            Path(args[0]).expanduser().write_text(" ".join(args[1:]), encoding="utf-8")

    def cmd_append(self, args):
        if self.need(args, 2):
            with Path(args[0]).expanduser().open("a", encoding="utf-8") as f:
                f.write(" ".join(args[1:]) + "\n")

    def cmd_copy(self, args):
        if self.need(args, 2):
            shutil.copy2(Path(args[0]).expanduser(), Path(args[1]).expanduser())

    def cmd_move(self, args):
        if self.need(args, 2):
            shutil.move(str(Path(args[0]).expanduser()), str(Path(args[1]).expanduser()))

    def cmd_delete(self, args):
        if self.need(args):
            p = Path(args[0]).expanduser()
            if p.is_file():
                p.unlink()
            else:
                print("Use rmdir for directories.")

    def cmd_rmdir(self, args):
        if self.need(args):
            Path(args[0]).expanduser().rmdir()

    def cmd_find(self, args):
        if self.need(args):
            pattern = args[0].lower()
            root = Path(args[1]).expanduser() if len(args) > 1 else Path.cwd()
            for p in root.rglob("*"):
                if pattern in p.name.lower():
                    print(p)

    def cmd_file_info(self, args):
        if self.need(args):
            p = Path(args[0]).expanduser()
            st = p.stat()
            print(f"Path: {p.resolve()}")
            print(f"Type: {'directory' if p.is_dir() else 'file'}")
            print(f"Size: {human_size(st.st_size)}")
            print(f"Modified: {dt.datetime.fromtimestamp(st.st_mtime)}")

    def cmd_hash(self, args):
        if self.need(args):
            p = Path(args[0]).expanduser()
            if p.is_file():
                h = hashlib.sha256()
                with p.open("rb") as f:
                    for chunk in iter(lambda: f.read(65536), b""):
                        h.update(chunk)
                print(h.hexdigest())
            else:
                print(hashlib.sha256(" ".join(args).encode()).hexdigest())

    def cmd_open(self, args):
        if self.need(args):
            target = args[0]
            if re.match(r"^https?://", target):
                webbrowser.open(target)
            else:
                p = str(Path(target).expanduser().resolve())
                if os.name == "nt":
                    os.startfile(p)
                elif sys.platform == "darwin":
                    subprocess.run(["open", p], check=False)
                else:
                    subprocess.run(["xdg-open", p], check=False)

    def cmd_env(self, args):
        for key in sorted(os.environ):
            print(f"{key}={os.environ[key]}")

    def cmd_env_get(self, args):
        if self.need(args):
            print(os.environ.get(args[0], ""))

    def cmd_python_version(self, args): print(platform.python_version())
    def cmd_node_version(self, args):
        node = shutil.which("node")
        subprocess.run([node, "--version"], check=False) if node else print("Node.js not installed.")

    def safe_script(self, name: str, suffix: str) -> Path | None:
        p = Path(name).expanduser().resolve()
        if p.suffix.lower() != suffix:
            print(f"Expected {suffix} file.")
            return None
        if not p.exists():
            print(self.t("not_found"))
            return None
        return p

    def cmd_run_py(self, args):
        if self.need(args):
            p = self.safe_script(args[0], ".py")
            if p:
                subprocess.run([sys.executable, str(p), *args[1:]], check=False)

    def run_js_file(self, file_name: str, args: list[str]):
        self.cmd_run_js([file_name, *args])

    def cmd_run_js(self, args):
        if self.need(args):
            node = shutil.which("node")
            if not node:
                print("Node.js not installed.")
                return
            p = self.safe_script(args[0], ".js")
            if p:
                subprocess.run([node, str(p), *args[1:]], check=False)

    def cmd_calc(self, args):
        if not self.need(args):
            return
        expr = " ".join(args)
        if not re.fullmatch(r"[0-9+\-*/%().\s]+", expr):
            print("Only numbers and + - * / % ( ) are allowed.")
            return
        print(eval(expr, {"__builtins__": {}}, {}))

    def cmd_random(self, args):
        import random
        a, b = (int(args[0]), int(args[1])) if len(args) >= 2 else (0, 100)
        print(random.randint(a, b))

    def cmd_uuid(self, args):
        import uuid
        print(uuid.uuid4())

    def cmd_b64e(self, args):
        import base64
        print(base64.b64encode(" ".join(args).encode()).decode())

    def cmd_b64d(self, args):
        import base64
        print(base64.b64decode(" ".join(args)).decode(errors="replace"))

    def cmd_urle(self, args): print(urllib.parse.quote(" ".join(args)))
    def cmd_urld(self, args): print(urllib.parse.unquote(" ".join(args)))

    def cmd_json_format(self, args):
        if self.need(args):
            p = Path(args[0]).expanduser()
            data = json.loads(p.read_text(encoding="utf-8"))
            p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            print("Formatted.")

    def cmd_history(self, args):
        for i, item in enumerate(self.history, 1):
            print(f"{i}: {item}")

    def cmd_uptime(self, args):
        if os.name == "nt":
            subprocess.run(["net", "statistics", "workstation"], check=False)
        else:
            print(Path("/proc/uptime").read_text().split()[0] + " seconds")

    def cmd_admin_check(self, args):
        return

    def cmd_config_show(self, args):
        print(json.dumps(self.config, indent=2, ensure_ascii=False))

    def cmd_prompt_set(self, args):
        if self.need(args):
            self.config["prompt"] = " ".join(args) + " "
            save_config(self.config)

    def cmd_shell_on(self, args):
        answer = input("Allow arbitrary OS shell commands? [y/N]: ").strip().lower()
        if answer == "y":
            self.config["allow_shell"] = True
            save_config(self.config)
            print("Shell commands enabled.")

    def cmd_shell_off(self, args):
        self.config["allow_shell"] = False
        save_config(self.config)
        print("Shell commands disabled.")


if __name__ == "__main__":
    Shell().run()
