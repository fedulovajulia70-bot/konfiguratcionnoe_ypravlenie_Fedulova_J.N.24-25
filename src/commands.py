"""Модуль с реализацией команд эмулятора оболочки."""

import fnmatch


def get_current_node(root: dict, path_stack: list[str]) -> dict:
    """Возвращает текущий узел в VFS по стеку путей.

    Args:
        root (dict): Корень виртуальной файловой системы.
        path_stack (list[str]): Список папок (путь от корня).

    Returns:
        dict: Текущая директория в памяти.
    """
    current = root
    for folder in path_stack:
        current = current["children"][folder]
    return current


def cmd_pwd(path_stack: list[str]) -> None:
    """Выводит текущий путь (команда pwd).

    Args:
        path_stack (list[str]): Список папок (путь от корня).
    """
    if not path_stack:
        print("/")
    else:
        print("/" + "/".join(path_stack))


def cmd_ls(current_node: dict, args: list[str]) -> None:
    """Выводит содержимое текущей директории (команда ls).

    Args:
        current_node (dict): Текущая директория.
        args (list[str]): Аргументы команды (поддерживается -l).
    """
    if "children" not in current_node:
        print("Ошибка: текущий объект не является директорией")
        return

    show_long = "-l" in args
    for name, node in current_node.get("children", {}).items():
        if show_long:
            prefix = "d" if node["type"] == "dir" else "-"
            print(f"{prefix} {name}")
        else:
            print(name)


def cmd_cd(root: dict, path_stack: list[str], args: list[str]) -> None:
    """Меняет текущую директорию (команда cd).

    Args:
        root (dict): Корень VFS.
        path_stack (list[str]): Текущий путь.
        args (list[str]): Аргументы команды.
    """
    if not args:
        path_stack.clear()
        return

    target = args[0]
    if target == "..":
        if path_stack:
            path_stack.pop()
        return

    current = get_current_node(root, path_stack)
    if target in current.get("children", {}):
        if current["children"][target]["type"] == "dir":
            path_stack.append(target)
        else:
            print(f"Ошибка: '{target}' не является директорией")
    else:
        print(f"Ошибка: директория '{target}' не найдена")


def cmd_find(current_node: dict, pattern: str, current_path: str = "") -> None:
    """Рекурсивно ищет файлы и папки по шаблону (команда find).

    Args:
        current_node (dict): Директория для поиска.
        pattern (str): Шаблон поиска (например, *.txt).
        current_path (str): Путь для вывода.
    """
    for name, node in current_node.get("children", {}).items():
        full_path = f"{current_path}/{name}" if current_path else name
        if fnmatch.fnmatch(name, pattern):
            print(full_path)
        if node["type"] == "dir":
            cmd_find(node, pattern, full_path)


def cmd_uniq(current_node: dict, args: list[str]) -> None:
    """Удаляет соседние дубликаты строк в файле (команда uniq).

    Args:
        current_node (dict): Текущая директория.
        args (list[str]): Аргументы команды (имя файла).
    """
    if not args:
        print("Ошибка: не указан файл")
        return

    filename = args[0]
    if filename not in current_node.get("children", {}):
        print(f"Ошибка: файл '{filename}' не найден")
        return

    node = current_node["children"][filename]
    if node["type"] != "file":
        print(f"Ошибка: '{filename}' не является файлом")
        return

    lines = node["content"].split("\n")
    prev_line = None
    for line in lines:
        if line != prev_line:
            print(line)
        prev_line = line


def cmd_mkdir(current_node: dict, args: list[str]) -> None:
    """Создает новую директорию (команда mkdir).

    Args:
        current_node (dict): Текущая директория.
        args (list[str]): Аргументы команды (имя новой папки).
    """
    if not args:
        print("Ошибка: не указано имя директории")
        return

    dirname = args[0]
    if "children" not in current_node:
        print("Ошибка: текущий объект не является директорией")
        return

    if dirname in current_node["children"]:
        print(f"Ошибка: '{dirname}' уже существует")
        return

    current_node["children"][dirname] = {"type": "dir", "children": {}}
    print(f"Директория '{dirname}' создана")


def cmd_rm(current_node: dict, args: list[str]) -> None:
    """Удаляет файл или директорию (команда rm).

    Args:
        current_node (dict): Текущая директория.
        args (list[str]): Аргументы команды (имя файла/папки).
    """
    if not args:
        print("Ошибка: не указан файл или директория")
        return

    target = args[0]
    if "children" not in current_node:
        print("Ошибка: текущий объект не является директорией")
        return

    if target not in current_node["children"]:
        print(f"Ошибка: '{target}' не найден")
        return

    del current_node["children"][target]
    print(f"'{target}' успешно удален")
