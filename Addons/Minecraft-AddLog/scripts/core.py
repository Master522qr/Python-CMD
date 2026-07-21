from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Iterable


class MinecraftAddLog:
    MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
    ALLOWED_EXTENSIONS = {".jar", ".zip"}
    CF_HOSTS = {"curseforge.com", "www.curseforge.com", "edge.forgecdn.net", "mediafilez.forgecdn.net"}
    MI_HOSTS = {"minecraft-inside.ru", "www.minecraft-inside.ru"}

    def __init__(self, addon_dir: Path, scripts_dir: Path):
        self.addon_dir = Path(addon_dir)
        self.scripts_dir = Path(scripts_dir)
        self.data_dir = self.addon_dir / "data"
        self.backup_dir = self.data_dir / "backups"
        self.removed_dir = self.data_dir / "removed_mods"
        self.settings_file = self.data_dir / "settings.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.removed_dir.mkdir(parents=True, exist_ok=True)

    # ---------- Общие функции ----------

    def _settings(self) -> dict:
        if self.settings_file.exists():
            try:
                return json.loads(self.settings_file.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return {}

    def _save_settings(self, data: dict) -> None:
        self.settings_file.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def _default_minecraft_dir(self) -> Path:
        if sys.platform.startswith("win"):
            return Path(os.environ.get("APPDATA", Path.home())) / ".minecraft"
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "minecraft"
        return Path.home() / ".minecraft"

    def minecraft_dir(self) -> Path:
        saved = self._settings().get("minecraft_dir")
        return Path(saved).expanduser() if saved else self._default_minecraft_dir()

    def mods_dir(self) -> Path:
        path = self.minecraft_dir() / "mods"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @staticmethod
    def _need(args: list[str], usage: str) -> bool:
        if not args:
            print(f"Использование: {usage}")
            return False
        return True

    @staticmethod
    def _safe_name(name: str) -> str:
        name = urllib.parse.unquote(name)
        name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)
        return name.strip(" .") or "download.jar"

    def _download(self, url: str, allowed_hosts: set[str]) -> Path:
        parsed = urllib.parse.urlparse(url)
        host = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Разрешены только HTTP/HTTPS ссылки.")
        if host not in allowed_hosts:
            raise ValueError(f"Недопустимый домен: {host}")

        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Minecraft-AddLog/1.0"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            final_url = response.geturl()
            final_host = (urllib.parse.urlparse(final_url).hostname or "").lower()
            if final_host not in allowed_hosts:
                raise ValueError(f"Перенаправление на запрещённый домен: {final_host}")

            length = response.headers.get("Content-Length")
            if length and int(length) > self.MAX_DOWNLOAD_BYTES:
                raise ValueError("Файл превышает лимит 512 МБ.")

            content_disposition = response.headers.get("Content-Disposition", "")
            match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';]+)', content_disposition, re.I)
            filename = match.group(1) if match else Path(urllib.parse.urlparse(final_url).path).name
            filename = self._safe_name(filename)

            suffix = Path(filename).suffix.lower()
            if suffix not in self.ALLOWED_EXTENSIONS:
                content_type = response.headers.get("Content-Type", "").lower()
                if "text/html" in content_type:
                    raise ValueError(
                        "Ссылка ведёт на HTML-страницу, а не на файл мода. "
                        "Нужна прямая ссылка загрузки .jar/.zip."
                    )
                filename += ".jar"

            target = self.mods_dir() / filename
            temp = target.with_suffix(target.suffix + ".part")
            total = 0
            with temp.open("wb") as out:
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > self.MAX_DOWNLOAD_BYTES:
                        out.close()
                        temp.unlink(missing_ok=True)
                        raise ValueError("Файл превысил лимит 512 МБ.")
                    out.write(chunk)

            if target.exists():
                stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
                target = target.with_name(f"{target.stem}-{stamp}{target.suffix}")
            temp.replace(target)

        if not zipfile.is_zipfile(target):
            target.unlink(missing_ok=True)
            raise ValueError("Загруженный файл не является корректным JAR/ZIP архивом.")

        print(f"Установлено: {target}")
        print(f"SHA-256: {self._sha256(target)}")
        return target

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _find_mod(self, value: str, include_disabled: bool = True) -> Path | None:
        candidates = list(self.mods_dir().glob("*"))
        if not include_disabled:
            candidates = [p for p in candidates if p.suffix.lower() in self.ALLOWED_EXTENSIONS]
        exact = [p for p in candidates if p.name.lower() == value.lower()]
        if exact:
            return exact[0]
        partial = [p for p in candidates if value.lower() in p.name.lower()]
        if len(partial) == 1:
            return partial[0]
        if len(partial) > 1:
            print("Найдено несколько файлов:")
            for item in partial:
                print(" -", item.name)
        else:
            print("Мод не найден:", value)
        return None

    def _latest_log(self) -> Path:
        return self.minecraft_dir() / "logs" / "latest.log"

    @staticmethod
    def _tail(path: Path, count: int) -> list[str]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", errors="replace") as file:
            lines = file.readlines()
        return lines[-count:]

    # ---------- Загрузчики ----------

    def curseforge(self, args: list[str]) -> None:
        if not self._need(args, "CursForge downLoads URL"):
            return
        if args[0].lower() == "downloads":
            args = args[1:]
        if not self._need(args, "CursForge downLoads URL"):
            return
        try:
            self._download(args[0], self.CF_HOSTS)
        except Exception as error:
            print("Ошибка CurseForge:", error)
            print("Подсказка: используйте прямую ссылку на .jar/.zip; страница проекта не является файлом.")

    def minecraft_island(self, args: list[str]) -> None:
        if not self._need(args, "MinecraftIsland Downloads URL"):
            return
        if args[0].lower() == "downloads":
            args = args[1:]
        if not self._need(args, "MinecraftIsland Downloads URL"):
            return
        try:
            self._download(args[0], self.MI_HOSTS)
        except Exception as error:
            print("Ошибка Minecraft Inside:", error)
            print("Пример прямой ссылки: https://minecraft-inside.ru/download/123456/")

    # ---------- Логи и crash reports ----------

    def log_show(self, args: list[str]) -> None:
        count = int(args[0]) if args and args[0].isdigit() else 80
        log = self._latest_log()
        lines = self._tail(log, count)
        if not lines:
            print("Лог не найден или пуст:", log)
            return
        print("".join(lines), end="")

    def log_live(self, args: list[str]) -> None:
        log = self._latest_log()
        if not log.exists():
            print("Лог не найден:", log)
            return
        print("Наблюдение за логом. Для остановки нажмите Ctrl+C.")
        try:
            with log.open("r", encoding="utf-8", errors="replace") as file:
                file.seek(0, 2)
                while True:
                    line = file.readline()
                    if line:
                        print(line, end="")
                    else:
                        time.sleep(0.25)
        except KeyboardInterrupt:
            print("\nНаблюдение остановлено.")

    def _filtered_log(self, patterns: Iterable[str], count: int = 200) -> None:
        log = self._latest_log()
        if not log.exists():
            print("Лог не найден:", log)
            return
        rx = re.compile("|".join(patterns), re.I)
        with log.open("r", encoding="utf-8", errors="replace") as file:
            matched = [line for line in file if rx.search(line)]
        print("".join(matched[-count:]) if matched else "Совпадений не найдено.")

    def log_errors(self, args: list[str]) -> None:
        self._filtered_log([r"\berror\b", r"exception", r"caused by", r"\bfatal\b", r"crash"])

    def log_warnings(self, args: list[str]) -> None:
        self._filtered_log([r"\bwarn(?:ing)?\b"])

    def crash_list(self, args: list[str]) -> None:
        folder = self.minecraft_dir() / "crash-reports"
        reports = sorted(folder.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not reports:
            print("Crash-report файлы не найдены.")
            return
        for report in reports:
            print(datetime.fromtimestamp(report.stat().st_mtime).isoformat(sep=" ", timespec="seconds"), report.name)

    def crash_show(self, args: list[str]) -> None:
        folder = self.minecraft_dir() / "crash-reports"
        if args:
            report = folder / args[0]
        else:
            reports = sorted(folder.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
            report = reports[0] if reports else None
        if not report or not report.exists():
            print("Crash-report не найден.")
            return
        print(report.read_text(encoding="utf-8", errors="replace"))

    # ---------- Пути и моды ----------

    def path_show(self, args: list[str]) -> None:
        print(self.minecraft_dir())

    def path_set(self, args: list[str]) -> None:
        if not self._need(args, 'mc-path-set "ПУТЬ"'):
            return
        path = Path(" ".join(args)).expanduser().resolve()
        if not path.exists():
            print("Папка не существует:", path)
            return
        settings = self._settings()
        settings["minecraft_dir"] = str(path)
        self._save_settings(settings)
        print("Путь Minecraft сохранён:", path)

    def mods_list(self, args: list[str]) -> None:
        files = sorted(p for p in self.mods_dir().iterdir() if p.is_file())
        if not files:
            print("Папка mods пуста:", self.mods_dir())
            return
        for path in files:
            state = "OFF" if path.name.endswith(".disabled") else "ON "
            print(f"[{state}] {path.name} ({path.stat().st_size / 1024 / 1024:.2f} МБ)")

    def mod_info(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-info ИМЯ"):
            return
        path = self._find_mod(" ".join(args))
        if not path:
            return
        print("Файл:", path.name)
        print("Размер:", path.stat().st_size, "байт")
        print("Изменён:", datetime.fromtimestamp(path.stat().st_mtime))
        print("SHA-256:", self._sha256(path))
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as jar:
                names = set(jar.namelist())
                markers = [
                    "META-INF/mods.toml",
                    "fabric.mod.json",
                    "quilt.mod.json",
                    "META-INF/neoforge.mods.toml",
                    "mcmod.info",
                ]
                print("Метаданные:", ", ".join(x for x in markers if x in names) or "не найдены")

    def mod_disable(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-disable ИМЯ"):
            return
        path = self._find_mod(" ".join(args), include_disabled=False)
        if path:
            target = path.with_name(path.name + ".disabled")
            path.rename(target)
            print("Мод отключён:", target.name)

    def mod_enable(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-enable ИМЯ"):
            return
        path = self._find_mod(" ".join(args))
        if not path:
            return
        if not path.name.endswith(".disabled"):
            print("Мод уже включён:", path.name)
            return
        target = path.with_name(path.name[:-9])
        path.rename(target)
        print("Мод включён:", target.name)

    def mod_remove(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-remove ИМЯ"):
            return
        path = self._find_mod(" ".join(args))
        if not path:
            return
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = self.removed_dir / f"{stamp}__{path.name}"
        shutil.move(str(path), str(target))
        print("Мод перемещён в резерв:", target)

    def mod_restore(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-restore ИМЯ"):
            return
        value = " ".join(args).lower()
        matches = [p for p in self.removed_dir.iterdir() if value in p.name.lower()]
        if not matches:
            print("Резервная копия мода не найдена.")
            return
        source = sorted(matches, key=lambda p: p.stat().st_mtime, reverse=True)[0]
        original = source.name.split("__", 1)[-1]
        target = self.mods_dir() / original
        shutil.move(str(source), str(target))
        print("Мод восстановлен:", target)

    def mod_duplicates(self, args: list[str]) -> None:
        groups: dict[str, list[Path]] = {}
        for path in self.mods_dir().glob("*.jar"):
            key = re.sub(r"[-_.]?\d+(?:\.\d+)+(?:[-_.][A-Za-z0-9]+)*", "", path.stem).lower()
            groups.setdefault(key, []).append(path)
        found = False
        for key, files in groups.items():
            if len(files) > 1:
                found = True
                print(f"Возможный дубликат [{key}]:")
                for file in files:
                    print(" -", file.name)
        if not found:
            print("Возможные дубликаты не найдены.")

    def mod_hash(self, args: list[str]) -> None:
        if not self._need(args, "mc-mod-hash ИМЯ"):
            return
        path = self._find_mod(" ".join(args))
        if path:
            print(self._sha256(path))

    def mod_verify(self, args: list[str]) -> None:
        if args:
            paths = [self._find_mod(" ".join(args))]
        else:
            paths = list(self.mods_dir().glob("*.jar"))
        paths = [p for p in paths if p]
        bad = 0
        for path in paths:
            try:
                with zipfile.ZipFile(path) as archive:
                    error = archive.testzip()
                if error:
                    bad += 1
                    print("[BAD]", path.name, "повреждённый элемент:", error)
                else:
                    print("[ OK]", path.name)
            except zipfile.BadZipFile:
                bad += 1
                print("[BAD]", path.name, "не является ZIP/JAR")
        print(f"Проверено: {len(paths)}, ошибок: {bad}")

    # ---------- Backup/config/system ----------

    def backup_create(self, args: list[str]) -> None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        name = args[0] if args else f"minecraft-{stamp}"
        target = self.backup_dir / self._safe_name(name)
        target = target.with_suffix(".zip")
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for folder_name in ("mods", "config"):
                folder = self.minecraft_dir() / folder_name
                if folder.exists():
                    for path in folder.rglob("*"):
                        if path.is_file():
                            archive.write(path, path.relative_to(self.minecraft_dir()))
        print("Резервная копия создана:", target)

    def backup_list(self, args: list[str]) -> None:
        backups = sorted(self.backup_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            print("Резервных копий нет.")
            return
        for path in backups:
            print(path.name, f"({path.stat().st_size / 1024 / 1024:.2f} МБ)")

    def backup_restore(self, args: list[str]) -> None:
        if not self._need(args, "mc-backup-restore ИМЯ.zip"):
            return
        source = self.backup_dir / args[0]
        if not source.exists() or not zipfile.is_zipfile(source):
            print("Резервная копия не найдена или повреждена.")
            return
        with zipfile.ZipFile(source) as archive:
            for member in archive.infolist():
                destination = (self.minecraft_dir() / member.filename).resolve()
                base = self.minecraft_dir().resolve()
                if base not in destination.parents and destination != base:
                    raise ValueError("Небезопасный путь внутри архива.")
            archive.extractall(self.minecraft_dir())
        print("Резервная копия восстановлена:", source.name)

    def config_find(self, args: list[str]) -> None:
        if not self._need(args, "mc-config-find ТЕКСТ"):
            return
        query = " ".join(args).lower()
        folder = self.minecraft_dir() / "config"
        found = 0
        for path in folder.rglob("*") if folder.exists() else []:
            if path.is_file() and path.stat().st_size < 5 * 1024 * 1024:
                try:
                    for number, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                        if query in line.lower():
                            print(f"{path.relative_to(folder)}:{number}: {line.strip()}")
                            found += 1
                            if found >= 200:
                                print("Показаны первые 200 совпадений.")
                                return
                except OSError:
                    pass
        if not found:
            print("Совпадений не найдено.")

    def config_open(self, args: list[str]) -> None:
        if not self._need(args, "mc-config-open ОТНОСИТЕЛЬНЫЙ_ПУТЬ"):
            return
        base = (self.minecraft_dir() / "config").resolve()
        path = (base / " ".join(args)).resolve()
        if base not in path.parents:
            print("Доступ разрешён только внутри папки config.")
            return
        if not path.exists() or not path.is_file():
            print("Файл не найден:", path)
            return
        print(path.read_text(encoding="utf-8", errors="replace"))

    def loader_detect(self, args: list[str]) -> None:
        versions = self.minecraft_dir() / "versions"
        names = [p.name.lower() for p in versions.iterdir()] if versions.exists() else []
        joined = "\n".join(names + [p.name.lower() for p in self.mods_dir().glob("*")])
        detected = [name for name in ("neoforge", "forge", "fabric", "quilt") if name in joined]
        print("Обнаруженные загрузчики:", ", ".join(detected) if detected else "не определены")

    def java_info(self, args: list[str]) -> None:
        java = shutil.which("java")
        print("Java:", java or "не найдена в PATH")
        if java:
            subprocess.run([java, "-version"], check=False)

    def diagnose(self, args: list[str]) -> None:
        mc = self.minecraft_dir()
        print("Minecraft:", mc, "[OK]" if mc.exists() else "[НЕ НАЙДЕН]")
        print("mods:", self.mods_dir())
        jars = list(self.mods_dir().glob("*.jar"))
        print("Активных JAR-модов:", len(jars))
        print("latest.log:", "[OK]" if self._latest_log().exists() else "[НЕТ]")
        crash_dir = mc / "crash-reports"
        crashes = list(crash_dir.glob("*.txt")) if crash_dir.exists() else []
        print("Crash reports:", len(crashes))
        java = shutil.which("java")
        print("Java:", java or "[НЕ НАЙДЕНА]")
        bad = [p.name for p in jars if not zipfile.is_zipfile(p)]
        print("Повреждённые JAR:", ", ".join(bad) if bad else "нет")
        self.loader_detect([])
