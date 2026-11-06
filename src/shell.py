"""Модуль, реализующий базовый цикл REPL для эмулятора оболочки."""

import os
import shlex
import socket
import getpass
import commands as cmd


def generate_prompt() -> str:
    """Формирует приглашение к вводу.

    Returns:
        str: Строка приглашения вида username@hostname:path$.
    """
    user = getpass.getuser()
    host = socket.gethostname()
    cwd = os.getcwd()

    home = os.path.expanduser("~")
    if cwd.startswith(home):
        cwd = cwd.replace(home, "~", 1)

    return f"{user}@{host}:{cwd}$ "


def parse_input(raw_input: str) -> tuple[str, list[str]]:
    """Парсит строку ввода на команду и аргументы.

    Args:
        raw_input (str): Сырая строка.

    Returns:
        tuple[str, list[str]]: Имя команды и аргументы.
    """
    tokens = shlex.split(raw_input)
    if not tokens:
        return "", []

    command = tokens[0]
    args = [os.path.expandvars(arg) for arg in tokens[1:]]
    return command, args


def execute_command(
    command: str, args: list[str], root_vfs: dict, path_stack: list[str]
) -> bool:
    """Выполняет команду. Возвращает False, если нужно выйти.

    Args:
        command (str): Имя команды.
        args (list[str]): Аргументы.
        root_vfs (dict): Корень VFS.
        path_stack (list[str]): Текущий путь.

    Returns:
        bool: True для продолжения, False для выхода.
    """
    if command == "exit":
        return False

    # Получаем текущую директорию для команд, которым она нужна
    current_node = cmd.get_current_node(root_vfs, path_stack)

    if command == "ls":
        cmd.cmd_ls(current_node, args)
    elif command == "cd":
        cmd.cmd_cd(root_vfs, path_stack, args)
    elif command == "pwd":
        cmd.cmd_pwd(path_stack)
    elif command == "find":
        pattern = args[0] if args else "*"
        cmd.cmd_find(current_node, pattern)
    elif command == "uniq":
        cmd.cmd_uniq(current_node, args)
    elif command == "mkdir":
        cmd.cmd_mkdir(current_node, args)
    elif command == "rm":
        cmd.cmd_rm(current_node, args)
    else:
        print(f"Ошибка: неизвестная команда '{command}'")

    return True


def run_script(script_path: str, root_vfs: dict) -> None:
    """Выполняет команды из стартового скрипта.

    Args:
        script_path (str): Путь к файлу скрипта.
        root_vfs (dict): Корень VFS.
    """
    print("--- Запуск стартового скрипта ---")
    path_stack = []
    try:
        with open(script_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                print(f"{generate_prompt()}{line}")
                command, args = parse_input(line)
                try:
                    if not execute_command(
                        command, args, root_vfs, path_stack
                    ):
                        break
                except Exception as err:
                    print(f"Ошибка выполнения строки '{line}': {err}")
    except FileNotFoundError:
        print(f"Ошибка: файл скрипта '{script_path}' не найден.")
    except Exception as err:
        print(f"Ошибка чтения скрипта: {err}")
    print("--- Скрипт завершен ---")


def run_repl(root_vfs: dict, script_path: str = None) -> None:
    """Запускает основной цикл (REPL) или выполняет скрипт.

    Args:
        root_vfs (dict): Корень VFS.
        script_path (str, optional): Путь к стартовому скрипту.
    """
    path_stack: list[str] = []

    if script_path:
        run_script(script_path, root_vfs)

    print("Добро пожаловать в эмулятор. Введите 'exit' для выхода.")

    while True:
        try:
            raw_input = input(generate_prompt())
            if not raw_input.strip():
                continue
            command, args = parse_input(raw_input)
            if not execute_command(command, args, root_vfs, path_stack):
                break
        except (KeyboardInterrupt, EOFError):
            # Ловим и Ctrl+C, и конец ввода (Ctrl+Z/D)
            print("\nДля выхода введите 'exit'")
        except Exception as err:
            print(f"Ошибка выполнения: {err}")
