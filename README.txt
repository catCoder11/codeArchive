Проект состоит из REST-сервиса, реализованного на Python через библиотеку FastAPI c использованием ASGI-сервера uvicorn, локальной БД SQLite и отдельного Python-скрипта с использованием библиотеки ast для записи всех .py файлов из указанной директории в БД



	||	БАЗА ДАННЫХ	||


БД состоит из двух связанных таблиц

Content (основная таблица)
id 		integer		id
name		text		имя объекта
parent_id	integer		id вышестоящего по иерархии объекта(для файлов == NULL)
category_id	integer		id типа объекта(файл, функция, async функция, класс) в таблице Category 
start_line	integer		номер первой строки объекта
end_line	integer		номер последней строки объекта
docstring	text		docstring объекта

Создан уникальный ключ по id
Создан уникальный ключ по Content.name для строк с category_id = 0. (Возможность добавления файлов с одинаковым именем убрана во избежание проблем с логикой поиска по имени функции.)
Создан внешний ключ по Content.Category_id = Category.id
Создан внешний ключ по Content.parent_id = Content.id

В таблице реализована древовидная структура.


Category (справочник типов объектов)
id	integer		id
name	text		имя типа

Создан уникальный ключ по id

записанные значения:
0	|	file
1	|	func
2	|	async_func
3	|	class



	||	ПАРСИНГ ФАЙЛОВ	||


в файле pyParser.py содержится скрипт для парсинга. Для парсинга используется функция save_files. 
В функцию save_files можно передать как путь до конкретного файла, так и до папки. 
В результате в базу данных сохранятся данные из файла/всех .py файлов в папке.
комментарии по работе алгоритма приведены в исходном коде.



	||	REST API	||


Реализовано 4 GET-метода:
|	/api/files
|	/api/files/{name}/structure
|	/api/search
|	/api/stats


/api/files  возвращает список файлов. Для каждого файла указывается имя, количество строк, docstring, количество функций. Опционально можно указать quary-параметры limit и offset
/api/files/{name}/structure возвращает иерархию классов и функций в файле {name}. Для каждого объекта в файле возвращается имя, тип, номер первой и последней строки, docstring, вложенные объекты (например функции в классе)
/api/search возвращает все функции и классы в описании которых встречается ключевое слово q(по умолчанию ""). Для каждого объекта возвращает: имя, тип, имя файла, номер первой и последней строки, docstring. Опционально можно указать type (class или function), limit и offset
/api/stats возвращает общее число файлов, функций, классов, список файлов: имя, количество функций и классов в файле. Опциональные параметры limit и offset для списка файлов


	||	ИНСТРУКЦИЯ ПО ЗАПУСКУ	||


Перед работой программы необходимо ввести в cmd в директории проекта команду py -m pip install -r requirements.txt
Для запуска REST сервиса(запускать из директории проекта): uvicorn main:app --reload
Для сохранения .py файлов из cmd(запускать из директории проекта): py -m pyParser {директория с .py файлами/путь до .py файла}


	||	ПРИМЕРЫ		||


запрос: /api/files?limit=3
ответ:
[
  {
    "fileName": "main.py",
    "length": 186,
    "docstring": null,
    "func_count": 5
  },
  {
    "fileName": "models.py",
    "length": 18,
    "docstring": null,
    "func_count": 0
  },
  {
    "fileName": "pyParser.py",
    "length": 78,
    "docstring": null,
    "func_count": 8
  }
]


запрос: api/files/test.py/structure
ответ:
[
  {
    "name": "simpleFunc",
    "type": "func",
    "start_line": 22,
    "end_line": 24,
    "docstring": "Очень проста функция",
    "children": []
  },
  {
    "name": "bigClass",
    "type": "class",
    "start_line": 1,
    "end_line": 19,
    "docstring": "Важный класс",
    "children": [
      {
        "name": "__init__",
        "type": "func",
        "start_line": 3,
        "end_line": 4,
        "docstring": null,
        "children": []
      },
      {
        "name": "importantFunc",
        "type": "func",
        "start_line": 6,
        "end_line": 13,
        "docstring": "Важная функция",
        "children": []
      },
      {
        "name": "simpleFunc",
        "type": "func",
        "start_line": 16,
        "end_line": 19,
        "docstring": null,
        "children": []
      }
    ]
  },
  {
    "name": "smallClass",
    "type": "class",
    "start_line": 27,
    "end_line": 28,
    "docstring": null,
    "children": []
  }
]


запрос: /api/search?q=get&limit=3
ответ:
[
  {
    "name": "get_files",
    "type": "async_func",
    "file_name": "main.py",
    "start_line": 26,
    "end_line": 60,
    "docstring": "Возвращает список всех проиндексированных файлов с количеством функций в каждом"
  },
  {
    "name": "get_file_structure",
    "type": "async_func",
    "file_name": "main.py",
    "start_line": 63,
    "end_line": 98,
    "docstring": "Возвращает полную древовидную структуру файла: все функции и классы с номерами строк и docstring"
  },
  {
    "name": "get_stats",
    "type": "async_func",
    "file_name": "main.py",
    "start_line": 146,
    "end_line": 186,
    "docstring": "Возвращает статистику, сколько в базе файлов, функций, классов и сколько классов и функций в каждом файле"
  }
]

запрос: /api/search?q=функция&offset=2
ответ:
[
  {
    "name": "save_files",
    "type": "func",
    "file_name": "pyParser.py",
    "start_line": 33,
    "end_line": 44,
    "docstring": "Функция принимает директорию и сохраняет все .py файлы в ней. Может быть как папка, так и файл"
  },
  {
    "name": "parse_file",
    "type": "func",
    "file_name": "pyParser.py",
    "start_line": 46,
    "end_line": 66,
    "docstring": "Функция принимает путь pathlib.Path до файла и парсит его с последующим сохранением в базу данных"
  },
  {
    "name": "importantFunc",
    "type": "func",
    "file_name": "test.py",
    "start_line": 6,
    "end_line": 13,
    "docstring": "Важная функция"
  },
  {
    "name": "simpleFunc",
    "type": "func",
    "file_name": "test.py",
    "start_line": 22,
    "end_line": 24,
    "docstring": "Очень проста функция"
  }
]

запрос: /api/stats?limit=4&offset=30
ответ:
{
  "total_file_count": 98,
  "total_func_count": 1104,
  "total_class_count": 195,
  "file_stats": [
    {
      "fileName": "video_translation_client.py",
      "func_count": 25,
      "class_count": 1
    },
    {
      "fileName": "video_translation_const.py",
      "func_count": 0,
      "class_count": 0
    },
    {
      "fileName": "video_translation_dataclass.py",
      "func_count": 0,
      "class_count": 12
    },
    {
      "fileName": "video_translation_enum.py",
      "func_count": 0,
      "class_count": 7
    }
  ]
}
