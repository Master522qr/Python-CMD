from pathlib import Path
import sys

def register(shell, addon_dir: Path, scripts_dir: Path):
    # Импорт внутренней логики аддона из изолированной папки scripts/
    scripts_path = str(scripts_dir)
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)

    from core import MinecraftAddLog

    app = MinecraftAddLog(addon_dir=addon_dir, scripts_dir=scripts_dir)

    commands = {
        "CursForge": (
            app.curseforge,
            "CursForge downLoads URL — скачать и установить мод по прямой ссылке CurseForge"
        ),
        "MinecraftIsland": (
            app.minecraft_island,
            "MinecraftIsland Downloads URL — скачать мод с minecraft-inside.ru"
        ),
        "mc-log": (app.log_show, "Показать последние строки latest.log"),
        "mc-log-live": (app.log_live, "Следить за latest.log в реальном времени"),
        "mc-log-errors": (app.log_errors, "Показать ошибки и исключения из latest.log"),
        "mc-log-warnings": (app.log_warnings, "Показать предупреждения из latest.log"),
        "mc-crash-list": (app.crash_list, "Показать список crash-report файлов"),
        "mc-crash-show": (app.crash_show, "Открыть последний или указанный crash-report"),
        "mc-path": (app.path_show, "Показать текущий путь к папке Minecraft"),
        "mc-path-set": (app.path_set, "Установить путь к папке Minecraft"),
        "mc-mods": (app.mods_list, "Показать установленные моды"),
        "mc-mod-info": (app.mod_info, "Показать сведения о JAR-моде"),
        "mc-mod-enable": (app.mod_enable, "Включить отключённый мод"),
        "mc-mod-disable": (app.mod_disable, "Отключить мод без удаления"),
        "mc-mod-remove": (app.mod_remove, "Удалить мод с созданием резервной копии"),
        "mc-mod-restore": (app.mod_restore, "Восстановить мод из резервной копии"),
        "mc-mod-duplicates": (app.mod_duplicates, "Найти возможные дубликаты модов"),
        "mc-mod-hash": (app.mod_hash, "Рассчитать SHA-256 файла мода"),
        "mc-mod-verify": (app.mod_verify, "Проверить целостность JAR/ZIP мода"),
        "mc-backup": (app.backup_create, "Создать резервную копию mods/config"),
        "mc-backups": (app.backup_list, "Показать резервные копии"),
        "mc-backup-restore": (app.backup_restore, "Восстановить резервную копию"),
        "mc-config-find": (app.config_find, "Найти текст в config-файлах"),
        "mc-config-open": (app.config_open, "Показать содержимое config-файла"),
        "mc-loader": (app.loader_detect, "Определить Forge/Fabric/NeoForge/Quilt"),
        "mc-java": (app.java_info, "Показать версию и путь Java"),
        "mc-diagnose": (app.diagnose, "Выполнить базовую диагностику сборки"),
    }

    for name, (handler, description) in commands.items():
        shell.register(name, handler, description)
