# Python CMD

**Python CMD 1.0 beta** — расширяемая командная оболочка на Python с поддержкой команд, аддонов и локальных JavaScript-файлов.

После запуска отображается:

```text
Python is running CMD
Your PC is now ready
[author : t.me/Py_CMD]
Our GitHub - https://github.com/Master522qr/Python-CMD/tree/main?tab=readme-ov-file
```

## Возможности

- Более 60 встроенных команд.
- Английский интерфейс по умолчанию; русский включается командой `Lang-RU`.
- Поддержка аддонов на Python.
- Запуск `.js` через установленный Node.js.
- Безопасная информация о системе, сети, дисках и процессах.
- Работа с файлами и папками.
- Цветное приглашение командной строки.
- Установка публичных GitHub-репозиториев через `VAP`.
- Конфигурация в `config.json`.

## Требования

- Python 3.10 или новее.
- Windows 10/11, Linux или macOS.
- Git — только для команды `VAP`.
- Node.js — только для запуска `.js`.

## Запуск

```bash
python main.py
```

Windows:

```bat
py main.py
```

## Права администратора

Python CMD **не обходит защиту системы** и не повышает права скрытно.

Для запуска с правами администратора на Windows:

1. Откройте PowerShell или CMD через «Запуск от имени администратора».
2. Перейдите в папку проекта.
3. Выполните `py main.py`.

Проверить права:

```text
admin-check
```

Это безопаснее автоматического повышения прав и не вызывает неожиданные системные изменения.

## Основные команды

```text
PY-CMD
CCB-BIT
WA-FI_Info
FON-APP
Lang-RU
Lang-EU
Addons-all
Addons-reload
VAP
Text style red
help
exit
```

### `PY-CMD`

Показывает состояние оболочки, версию Python CMD, версию Python и наличие прав администратора.

### `CCB-BIT`

Показывает общую информацию о компьютере: ОС, архитектуру, процессор, имя компьютера, пользователя, память и диски.

### `WA-FI_Info`

Показывает безопасную информацию о текущем Wi‑Fi-подключении и доступных сетях.

Команда намеренно **не извлекает сохранённые пароли Wi‑Fi**. Пароли являются учётными данными и должны просматриваться только штатными средствами операционной системы владельцем устройства.

### `FON-APP`

Показывает запущенные процессы.

Выключенное приложение не является активным процессом, поэтому получить список «абсолютно всех выключенных приложений» невозможно. Для списка установленных программ следует использовать штатные средства ОС.

### Язык

```text
Lang-RU
Lang-EU
```

Изменение сохраняется в `config.json`. Перезапуск необязателен.

### Цвет текста

```text
Text style red
Text style green
Text style bright_blue
Text style default
```

Доступные цвета:

```text
default black red green yellow blue magenta cyan white
bright_black bright_red bright_green bright_yellow
bright_blue bright_magenta bright_cyan bright_white
```

### VAP

Клонирует только публичные HTTPS-репозитории с `github.com`:

```text
VAP https://github.com/OWNER/REPO
VAP https://github.com/OWNER/REPO my-folder
```

Перед клонированием программа спрашивает подтверждение. Установка и запуск чужого кода выполняются на риск пользователя — проверяйте репозиторий перед запуском.

## Работа с JavaScript

Установите Node.js и проверьте:

```text
node-version
```

Запуск файла:

```text
run-js scripts/example.js
```

Также можно ввести путь к `.js` непосредственно:

```text
scripts/example.js
```

## Работа с файлами

```text
pwd
cd PATH
ls
tree
mkdir NAME
touch FILE
cat FILE
write FILE text
append FILE text
copy SOURCE DEST
move SOURCE DEST
delete FILE
rmdir DIRECTORY
find NAME
file-info FILE
hash FILE
```

## Сеть и система

```text
hostname
whoami
os-info
cpu-info
memory-info
disk-info
ip-local
dns-lookup example.com
ping example.com
ports
uptime
admin-check
```

## Полный список

Введите:

```text
help
```

## Настройка

Файл `config.json` создаётся автоматически:

```json
{
  "language": "EU",
  "prompt": "PY-CMD> ",
  "text_color": "default",
  "allow_shell": false
}
```

### Свой prompt

```text
prompt-set MASTER>
```

### Системные команды

По умолчанию произвольные команды ОС отключены.

Включить:

```text
shell-on
```

Отключить:

```text
shell-off
```

При включении `shell-on` неизвестный ввод передаётся системной оболочке. Не вставляйте команды из непроверенных источников.


# Создание аддона

Каждый скачанный аддон должен находиться в собственной папке внутри `addons`.

Название папки является названием аддона:

```text
Python-CMD/
└── addons/
    └── MyAddon/
        ├── addon.py
        ├── README.txt
        └── scripts/
            ├── worker.py
            ├── helper.py
            └── module.js
```

- `MyAddon/` — папка и название аддона.
- `addon.py` — главный файл, который Python CMD автоматически подключает при запуске.
- `scripts/` — все скрипты, необходимые аддону.
- `README.txt` — описание аддона и его команд.

Главный файл `addon.py`:

```python
from pathlib import Path
import subprocess
import sys


def register(shell, addon_dir: Path, scripts_dir: Path):
    def my_command(args):
        launcher = scripts_dir / "worker.py"
        subprocess.run(
            [sys.executable, str(launcher), *args],
            check=False
        )

    shell.register(
        "my-command",
        my_command,
        "Команда аддона MyAddon"
    )
```

Файл `scripts/worker.py`:

```python
import sys

print("Аддон запущен")
print("Аргументы:", sys.argv[1:])
```

При запуске Python CMD:

1. Открывается папка `addons`.
2. Проверяется каждая папка аддона.
3. В ней находится `addon.py`.
4. Создаётся папка `scripts`, если её ещё нет.
5. Вызывается функция:

```python
register(shell, addon_dir, scripts_dir)
```

Чтобы установить скачанный аддон, скопируйте всю его папку:

```text
DownloadedAddon/
```

в:

```text
Python-CMD/addons/
```

Результат:

```text
Python-CMD/addons/DownloadedAddon/addon.py
Python-CMD/addons/DownloadedAddon/scripts/
```

Файлы разных аддонов нельзя смешивать. У каждого аддона должна быть собственная папка.

Перезагрузка без перезапуска CMD:

```text
addons-reload
```

Просмотр подключённых аддонов:

```text
addons-all
```

## Контакты

Telegram: https://t.me/Py_CMD

GitHub: https://github.com/Master522qr/Python-CMD/tree/main?tab=readme-ov-file

## Выравнивание интерфейса

Только стартовый баннер выводится по центру терминала. Приглашение `PY-CMD>`, ошибки, справка, результаты команд и сообщения аддонов выводятся слева, как в обычном CMD.
