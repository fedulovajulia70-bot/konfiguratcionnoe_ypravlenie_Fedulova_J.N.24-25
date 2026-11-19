# Вариант 26: граф зависимостей npm

CLI-приложение на Python 3.10+, использующее стандартную библиотеку.
Задание: JSON-конфигурация, npm, рекурсивный DFS, фильтрация, циклы,
порядок загрузки, D2, SVG и ASCII-дерево.

## Запуск

```console
python src/main.py examples/configs/diamond.json
python src/main.py examples/configs/diamond.json --stage 1
python -m unittest discover -s tests -v
```

В Windows также доступен `run.bat`, в Linux/macOS — `sh run.sh`.
При необходимости задайте переменную `PYTHON` с путем к интерпретатору.

## Конфигурация

Все шесть полей обязательны. Пути разрешаются относительно JSON-файла.

| Поле | Значение |
| --- | --- |
| `package` | Имя npm-пакета, `name@version` или тестовый узел `A` |
| `repository` | HTTP(S) URL npm-реестра или путь к тестовому JSON |
| `test_mode` | `true`: тестовый граф; `false`: npm-реестр |
| `output` | Путь к SVG; рядом сохраняется D2 с тем же именем |
| `ascii_tree` | Выводить ASCII-дерево на этапе 5 |
| `filter_substring` | Исключать имена с этой подстрокой; `""` отключает |

Неизвестные и пропущенные поля, неправильные типы, неверные имена,
URL и пути приводят к сообщению `Error: ...` и коду возврата 1.
Подстрока чувствительна к регистру; исключение корня считается ошибкой.

## Модули

- `config`: `read_json`, `split_package`, валидация и `load_config`.
- `cli`: `run` выполняет этап; `main` обрабатывает CLI и ошибки.
- `errors`: `AppError` для ожидаемых ошибок приложения.

Этап 1 выводит все параметры в формате `ключ=значение`.

Этап 2 выводит прямые зависимости из поля `dependencies` выбранной версии:

```console
python src/main.py examples/configs/is-odd.json --stage 2
```

`repository` — URL npm-реестра с JSON API, а не ссылка на исходники GitHub.
`repository.NpmRepository` самостоятельно делает HTTP-запросы через `urllib`,
кэширует метаданные и разбирает JSON. `resolve` возвращает `Package`.
`TestRepository` читает JSON вида `{"A": ["B"], "B": []}`.
`semver.select_version` самостоятельно выбирает максимальную подходящую
версию: точная версия, dist-tag, `^`, `~`, `*`, `x`, сравнения, AND, `||`,
диапазон с дефисом и явно указанные prerelease. Поддерживаются npm-алиасы.
Git-, URL-, workspace- и file-зависимости завершаются понятной ошибкой.

## Рекурсивный DFS и тестовый режим

`graph.build_graph` рекурсивно обходит зависимости в алфавитном порядке.
Узел npm идентифицируется парой `имя@версия`; повторный узел не обходится.
Ребро к узлу в активном стеке фиксирует цикл, включая самозависимость.
`DependencyGraph` хранит корень, пакеты, ребра и найденные циклы.
`describe_graph` возвращает список смежности.

При фильтрации исключается пакет и обход через него. Его потомки могут
остаться, если достижимы по другой, не исключенной ветви. Фильтр проверяется
до HTTP-запроса; для npm-алиаса проверяется также настоящее имя.

```console
python src/main.py examples/configs/diamond.json --stage 3
python src/main.py examples/configs/cycle.json --stage 3
python src/main.py examples/configs/filtered.json --stage 3
python src/main.py examples/configs/isolated.json --stage 3
```

Тестовый репозиторий — непустой JSON-объект: ключи и ссылки состоят из
больших латинских букв. Все узлы, включая листья, объявляются явно.
Отсутствующие узлы, повторные ребра и неправильные списки — ошибки.

## Порядок загрузки и сравнение с npm

`operations.load_order` выполняет рекурсивный DFS и добавляет узел после
его зависимостей. Корень идет последним. Для цикла порядок невозможен:
этап 4 возвращает ошибку с обнаруженным циклом и код возврата 1.

```console
python src/main.py examples/configs/diamond.json --stage 4
python src/main.py examples/configs/chain.json --stage 4
python src/main.py examples/configs/cycle.json --stage 4
python -m scripts.compare_npm
```

Для ромба: `D -> B -> C -> A`; для цепочки: `C -> B -> A`;
для изолированного узла: `A`; с фильтром `B`: `D -> C -> A`.

Скрипт `scripts.compare_npm` нужен только для требуемого сравнения:
приложение его не импортирует. Он отдельно запускает настоящий npm с
`--ignore-scripts`, сохраняет журнал запросов и `npm ls --all` в `tmp/`,
а сравнение узлов, ребер и порядка — в `output/comparison.json`.
Повторные запуски npm могут использовать кэш и package-lock.
Node.js/npm требуются только для этого скрипта.

Наш порядок — зависимостный порядок готовности пакетов, а не хронология
сетевых запросов или выполнения lifecycle-скриптов. npm сначала получает
манифест родителя, чтобы узнать зависимости, и может загружать пакеты
параллельно. Поэтому журнал `fetch manifest` закономерно отличается от
DFS postorder; несколько независимых зависимостей допускают разные порядки.

## D2, SVG и ASCII-дерево

