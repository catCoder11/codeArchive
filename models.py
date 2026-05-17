import sqlite3
from pydantic import BaseModel

con = sqlite3.connect("codeArchive.db") # подключение БД
con.create_function("LOWER", 1, lambda text: text.lower() if text is not None else None) # переопределение функции LOWER
# оригинальный LOWER не работает с кириллицей
con.row_factory = sqlite3.Row # настройка, чтобы значения возвращались в виде "ряда"(ключ-значение)
cur = con.cursor() # создание курсора

class Node(BaseModel):
    """Модель объекта(файл, функция, класс)"""
    id: int
    parent_id: int | None
    name: str
    type: str
    start_line: int
    end_line: int
    docstring: str | None