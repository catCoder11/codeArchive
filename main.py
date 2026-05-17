from fastapi import FastAPI

import models
app = FastAPI()

def build_tree(data: list[models.Node]):
    """Строит json-древо классов и функций. Предполагает, что в передаваемом списке 1 файл и он идёт первым элементом"""
    raws = {}
    root = data[0].id # запись id файла
    for item in data[1:]:
        node = {**item.model_dump(), "children": []} # создание "узла" с добавлением ключа children(список вложенных объектов)
        raws[node["id"]] = node
    tree = []
    for node in raws.values(): # перебор всех узлов
        parent_id = node["parent_id"]
        if parent_id == root:
            tree.append(node) # добавление глобальных объектов в файле
        elif parent_id in raws:
            raws[parent_id]["children"].append(node) # добавление вложенных объектов в children родителя
    for dictionary in raws.values(): # удаление лишних ключей
        del dictionary["id"]
        del dictionary["parent_id"]
    return tree # возвращение дерева(структура полная т.к. dict "узлы" передаются по ссылке)

@app.get("/api/files")
async def get_files(offset: int = 0, limit: int = -1):
    """Возвращает список всех проиндексированных файлов с количеством функций в каждом"""
    request = f"""WITH RECURSIVE tree AS (
    SELECT
        id,
        category_id,
        id AS root_id
    FROM Content
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        c.id,
        c.category_id,
        t.root_id
    FROM Content c
    JOIN tree t ON c.parent_id = t.id
)
SELECT
    c.name as fileName,
    c.end_line as length,
    c.docstring,
    SUM(CASE WHEN t.category_id IN (1, 2) THEN 1 ELSE 0 END) AS func_count
FROM tree t
JOIN Content c ON t.root_id = c.id
GROUP BY t.root_id""" # sql запрос на список файлов: имя, "длина" (номер последней строки), docstring, число функций
    file_count = models.cur.execute("""
    SELECT COUNT(*) FROM Content c WHERE c.category_id == 0""").fetchone()[0]
    if limit > 0 and 0 <= offset < file_count: # проверка limit и offset на корректность. В противном случае игнорируются
        request += f" LIMIT {limit} OFFSET {offset}"
    elif limit > 0:
        request += f" LIMIT {limit}"
    elif 0 <= offset < file_count:
        request += f" LIMIT -1 OFFSET {offset}"
    res = models.cur.execute(request).fetchall() # возвращает результат запроса
    return list(res)

@app.get("/api/files/{name}/structure")
async def get_file_structure(name: str):
    """Возвращает полную древовидную структуру файла: все функции и классы с номерами строк и docstring"""
    res = models.cur.execute(f"""
    WITH RECURSIVE tree AS (
        SELECT
            id,
            id AS root_id
        FROM Content
        WHERE parent_id IS NULL AND LOWER(name) == LOWER("{name}")

        UNION ALL

        SELECT
            c.id,
            t.root_id
        FROM Content c
        JOIN tree t ON c.parent_id = t.id
    )
    SELECT
    c.id,
    c.parent_id,
    c.name,
    cat.name as type,
    c.start_line,
    c.end_line,
    c.docstring
    FROM Content c
    JOIN tree t on c.id == t.id
    JOIN Categories cat on cat.id == c.category_id
    GROUP BY c.id
    ORDER BY c.category_id
    """).fetchall() # sql запрос возвращает объекты, входящие в файл
    # category_id заменяется на type(class, file, async_func, func)
    if res:
        return build_tree([models.Node(**el) for el in res]) # возвращает древовидную структуру
    return []

@app.get("/api/search")
async def find_node(q: str = "", type: str = None, offset: int = 0, limit: int = -1):
    """Возвращает все функции и классы, в имени или описании которых встречается ключевое слово (регистронезависимо)"""
    request = f"""
        WITH RECURSIVE tree AS (
    SELECT
        id,
        name AS root_name
    FROM Content
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        c.id,
        t.root_name
    FROM Content c
    JOIN tree t ON c.parent_id = t.id
)

SELECT c.name,
cat.name AS type,
t.root_name as file_name,
c.start_line,
c.end_line,
c.docstring
FROM Content c
JOIN tree t ON t.id == c.id
JOIN Categories cat ON c.category_id == cat.id
WHERE c.category_id != 0 AND (LOWER(c.name) LIKE LOWER('%{q}%') OR LOWER(docstring) LIKE LOWER('%{q}%'))""" # sql запрос на список объектов(функций, классов), удовлетворяющих условию.
    # Для каждого: имя, тип, имя файла, номер первой и последней строки, docstring
    if type == "class": # опциональная фильтрация: отобразить только классы
        request += " AND c.category_id == 3"
    elif type == "function": # только функции
        request += " AND c.category_id in (1,2)"
    file_count = models.cur.execute("""
        SELECT COUNT(*) FROM Content c WHERE c.category_id == 0""").fetchone()[0]
    if limit > 0 and 0 <= offset < file_count: # проверка limit и offset на корректность. В противном случае игнорируются
        request += f" LIMIT {limit} OFFSET {offset}"
    elif limit > 0:
        request += f" LIMIT {limit}"
    elif 0 <= offset < file_count:
        request += f" LIMIT -1 OFFSET {offset}"
    res = models.cur.execute(request).fetchall()
    return list(res)

@app.get("/api/stats")
async def get_stats(limit: int = -1, offset: int = 0):
    """Возвращает статистику, сколько в базе файлов, функций, классов и сколько классов и функций в каждом файле"""
    request = f"""WITH RECURSIVE tree AS (
    SELECT
        id,
        category_id,
        id AS root_id
    FROM Content
    WHERE parent_id IS NULL

    UNION ALL

    SELECT
        c.id,
        c.category_id,
        t.root_id
    FROM Content c
    JOIN tree t ON c.parent_id = t.id
)

SELECT
    c.name as fileName,
    SUM(CASE WHEN t.category_id IN (1, 2) THEN 1 ELSE 0 END) AS func_count,
    SUM(CASE WHEN t.category_id == 3 THEN 1 ELSE 0 END) as class_count
FROM tree t
JOIN Content c ON t.root_id = c.id
GROUP BY t.root_id""" # sql запрос на список файлов: имя, количество функций и количество классов в нём
    file_count = models.cur.execute("""
            SELECT COUNT(*) FROM Content c WHERE c.category_id == 0""").fetchone()[0]
    if limit >= 0 and 0 <= offset < file_count: # проверка limit и offset на корректность. В противном случае игнорируются
        request += f" LIMIT {limit} OFFSET {offset}"
    elif limit >= 0:
        request += f" LIMIT {limit}"
    elif 0 <= offset < file_count:
        request += f" LIMIT -1 OFFSET {offset}"
    res = dict(models.cur.execute("""SELECT 
    SUM(CASE WHEN c.category_id == 0 THEN 1 ELSE 0 END) as total_file_count,
    SUM(CASE WHEN c.category_id in (1,2) THEN 1 ELSE 0 END) as total_func_count,
    SUM(CASE WHEN c.category_id == 3 THEN 1 ELSE 0 END) as total_class_count
    FROM Content c""").fetchone()) # sql запрос на то, сколько всего файлов, функций, классов
    file_stat_res = models.cur.execute(request).fetchall()
    res["file_stats"] = list(file_stat_res)
    return res