Для SVG нужен официальный [D2](https://d2lang.com/tour/install), доступный
через PATH. Также поддерживаются `D2_BINARY` с путем к исполняемому файлу
или локальный `tools/d2/d2.exe` (Windows), `tools/d2/d2` (Linux/macOS).
В данной рабочей папке подготовлен локальный D2 0.9.0.
Python-пакеты для работы приложения не требуются.

```console
python src/main.py examples/configs/is-odd.json
python src/main.py examples/configs/is-even.json
python src/main.py examples/configs/string-width.json
python -m scripts.demo
python -m scripts.demo --offline
```

По умолчанию выполняется этап 5. `--stage 1` показывает параметры,
`--stage 2` — прямые зависимости, `--stage 3` — список смежности и циклы,
`--stage 4` — порядок загрузки, `--stage 5` — D2, SVG и необязательное дерево.
На этапах 1–4 D2 не нужен. npm не нужен для этапов 1–5.

`visualization.to_d2` формирует D2 с отдельным объявлением каждого узла,
включая листья и изолированный корень. `export_graph` сохраняет `.d2`,
вызывает D2 с `--layout=dagre` и проверяет, что результат — SVG.
При отсутствии D2 исходник сохраняется, приложение сообщает об ошибке.
`ascii_tree` отмечает повторную общую зависимость `[shared]`, цикл `[cycle]`.

```text
A
|-- B
|   `-- D
`-- C
    `-- D [shared]
```

Сгенерированные примеры находятся в `output/`: `.d2`, `.svg` и `.txt`.
Результаты сравнения и пояснения: [docs/REPORT.md](docs/REPORT.md).
Исходники находятся в `src/`, тесты — в `tests/`, конфигурации и тестовые
репозитории — в `examples/`. Сборка и установка Python-зависимостей не нужны.
Код проверяется `pycodestyle` и `ruff`, строки не длиннее 79 символов.

Необязательная установка инструментов проверки и запуск:

```console
python -m pip install pycodestyle ruff
python -m pycodestyle src tests scripts
python -m ruff check src tests scripts
```

## Справочник функций

| Функции и методы | Назначение |
| --- | --- |
| `config.read_json` | Чтение JSON с обработкой ошибок |
| `config.split_package` | Разделение имени и требования версии |
| `config.validate_package` | Проверка npm-имени или тестового имени |
| `config.validate_repository` | Проверка URL либо локального пути |
| `config.validate_output` | Проверка пути SVG и защиты входных файлов |
| `config.validate_fields` | Проверка ключей, типов и фильтра |
| `config.load_config` | Сборка неизменяемого объекта Config |
| `Version.parse`, `Version.__lt__` | Разбор и сравнение SemVer |
| `semver.partial` | Разбор частичной версии и wildcard |
| `semver.increment`, `upper_bound` | Формирование границ диапазона |
| `semver.bounded`, `comparator` | Преобразование одного условия |
| `semver.compile_group` | Разбор AND-группы либо диапазона с дефисом |
| `semver.matches`, `select_version` | Проверка диапазона и выбор версии |
| `Package.key` | Идентификатор конкретной версии пакета |
| `NpmRepository.__init__`, `metadata` | Настройка реестра, HTTP и кэш |
| `NpmRepository.resolve` | Разрешение версии и чтение dependencies |
| `repository.validate_dependencies` | Проверка карты зависимостей |
| `TestRepository.__init__`, `validate_node` | Загрузка тестового графа |
| `TestRepository.resolve` | Чтение тестового узла |
| `repository.create_repository` | Выбор источника данных |
| `graph.build_graph`, внутренний `visit` | Рекурсивный DFS и циклы |
| `graph.describe_graph` | Текстовый список смежности |
| `operations.load_order`, `visit` | Порядок зависимостей DFS postorder |
| `visualization.to_d2` | Сериализация графа в D2 |
| `visualization.ascii_tree`, `visit` | Безопасный вывод ASCII-дерева |
| `visualization.find_d2`, `export_graph` | Поиск D2 и экспорт SVG |
| `cli.run`, `main` | Выполнение этапа и обработка CLI |
| `compare_npm.command`, `install` | Независимый запуск npm для сравнения |
| `compare_npm.npm_graph`, `visit` | Преобразование npm ls в узлы и ребра |
| `compare_npm.compare_one`, `main` | Сравнение и запись результатов |
| `demo.main` | Генерация всех демонстрационных файлов |

## Границы анализа

Анализируются обычные runtime-зависимости `dependencies`. В этой учебной
реализации не устанавливаются пакеты и не выполняются их скрипты;
`devDependencies`, `peerDependencies`, `optionalDependencies`, lock-файлы,
hoisting, overrides и платформенные ограничения не моделируются.
Поэтому для произвольного проекта результат может отличаться от полного
дерева npm. В сравнительном скрипте отключены optional- и peer-автоустановка.
Глубина рекурсии ограничена Python; чрезмерно глубокий граф приводит к
сообщению об ошибке, а не зависанию. Сетевой тайм-аут — 30 секунд на запрос,
тайм-аут рендеринга D2 — 60 секунд. При ошибке возвращается код 1,
при неверных CLI-аргументах — 2, при успехе — 0.

## Git

В локальной истории сохранены пять этапов с Conventional Commits.
Временные файлы, бинарный D2, кэш npm и результаты генерации исключены
через `.gitignore`. История пяти этапов сохранена при обновлении
[публичного репозитория][repository]. Прежняя работа удалена из текущей
версии файлов репозитория.

[repository]: https://github.com/fedulovajulia70-bot/konfiguratcionnoe_ypravlenie_Fedulova_J.N.24-25

## Документация форматов

- [Метаданные npm](https://github.com/npm/registry/blob/main/docs/responses/package-metadata.md).
- [Семантика диапазонов npm](https://github.com/npm/node-semver#ranges).
- [npm ls](https://docs.npmjs.com/cli/v12/commands/npm-ls/).
- [Связи D2](https://d2lang.com/tour/connections).
- [Экспорт D2](https://d2lang.com/tour/exports/).
