Minecraft AddLog
================

Аддон для Python CMD 1.0 Beta, предназначенный для:
- просмотра логов Minecraft;
- поиска ошибок, исключений и предупреждений;
- управления установленными модами;
- создания резервных копий;
- диагностики Java, загрузчика и папки Minecraft;
- установки модов по прямым URL с CurseForge и Minecraft Inside.

УСТАНОВКА
---------
1. Скопируйте папку Minecraft-AddLog в:
   Python-CMD/addons/Minecraft-AddLog/
2. Выполните в Python CMD:
   addons-reload
3. Проверьте загрузку:
   addons-all

ВАЖНО
-----
Загрузчики принимают прямые ссылки на файлы .jar или .zip.
HTML-страница проекта CurseForge не является файлом мода.
Некоторые загрузки CurseForge могут требовать официальный API-ключ или открытие
страницы загрузки в браузере. Аддон не обходит ограничения сайтов.

ОСНОВНЫЕ КОМАНДЫ
----------------
CursForge downLoads URL
    Скачать прямой JAR/ZIP URL с разрешённых доменов CurseForge.

MinecraftIsland Downloads URL
    Скачать мод с minecraft-inside.ru.
    Пример:
    MinecraftIsland Downloads https://minecraft-inside.ru/download/123456/

ДОПОЛНИТЕЛЬНЫЕ 25 КОМАНД
-----------------------
1.  mc-log [КОЛИЧЕСТВО]         Последние строки latest.log.
2.  mc-log-live                 Просмотр latest.log в реальном времени.
3.  mc-log-errors               Ошибки, exception, caused by, fatal.
4.  mc-log-warnings             Предупреждения.
5.  mc-crash-list               Список crash-report файлов.
6.  mc-crash-show [ФАЙЛ]        Показать crash-report.
7.  mc-path                     Текущая папка Minecraft.
8.  mc-path-set "ПУТЬ"          Изменить папку Minecraft.
9.  mc-mods                     Список модов.
10. mc-mod-info ИМЯ             Размер, хеш, метаданные.
11. mc-mod-enable ИМЯ           Включить файл .disabled.
12. mc-mod-disable ИМЯ          Отключить мод.
13. mc-mod-remove ИМЯ           Убрать мод в локальный резерв.
14. mc-mod-restore ИМЯ          Вернуть удалённый мод.
15. mc-mod-duplicates           Найти возможные дубликаты.
16. mc-mod-hash ИМЯ             SHA-256 мода.
17. mc-mod-verify [ИМЯ]         Проверить целостность JAR.
18. mc-backup [ИМЯ]             Архивировать mods и config.
19. mc-backups                  Список резервных копий.
20. mc-backup-restore ИМЯ.zip   Восстановить backup.
21. mc-config-find ТЕКСТ        Искать текст в config.
22. mc-config-open ПУТЬ         Читать config-файл.
23. mc-loader                   Определить загрузчик модов.
24. mc-java                     Показать установленную Java.
25. mc-diagnose                 Общая диагностика.

БЕЗОПАСНОСТЬ
------------
- Разрешены только HTTP/HTTPS.
- Проверяется домен источника и домен после перенаправления.
- Максимальный размер загрузки: 512 МБ.
- Загруженный файл проверяется как ZIP/JAR.
- Восстановление backup защищено от выхода путей за папку Minecraft.
- Перед удалением мод переносится в data/removed_mods.

ЗАВИСИМОСТИ
-----------
Только стандартная библиотека Python 3.10+.
