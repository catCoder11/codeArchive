import pathlib
import ast
import sys
from models import con, cur

count = 0

class MethodChecker(ast.NodeVisitor):
    """Класс для древовидной записи элементов в базу данных.
    Метод visit рекурсивно сохраняет в базу данных информацию о всех классах, функциях и файлах, включая id объекта-отца"""
    def __init__(self, file_id):
        self.current_obj = file_id

    def visit_data(self, node, category):
        """Проход по функции или классу, сохранение в БД, проход по всем вложенным в него объектам"""
        prev_obj = self.current_obj
        self.current_obj = add_data_object(node.name, prev_obj, category, node.lineno,
                                           node.end_lineno, ast.get_docstring(node)) # добавление объекта в БД и сохранение его в переменной как текущего
        self.generic_visit(node)  # проход по компонентам текущего узла
        self.current_obj = prev_obj  # Выходим из узла


    def visit_ClassDef(self, node):
        """Проход по классу"""
        self.visit_data(node, 3)

    def visit_FunctionDef(self, node):
        """Проход по функции"""
        self.visit_data(node, 1)

    def visit_AsyncFunctionDef(self, node):
        """Проход по асинхронной функции"""
        self.visit_data(node, 2)

def save_files(directory: str):
    """Функция принимает директорию и сохраняет все .py файлы в ней. Может быть как папка, так и файл"""
    path = pathlib.Path(directory)
    if path.is_file(): # если указан файл
        if path.suffix == '.py':
            parse_file(path)
        else:
            print("Неверный формат файла")
        return

    for file_path in path.glob('*.py'): # если указана папка
        print(file_path)
        parse_file(file_path)

def parse_file(file_path:pathlib.Path):
    """Функция принимает путь pathlib.Path до файла и парсит его с последующим сохранением в базу данных"""
    name = file_path.name
    print("Идёт сохранение файла " + name)
    res = cur.execute(f"""SELECT count(*) FROM Content c WHERE c.category_id=0 AND LOWER(name) = LOWER('{name}')""").fetchall()[0][0]
    if res == 1: # проверка на дубликаты
        print(f"Файл {name} уже есть в базе данных!")
        return
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            tree = ast.parse(f.read()) # создание дерева объектов файла
            if not tree.body: # проверка на пустой файл
                print(f"Файл {name} пустой")
                return
            file_id = add_data_object(file_path.name, None,0, 1,
                                      tree.body[-1].end_lineno, ast.get_docstring(tree)) # добавление файла в БД
            visitor = MethodChecker(file_id)
            visitor.visit(tree) # проход по всем узлам дерева и добавление классов, функций в БД
        print("Файл " + name + " успешно сохранён")
        global count
        count += 1
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f" Ошибка в файле {file_path}: {e}")
def add_data_object(name:str, parent_id:int | None, category_id:int, st:int, end:int, docstr:str | None):
    """Добавляет в таблицу Content новый ряд"""
    cur.execute(f"""
        INSERT INTO Content(name, parent_id, category_id, start_line, end_line, docstring)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (name, parent_id, category_id, st, end, docstr))
    con.commit()
    return cur.lastrowid # возвращение id последнего добавленного объекта в таблице


if __name__ == '__main__':
    if (len(sys.argv)>1):
        save_files(sys.argv[1])
        print(f"Сохранено {count} файлов")
    else:
        print("Укажите директорию для парсинга")