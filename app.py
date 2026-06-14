from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
import sqlite3
import hashlib
import os
import json
import time
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'pylearn_secret_key_2024_very_secure'
app.jinja_env.auto_reload = True

DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'pylearn.db')
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# ──────────────────────────────────────────────────────────────
# DATABASE HELPERS
# ──────────────────────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT
        );
        CREATE TABLE IF NOT EXISTS track_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            track_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            completed INTEGER DEFAULT 0,
            score INTEGER DEFAULT 0,
            attempts INTEGER DEFAULT 0,
            completed_at TEXT,
            UNIQUE(user_id, track_id, task_id)
        );
        CREATE TABLE IF NOT EXISTS typing_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            wpm INTEGER NOT NULL,
            accuracy REAL NOT NULL,
            completed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS speed_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            time_seconds REAL NOT NULL,
            correct INTEGER DEFAULT 0,
            completed_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS sandbox_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        );
    """)
    conn.commit()
    conn.close()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ──────────────────────────────────────────────────────────────
# AUTH DECORATOR
# ──────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def get_current_user():
    if 'user_id' not in session:
        return None
    conn = get_db()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    conn.close()
    return user

# ──────────────────────────────────────────────────────────────
# CURRICULUM DATA
# ──────────────────────────────────────────────────────────────

TRACKS = [
    {
        "id": 1,
        "title": "Основы Python",
        "subtitle": "Переменные, типы данных, операторы",
        "icon": "🐍",
        "color": "#4A90D9",
        "level": "Начинающий",
        "theory": {
            "title": "Основы Python",
            "sections": [
                {
                    "heading": "Что такое переменная?",
                    "text": "Переменная — это именованная область памяти, в которой хранится значение. В Python вам не нужно указывать тип переменной — он определяется автоматически.",
                    "code": "name = \"Alice\"\nage = 25\nheight = 1.75\nis_student = True"
                },
                {
                    "heading": "Типы данных",
                    "text": "Python поддерживает несколько встроенных типов: int (целые числа), float (числа с плавающей точкой), str (строки), bool (булевы значения).",
                    "code": "x = 42          # int\ny = 3.14        # float\nz = \"hello\"     # str\nb = True        # bool\n\nprint(type(x))  # <class 'int'>"
                },
                {
                    "heading": "Арифметические операторы",
                    "text": "Python поддерживает стандартные математические операции: сложение, вычитание, умножение, деление, деление нацело, остаток от деления и возведение в степень.",
                    "code": "a = 10\nb = 3\n\nprint(a + b)   # 13\nprint(a - b)   # 7\nprint(a * b)   # 30\nprint(a / b)   # 3.333...\nprint(a // b)  # 3\nprint(a % b)   # 1\nprint(a ** b)  # 1000"
                }
            ]
        },
        "tasks": [
            {
                "id": 1,
                "type": "choice",
                "question": "Какой тип данных у значения <code>42</code> в Python?",
                "options": ["str", "int", "float", "bool"],
                "correct": 1,
                "explanation": "42 — целое число, тип int."
            },
            {
                "id": 2,
                "type": "choice",
                "question": "Как объявить переменную <code>x</code> со значением 10?",
                "options": ["var x = 10", "x := 10", "x = 10", "int x = 10"],
                "correct": 2,
                "explanation": "В Python переменные объявляются без ключевых слов: x = 10."
            },
            {
                "id": 3,
                "type": "fill",
                "question": "Что выведет <code>print(10 % 3)</code>?",
                "options": ["3", "1", "0", "3.33"],
                "correct": 1,
                "explanation": "10 % 3 = 1 (остаток от деления 10 на 3)."
            },
            {
                "id": 4,
                "type": "choice",
                "question": "Какой оператор используется для возведения в степень в Python?",
                "options": ["^", "**", "pow", "^^"],
                "correct": 1,
                "explanation": "В Python ** — оператор возведения в степень. Например, 2**3 = 8."
            },
            {
                "id": 5,
                "type": "choice",
                "question": "Что вернёт <code>type(3.14)</code>?",
                "options": ["<class 'int'>", "<class 'str'>", "<class 'float'>", "<class 'double'>"],
                "correct": 2,
                "explanation": "3.14 — число с плавающей точкой, тип float."
            },
            {
                "id": 6,
                "type": "fill",
                "question": "Что выведет <code>print(10 // 3)</code>?",
                "options": ["3.33", "1", "3", "4"],
                "correct": 2,
                "explanation": "// — целочисленное деление. 10 // 3 = 3."
            },
            {
                "id": 7,
                "type": "choice",
                "question": "Какой тип у значения <code>True</code>?",
                "options": ["int", "str", "bool", "flag"],
                "correct": 2,
                "explanation": "True и False — булевы значения типа bool."
            },
            {
                "id": 8,
                "type": "choice",
                "question": "Как правильно создать строковую переменную?",
                "options": ["name = Alice", "name = 'Alice'", "string name = Alice", "str name = 'Alice'"],
                "correct": 1,
                "explanation": "Строки заключаются в одинарные или двойные кавычки."
            },
            {
                "id": 9,
                "type": "fill",
                "question": "Что выведет <code>print(2 ** 8)</code>?",
                "options": ["16", "64", "256", "512"],
                "correct": 2,
                "explanation": "2 в степени 8 равно 256."
            },
            {
                "id": 10,
                "type": "choice",
                "question": "Что означает <code>x += 5</code>?",
                "options": ["x = 5", "x = x + 5", "x == x + 5", "x = x * 5"],
                "correct": 1,
                "explanation": "x += 5 — сокращённая запись x = x + 5."
            }
        ]
    },
    {
        "id": 2,
        "title": "Строки",
        "subtitle": "Работа со строками и методы",
        "icon": "📝",
        "color": "#5BA85A",
        "level": "Начинающий",
        "theory": {
            "title": "Строки в Python",
            "sections": [
                {
                    "heading": "Создание строк",
                    "text": "Строки в Python можно создавать с одинарными, двойными или тройными кавычками. Тройные кавычки позволяют создавать многострочные строки.",
                    "code": "s1 = 'Hello'\ns2 = \"World\"\ns3 = '''Многострочная\nстрока'''\nprint(s1 + ' ' + s2)  # Hello World"
                },
                {
                    "heading": "Методы строк",
                    "text": "Строки имеют множество встроенных методов для обработки текста.",
                    "code": "text = \"  hello world  \"\nprint(text.upper())     # HELLO WORLD\nprint(text.strip())     # hello world\nprint(text.replace('world', 'Python'))  # hello Python\nprint(len(text))        # 15"
                },
                {
                    "heading": "Срезы строк",
                    "text": "Вы можете получить подстроку с помощью срезов.",
                    "code": "s = \"Python\"\nprint(s[0])     # P\nprint(s[-1])    # n\nprint(s[1:4])   # yth\nprint(s[::-1])  # nohtyP"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Что вернёт <code>'hello'.upper()</code>?", "options": ["hello", "HELLO", "Hello", "hELLO"], "correct": 1, "explanation": "upper() переводит все символы в верхний регистр."},
            {"id": 2, "type": "choice", "question": "Что вернёт <code>len('Python')</code>?", "options": ["5", "6", "7", "8"], "correct": 1, "explanation": "В слове 'Python' 6 символов."},
            {"id": 3, "type": "fill", "question": "Что вернёт <code>'hello'[0]</code>?", "options": ["h", "e", "o", "hello"], "correct": 0, "explanation": "Индексация начинается с 0."},
            {"id": 4, "type": "choice", "question": "Как объединить две строки <code>a = 'foo'</code> и <code>b = 'bar'</code>?", "options": ["a + b", "a.add(b)", "concat(a,b)", "a & b"], "correct": 0, "explanation": "Строки конкатенируются оператором +."},
            {"id": 5, "type": "choice", "question": "Что делает метод <code>strip()</code>?", "options": ["Разбивает строку", "Удаляет пробелы по краям", "Переводит в нижний регистр", "Считает символы"], "correct": 1, "explanation": "strip() удаляет пробелы (и другие символы) в начале и конце строки."},
            {"id": 6, "type": "fill", "question": "Что вернёт <code>'Python'[-1]</code>?", "options": ["P", "n", "o", "None"], "correct": 1, "explanation": "Отрицательный индекс -1 указывает на последний символ."},
            {"id": 7, "type": "choice", "question": "Как разбить строку по пробелам?", "options": [".split()", ".break()", ".divide()", ".cut()"], "correct": 0, "explanation": "split() разбивает строку по разделителю (по умолчанию — пробел)."},
            {"id": 8, "type": "choice", "question": "Что вернёт <code>'hello'.replace('l', 'r')</code>?", "options": ["herro", "hello", "herlo", "heiro"], "correct": 0, "explanation": "replace() заменяет все вхождения первой подстроки на вторую."},
            {"id": 9, "type": "fill", "question": "Что вернёт <code>'abc' * 3</code>?", "options": ["abc3", "abcabcabc", "aabbcc", "abc abc abc"], "correct": 1, "explanation": "Умножение строки на число повторяет её N раз."},
            {"id": 10, "type": "choice", "question": "Что вернёт <code>'hello'.find('ll')</code>?", "options": ["0", "1", "2", "-1"], "correct": 2, "explanation": "find() возвращает индекс первого вхождения подстроки. 'll' начинается с индекса 2."}
        ]
    },
    {
        "id": 3,
        "title": "Условия",
        "subtitle": "if, elif, else и логика",
        "icon": "🔀",
        "color": "#E07B39",
        "level": "Начинающий",
        "theory": {
            "title": "Условные операторы",
            "sections": [
                {
                    "heading": "Оператор if",
                    "text": "Условный оператор if позволяет выполнять блок кода только при выполнении определённого условия.",
                    "code": "age = 18\nif age >= 18:\n    print(\"Совершеннолетний\")\nelse:\n    print(\"Несовершеннолетний\")"
                },
                {
                    "heading": "elif — несколько условий",
                    "text": "elif позволяет проверить несколько условий последовательно.",
                    "code": "score = 75\nif score >= 90:\n    grade = 'A'\nelif score >= 75:\n    grade = 'B'\nelif score >= 60:\n    grade = 'C'\nelse:\n    grade = 'F'\nprint(grade)  # B"
                },
                {
                    "heading": "Логические операторы",
                    "text": "and, or, not используются для объединения условий.",
                    "code": "x = 5\nif x > 0 and x < 10:\n    print(\"Однозначное число\")\n\nif x < 0 or x > 100:\n    print(\"Вне диапазона\")\n\nif not x == 0:\n    print(\"Не ноль\")"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Что выведет код?<br><code>x = 5<br>if x > 3:<br>&nbsp;&nbsp;print('big')<br>else:<br>&nbsp;&nbsp;print('small')</code>", "options": ["small", "big", "error", "None"], "correct": 1, "explanation": "5 > 3, поэтому выполняется первая ветка."},
            {"id": 2, "type": "choice", "question": "Какой оператор используется для проверки равенства?", "options": ["=", "==", "===", "eq"], "correct": 1, "explanation": "== проверяет равенство. = — оператор присваивания."},
            {"id": 3, "type": "fill", "question": "Что выведет <code>print(5 > 3)</code>?", "options": ["5", "3", "True", "False"], "correct": 2, "explanation": "5 > 3 — это истина, поэтому выводится True."},
            {"id": 4, "type": "choice", "question": "Оператор <code>not True</code> вернёт:", "options": ["True", "False", "None", "Error"], "correct": 1, "explanation": "not инвертирует булево значение."},
            {"id": 5, "type": "choice", "question": "Что означает <code>x != 5</code>?", "options": ["x равно 5", "x не равно 5", "x больше 5", "x меньше 5"], "correct": 1, "explanation": "!= — оператор неравенства."},
            {"id": 6, "type": "fill", "question": "Выберите правильный синтаксис elif:", "options": ["else if:", "elif:", "elseif:", "else if():"], "correct": 1, "explanation": "В Python используется elif (сокращение от else if)."},
            {"id": 7, "type": "choice", "question": "Что вернёт <code>True and False</code>?", "options": ["True", "False", "None", "Error"], "correct": 1, "explanation": "and возвращает True только если оба операнда True."},
            {"id": 8, "type": "choice", "question": "Что вернёт <code>True or False</code>?", "options": ["True", "False", "None", "Error"], "correct": 0, "explanation": "or возвращает True если хотя бы один операнд True."},
            {"id": 9, "type": "fill", "question": "Как проверить, входит ли <code>x</code> в диапазон [1, 10]?", "options": ["x > 1 and x < 10", "1 < x < 10", "x in (1, 10)", "Варианты 1 и 2 верны"], "correct": 3, "explanation": "Оба варианта корректны: x > 1 and x < 10 и 1 < x < 10."},
            {"id": 10, "type": "choice", "question": "Что произойдёт, если условие if ложно и нет else?", "options": ["Ошибка", "Программа остановится", "Блок пропускается", "Выполнится False"], "correct": 2, "explanation": "Если условие ложно и нет else, блок кода просто пропускается."}
        ]
    },
    {
        "id": 4,
        "title": "Циклы",
        "subtitle": "for, while, break, continue",
        "icon": "🔄",
        "color": "#9B59B6",
        "level": "Начинающий",
        "theory": {
            "title": "Циклы в Python",
            "sections": [
                {
                    "heading": "Цикл for",
                    "text": "Цикл for используется для итерации по последовательностям: спискам, строкам, диапазонам.",
                    "code": "for i in range(5):\n    print(i)  # 0, 1, 2, 3, 4\n\nfruits = ['apple', 'banana', 'cherry']\nfor fruit in fruits:\n    print(fruit)"
                },
                {
                    "heading": "Цикл while",
                    "text": "while выполняет блок кода пока условие истинно.",
                    "code": "count = 0\nwhile count < 5:\n    print(count)\n    count += 1\n# 0, 1, 2, 3, 4"
                },
                {
                    "heading": "break и continue",
                    "text": "break прерывает цикл, continue переходит к следующей итерации.",
                    "code": "for i in range(10):\n    if i == 5:\n        break       # выход из цикла\n    if i % 2 == 0:\n        continue    # пропустить чётные\n    print(i)  # 1, 3"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Сколько раз выполнится тело цикла <code>for i in range(5)</code>?", "options": ["4", "5", "6", "0"], "correct": 1, "explanation": "range(5) генерирует числа 0, 1, 2, 3, 4 — 5 итераций."},
            {"id": 2, "type": "fill", "question": "Что выведет <code>for i in range(2, 5): print(i)</code>?", "options": ["2 3 4 5", "2 3 4", "0 1 2", "2 3 4 5 6"], "correct": 1, "explanation": "range(2, 5) генерирует 2, 3, 4 (конечное значение не включается)."},
            {"id": 3, "type": "choice", "question": "Что делает оператор <code>break</code>?", "options": ["Продолжает следующую итерацию", "Полностью выходит из цикла", "Делает паузу", "Возвращает значение"], "correct": 1, "explanation": "break немедленно выходит из цикла."},
            {"id": 4, "type": "choice", "question": "Что делает оператор <code>continue</code>?", "options": ["Выходит из цикла", "Пропускает оставшийся код итерации", "Повторяет итерацию", "Останавливает программу"], "correct": 1, "explanation": "continue переходит к следующей итерации, пропуская оставшийся код."},
            {"id": 5, "type": "fill", "question": "Что выведет: <code>i=0; while i<3: print(i); i+=1</code>?", "options": ["0 1 2 3", "1 2 3", "0 1 2", "Бесконечный цикл"], "correct": 2, "explanation": "while i<3: i=0,1,2 — три итерации."},
            {"id": 6, "type": "choice", "question": "Как перебрать все символы строки <code>s = 'hi'</code>?", "options": ["for i in len(s)", "for c in s", "for c in str(s)", "while s"], "correct": 1, "explanation": "Строка является итерируемым объектом."},
            {"id": 7, "type": "choice", "question": "range(0, 10, 2) генерирует:", "options": ["0 1 2 3 4 5 6 7 8 9", "0 2 4 6 8", "0 2 4 6 8 10", "2 4 6 8 10"], "correct": 1, "explanation": "range(start, stop, step) — начиная с 0, до 10 (не включая), шаг 2."},
            {"id": 8, "type": "choice", "question": "Что такое бесконечный цикл?", "options": ["for i in range(0)", "while True:", "for i in []", "while False:"], "correct": 1, "explanation": "while True — условие всегда истинно, цикл бесконечен."},
            {"id": 9, "type": "fill", "question": "Функция enumerate() позволяет получить:", "options": ["Только индексы", "Только значения", "Индекс и значение", "Словарь"], "correct": 2, "explanation": "enumerate(iterable) возвращает пары (индекс, значение)."},
            {"id": 10, "type": "choice", "question": "Что выведет: <code>for i in range(3): pass</code>?", "options": ["0 1 2", "pass", "ничего", "Ошибка"], "correct": 2, "explanation": "pass — это пустой оператор. Цикл выполнится, но ничего не выведет."}
        ]
    },
    {
        "id": 5,
        "title": "Списки",
        "subtitle": "Списки, методы, comprehensions",
        "icon": "📋",
        "color": "#E74C3C",
        "level": "Средний",
        "theory": {
            "title": "Списки в Python",
            "sections": [
                {
                    "heading": "Создание и доступ",
                    "text": "Список — упорядоченная изменяемая коллекция элементов. Элементы могут быть разных типов.",
                    "code": "nums = [1, 2, 3, 4, 5]\nprint(nums[0])   # 1\nprint(nums[-1])  # 5\nprint(nums[1:3]) # [2, 3]"
                },
                {
                    "heading": "Методы списков",
                    "text": "Списки поддерживают методы для добавления, удаления и изменения элементов.",
                    "code": "lst = [3, 1, 4, 1, 5]\nlst.append(9)     # добавить в конец\nlst.insert(0, 0)  # вставить на позицию\nlst.remove(1)     # удалить первый элемент со значением 1\nlst.sort()        # сортировка\nprint(lst)"
                },
                {
                    "heading": "List Comprehension",
                    "text": "Краткий способ создания списков с помощью выражений.",
                    "code": "squares = [x**2 for x in range(10)]\n# [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]\n\nevens = [x for x in range(20) if x % 2 == 0]\n# [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Как добавить элемент в конец списка?", "options": [".add()", ".append()", ".push()", ".insert()"], "correct": 1, "explanation": "append() добавляет элемент в конец списка."},
            {"id": 2, "type": "fill", "question": "Что вернёт <code>[1,2,3][1:3]</code>?", "options": ["[1,2]", "[2,3]", "[1,2,3]", "[3]"], "correct": 1, "explanation": "Срез [1:3] берёт элементы с индекса 1 до 3 (не включая): [2, 3]."},
            {"id": 3, "type": "choice", "question": "Метод <code>pop()</code> без аргументов:", "options": ["Удаляет первый элемент", "Удаляет последний элемент", "Возвращает копию", "Очищает список"], "correct": 1, "explanation": "pop() без аргументов удаляет и возвращает последний элемент."},
            {"id": 4, "type": "choice", "question": "Как создать список из 5 нулей?", "options": ["[0] * 5", "list(0, 5)", "zeros(5)", "[0 for _ in 5]"], "correct": 0, "explanation": "[0] * 5 создаёт [0, 0, 0, 0, 0]."},
            {"id": 5, "type": "fill", "question": "Что вернёт <code>len([1, [2, 3], 4])</code>?", "options": ["4", "3", "2", "Ошибка"], "correct": 1, "explanation": "len() считает элементы верхнего уровня: 1, [2,3], 4 — три элемента."},
            {"id": 6, "type": "choice", "question": "Как отсортировать список <code>lst</code> по убыванию?", "options": ["lst.sort(reverse=True)", "lst.sort(desc)", "lst.reverse_sort()", "sort(lst, -1)"], "correct": 0, "explanation": "sort(reverse=True) сортирует в обратном порядке."},
            {"id": 7, "type": "choice", "question": "List comprehension <code>[x*2 for x in range(3)]</code> вернёт:", "options": ["[0,1,2]", "[2,4,6]", "[0,2,4]", "[1,2,3]"], "correct": 2, "explanation": "x*2 для x = 0,1,2 даёт 0,2,4."},
            {"id": 8, "type": "fill", "question": "Метод <code>count()</code> в списке:", "options": ["Считает все элементы", "Считает вхождения значения", "Считает уникальные элементы", "Нет такого метода"], "correct": 1, "explanation": "lst.count(x) возвращает количество вхождений x в список."},
            {"id": 9, "type": "choice", "question": "Как проверить, есть ли элемент <code>5</code> в списке <code>lst</code>?", "options": ["lst.has(5)", "5 in lst", "lst.contains(5)", "lst.find(5) != -1"], "correct": 1, "explanation": "Оператор in проверяет принадлежность элемента."},
            {"id": 10, "type": "choice", "question": "Что делает <code>lst.extend([4, 5])</code>?", "options": ["Добавляет список как один элемент", "Добавляет элементы [4,5] в конец", "Создаёт копию с [4,5]", "Вставляет в начало"], "correct": 1, "explanation": "extend() добавляет все элементы другого списка в конец."}
        ]
    },
    {
        "id": 6,
        "title": "Словари",
        "subtitle": "dict, ключи, значения, методы",
        "icon": "📖",
        "color": "#1ABC9C",
        "level": "Средний",
        "theory": {
            "title": "Словари в Python",
            "sections": [
                {
                    "heading": "Создание словаря",
                    "text": "Словарь — коллекция пар ключ-значение. Ключи должны быть уникальны и неизменяемы.",
                    "code": "person = {\n    'name': 'Alice',\n    'age': 30,\n    'city': 'Moscow'\n}\nprint(person['name'])  # Alice"
                },
                {
                    "heading": "Основные методы",
                    "text": "Словари предоставляют методы для работы с ключами, значениями и парами.",
                    "code": "d = {'a': 1, 'b': 2, 'c': 3}\nprint(d.keys())    # dict_keys(['a', 'b', 'c'])\nprint(d.values())  # dict_values([1, 2, 3])\nprint(d.items())   # dict_items([('a',1),('b',2),('c',3)])\nd.get('z', 0)      # 0 (значение по умолчанию)"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Как получить значение по ключу <code>'name'</code>?", "options": ["d.get_key('name')", "d['name']", "d.key('name')", "d.value('name')"], "correct": 1, "explanation": "d['key'] — стандартный способ доступа к значению по ключу."},
            {"id": 2, "type": "fill", "question": "Что вернёт <code>d.get('x', 'default')</code> если <code>'x'</code> нет в словаре?", "options": ["None", "KeyError", "default", "False"], "correct": 2, "explanation": "get() возвращает второй аргумент если ключ не найден."},
            {"id": 3, "type": "choice", "question": "Как добавить новую пару ключ-значение в словарь?", "options": ["d.add('key', val)", "d['key'] = val", "d.insert('key', val)", "d.set('key', val)"], "correct": 1, "explanation": "Присваивание d['key'] = val добавляет или обновляет запись."},
            {"id": 4, "type": "choice", "question": "Метод <code>keys()</code> возвращает:", "options": ["Список ключей", "Все ключи как строку", "Объект dict_keys", "Кортеж ключей"], "correct": 2, "explanation": "keys() возвращает объект dict_keys, который можно итерировать."},
            {"id": 5, "type": "fill", "question": "Как удалить ключ <code>'age'</code> из словаря <code>d</code>?", "options": ["d.remove('age')", "del d['age']", "d.delete('age')", "d.pop_key('age')"], "correct": 1, "explanation": "del d[key] удаляет запись. Также можно использовать d.pop('age')."},
            {"id": 6, "type": "choice", "question": "Как проверить, есть ли ключ <code>'x'</code> в словаре <code>d</code>?", "options": ["d.has_key('x')", "'x' in d", "d.contains('x')", "d.exists('x')"], "correct": 1, "explanation": "Оператор in проверяет наличие ключа в словаре."},
            {"id": 7, "type": "choice", "question": "Словарь может иметь дублирующиеся ключи?", "options": ["Да", "Нет", "Только числовые", "Только строковые"], "correct": 1, "explanation": "Ключи словаря всегда уникальны. При дублировании значение перезаписывается."},
            {"id": 8, "type": "fill", "question": "Что вернёт <code>len({'a':1,'b':2})</code>?", "options": ["1", "2", "4", "0"], "correct": 1, "explanation": "len() возвращает количество пар ключ-значение."},
            {"id": 9, "type": "choice", "question": "Dict comprehension для квадратов: <code>{x: ___ for x in range(4)}</code>?", "options": ["x^2", "x**2", "pow(x)", "x*x и x**2 верны"], "correct": 3, "explanation": "Оба выражения x*x и x**2 вычисляют квадрат числа."},
            {"id": 10, "type": "choice", "question": "Метод <code>update()</code> у словаря:", "options": ["Обновляет один ключ", "Обновляет/добавляет несколько ключей из другого словаря", "Возвращает новый словарь", "Сортирует словарь"], "correct": 1, "explanation": "update() объединяет словари, добавляя или обновляя ключи."}
        ]
    },
    {
        "id": 7,
        "title": "Функции",
        "subtitle": "def, аргументы, lambda, return",
        "icon": "⚡",
        "color": "#F39C12",
        "level": "Средний",
        "theory": {
            "title": "Функции в Python",
            "sections": [
                {
                    "heading": "Определение функции",
                    "text": "Функция — блок кода, который можно вызывать многократно. Определяется с помощью def.",
                    "code": "def greet(name):\n    return f'Hello, {name}!'\n\nresult = greet('Alice')\nprint(result)  # Hello, Alice!"
                },
                {
                    "heading": "Аргументы по умолчанию и *args",
                    "text": "Можно задавать значения по умолчанию и принимать переменное количество аргументов.",
                    "code": "def power(base, exp=2):\n    return base ** exp\n\nprint(power(3))    # 9\nprint(power(2, 3)) # 8\n\ndef total(*args):\n    return sum(args)\n\nprint(total(1, 2, 3, 4))  # 10"
                },
                {
                    "heading": "Lambda-функции",
                    "text": "Анонимные функции, записанные в одну строку.",
                    "code": "square = lambda x: x ** 2\nprint(square(5))   # 25\n\nadd = lambda a, b: a + b\nprint(add(3, 4))   # 7"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Ключевое слово для определения функции:", "options": ["function", "def", "func", "define"], "correct": 1, "explanation": "def используется для определения функций в Python."},
            {"id": 2, "type": "fill", "question": "Что вернёт функция без явного <code>return</code>?", "options": ["0", "False", "None", "Ошибка"], "correct": 2, "explanation": "Функция без return неявно возвращает None."},
            {"id": 3, "type": "choice", "question": "Лямбда-функция <code>lambda x: x*2</code>:", "options": ["Это синтаксическая ошибка", "Анонимная функция, умножающая аргумент на 2", "Функция, возвращающая список", "Функция без аргументов"], "correct": 1, "explanation": "lambda создаёт анонимную функцию."},
            {"id": 4, "type": "choice", "question": "Как задать аргумент по умолчанию?", "options": ["def f(x = 5)", "def f(x: 5)", "def f(x default 5)", "def f(x -> 5)"], "correct": 0, "explanation": "Значение по умолчанию задаётся через = в сигнатуре."},
            {"id": 5, "type": "fill", "question": "Что такое *args в параметрах функции?", "options": ["Обязательный аргумент", "Именованный аргумент", "Переменное количество позиционных аргументов", "Указатель"], "correct": 2, "explanation": "*args принимает произвольное количество позиционных аргументов в кортеже."},
            {"id": 6, "type": "choice", "question": "**kwargs принимает:", "options": ["Позиционные аргументы", "Именованные аргументы в словарь", "Функции как аргументы", "Только строки"], "correct": 1, "explanation": "**kwargs собирает именованные аргументы в словарь."},
            {"id": 7, "type": "choice", "question": "Что такое рекурсия?", "options": ["Цикл внутри функции", "Функция, вызывающая саму себя", "Вложенная функция", "Функция без return"], "correct": 1, "explanation": "Рекурсия — это когда функция вызывает сама себя."},
            {"id": 8, "type": "fill", "question": "Функция <code>map(func, lst)</code>:", "options": ["Применяет func к каждому элементу lst", "Создаёт словарь", "Сортирует список", "Фильтрует элементы"], "correct": 0, "explanation": "map() применяет функцию к каждому элементу итерируемого объекта."},
            {"id": 9, "type": "choice", "question": "Что делает <code>filter(func, lst)</code>?", "options": ["Трансформирует элементы", "Оставляет элементы, для которых func вернула True", "Создаёт новый список из функций", "Удаляет дубликаты"], "correct": 1, "explanation": "filter() возвращает элементы, для которых функция-предикат возвращает True."},
            {"id": 10, "type": "choice", "question": "Docstring функции — это:", "options": ["Комментарий (#)", "Строка документации в начале функции", "Имя функции", "Тип возвращаемого значения"], "correct": 1, "explanation": "Docstring — строковый литерал в начале функции, описывающий её поведение."}
        ]
    },
    {
        "id": 8,
        "title": "Классы и ООП",
        "subtitle": "class, self, наследование",
        "icon": "🏗️",
        "color": "#8E44AD",
        "level": "Продвинутый",
        "theory": {
            "title": "Объектно-ориентированное программирование",
            "sections": [
                {
                    "heading": "Определение класса",
                    "text": "Класс — шаблон для создания объектов. __init__ — конструктор класса.",
                    "code": "class Dog:\n    def __init__(self, name, age):\n        self.name = name\n        self.age = age\n    \n    def bark(self):\n        return f'{self.name} says Woof!'\n\ndog = Dog('Rex', 3)\nprint(dog.bark())"
                },
                {
                    "heading": "Наследование",
                    "text": "Класс может наследовать атрибуты и методы другого класса.",
                    "code": "class Animal:\n    def __init__(self, name):\n        self.name = name\n    \n    def speak(self):\n        return 'Some sound'\n\nclass Cat(Animal):\n    def speak(self):\n        return f'{self.name} says Meow!'\n\ncat = Cat('Whiskers')\nprint(cat.speak())"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Ключевое слово для создания класса:", "options": ["object", "class", "type", "struct"], "correct": 1, "explanation": "class используется для определения классов."},
            {"id": 2, "type": "fill", "question": "Что такое <code>self</code> в методах класса?", "options": ["Глобальная переменная", "Ссылка на текущий экземпляр", "Ключевое слово Python", "Тип данных"], "correct": 1, "explanation": "self — ссылка на конкретный экземпляр класса."},
            {"id": 3, "type": "choice", "question": "Метод <code>__init__</code> вызывается:", "options": ["При удалении объекта", "При создании объекта", "При копировании", "При сравнении"], "correct": 1, "explanation": "__init__ — конструктор, вызывается при создании нового объекта."},
            {"id": 4, "type": "choice", "question": "Как создать экземпляр класса <code>Car</code>?", "options": ["Car.new()", "new Car()", "car = Car()", "create Car()"], "correct": 2, "explanation": "Экземпляр создаётся вызовом имени класса как функции."},
            {"id": 5, "type": "fill", "question": "Как наследовать от класса <code>Animal</code>?", "options": ["class Dog inherits Animal:", "class Dog(Animal):", "class Dog extends Animal:", "class Dog: inherit Animal"], "correct": 1, "explanation": "Родительский класс указывается в круглых скобках."},
            {"id": 6, "type": "choice", "question": "Что такое полиморфизм?", "options": ["Один класс — много объектов", "Разные классы — одинаковый интерфейс методов", "Класс внутри класса", "Несколько наследований"], "correct": 1, "explanation": "Полиморфизм позволяет использовать объекты разных классов через один интерфейс."},
            {"id": 7, "type": "choice", "question": "Метод <code>__str__</code> определяет:", "options": ["Сравнение объектов", "Строковое представление объекта", "Хеш объекта", "Удаление объекта"], "correct": 1, "explanation": "__str__ вызывается при print(obj) и str(obj)."},
            {"id": 8, "type": "fill", "question": "super() используется для:", "options": ["Создания суперкласса", "Вызова методов родительского класса", "Проверки наследования", "Удаления класса"], "correct": 1, "explanation": "super() возвращает прокси-объект для вызова методов родительского класса."},
            {"id": 9, "type": "choice", "question": "Атрибут класса (не экземпляра) объявляется:", "options": ["Внутри __init__ через self", "Вне методов на уровне класса", "С помощью @classattr", "Только в __class__"], "correct": 1, "explanation": "Атрибуты класса объявляются вне методов и разделяются между экземплярами."},
            {"id": 10, "type": "choice", "question": "Что такое инкапсуляция?", "options": ["Наследование свойств", "Скрытие внутренней реализации", "Создание множества объектов", "Связывание классов"], "correct": 1, "explanation": "Инкапсуляция — принцип сокрытия деталей реализации."}
        ]
    },
    {
        "id": 9,
        "title": "Исключения",
        "subtitle": "try, except, finally, raise",
        "icon": "🛡️",
        "color": "#E67E22",
        "level": "Продвинутый",
        "theory": {
            "title": "Обработка исключений",
            "sections": [
                {
                    "heading": "try / except",
                    "text": "Блок try/except перехватывает и обрабатывает исключения, не допуская краша программы.",
                    "code": "try:\n    result = 10 / 0\nexcept ZeroDivisionError:\n    print('Деление на ноль!')\nexcept ValueError as e:\n    print(f'Ошибка: {e}')\nfinally:\n    print('Выполняется всегда')"
                },
                {
                    "heading": "Генерация исключений",
                    "text": "raise позволяет явно вызывать исключения.",
                    "code": "def divide(a, b):\n    if b == 0:\n        raise ValueError('Делитель не может быть 0')\n    return a / b\n\ntry:\n    divide(10, 0)\nexcept ValueError as e:\n    print(e)"
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Какой блок выполняется при возникновении исключения?", "options": ["try", "except", "finally", "else"], "correct": 1, "explanation": "except перехватывает и обрабатывает исключения."},
            {"id": 2, "type": "fill", "question": "Блок <code>finally</code> выполняется:", "options": ["Только при ошибке", "Только без ошибки", "Всегда", "Никогда"], "correct": 2, "explanation": "finally выполняется всегда — и при ошибке, и без неё."},
            {"id": 3, "type": "choice", "question": "Как явно вызвать исключение?", "options": ["throw Exception()", "raise Exception()", "error Exception()", "throw new Exception()"], "correct": 1, "explanation": "raise используется для явного генерирования исключений."},
            {"id": 4, "type": "choice", "question": "Какое исключение возникнет при <code>int('abc')</code>?", "options": ["TypeError", "ValueError", "NameError", "SyntaxError"], "correct": 1, "explanation": "ValueError возникает при неверном значении для преобразования."},
            {"id": 5, "type": "fill", "question": "Перехватить любое исключение можно через:", "options": ["except Error:", "except:", "except All:", "except Exception:"], "correct": 3, "explanation": "except Exception: перехватывает все стандартные исключения."},
            {"id": 6, "type": "choice", "question": "Что такое IndexError?", "options": ["Неверный тип данных", "Обращение по несуществующему индексу", "Деление на ноль", "Неопределённая переменная"], "correct": 1, "explanation": "IndexError возникает при обращении к несуществующему индексу."},
            {"id": 7, "type": "choice", "question": "Блок <code>else</code> после try/except выполняется:", "options": ["При любом исходе", "Только если исключение произошло", "Только если исключения не было", "Никогда"], "correct": 2, "explanation": "else в try/except выполняется только если исключение не было поднято."},
            {"id": 8, "type": "fill", "question": "NameError возникает когда:", "options": ["Неверное имя файла", "Переменная не определена", "Неверное имя класса", "Функция не найдена"], "correct": 1, "explanation": "NameError — обращение к несуществующей переменной."},
            {"id": 9, "type": "choice", "question": "Как создать собственное исключение?", "options": ["def MyError(): pass", "class MyError(Exception): pass", "exception MyError", "raise new MyError"], "correct": 1, "explanation": "Собственные исключения создаются как классы, наследующие Exception."},
            {"id": 10, "type": "choice", "question": "Что такое TypeError?", "options": ["Ошибка синтаксиса", "Операция с несовместимыми типами", "Переполнение", "Отсутствие файла"], "correct": 1, "explanation": "TypeError возникает при применении операции к несовместимым типам данных."}
        ]
    },
    {
        "id": 10,
        "title": "Файлы и модули",
        "subtitle": "Работа с файлами, import, os",
        "icon": "📦",
        "color": "#16A085",
        "level": "Продвинутый",
        "theory": {
            "title": "Файлы и модули",
            "sections": [
                {
                    "heading": "Работа с файлами",
                    "text": "Python предоставляет встроенные функции для чтения и записи файлов.",
                    "code": "# Запись\nwith open('file.txt', 'w') as f:\n    f.write('Hello, World!')\n\n# Чтение\nwith open('file.txt', 'r') as f:\n    content = f.read()\nprint(content)"
                },
                {
                    "heading": "Импорт модулей",
                    "text": "Модули расширяют возможности Python. Используйте import для подключения.",
                    "code": "import os\nimport json\nfrom math import sqrt, pi\nfrom datetime import datetime\n\nprint(os.getcwd())\nprint(sqrt(16))  # 4.0\nprint(pi)        # 3.14159..."
                }
            ]
        },
        "tasks": [
            {"id": 1, "type": "choice", "question": "Режим <code>'w'</code> при открытии файла:", "options": ["Только чтение", "Запись (перезапись)", "Добавление в конец", "Бинарный режим"], "correct": 1, "explanation": "'w' открывает файл для записи, создавая новый или перезаписывая существующий."},
            {"id": 2, "type": "fill", "question": "Зачем использовать <code>with open()</code>?", "options": ["Быстрее открывает файл", "Автоматически закрывает файл", "Позволяет читать бинарные файлы", "Только для записи"], "correct": 1, "explanation": "with гарантирует закрытие файла даже при возникновении исключения."},
            {"id": 3, "type": "choice", "question": "Как импортировать только функцию <code>sqrt</code> из <code>math</code>?", "options": ["import sqrt from math", "from math import sqrt", "import math.sqrt", "use math: sqrt"], "correct": 1, "explanation": "from module import name — стандартный синтаксис импорта."},
            {"id": 4, "type": "choice", "question": "Режим <code>'a'</code> при открытии файла:", "options": ["Только чтение", "Запись с начала", "Добавление в конец", "Бинарный режим"], "correct": 2, "explanation": "'a' (append) добавляет данные в конец файла, не удаляя содержимое."},
            {"id": 5, "type": "fill", "question": "Модуль <code>os</code> используется для:", "options": ["Работы с сетью", "Взаимодействия с операционной системой", "Работы с датами", "Математических вычислений"], "correct": 1, "explanation": "os предоставляет инструменты для работы с файловой системой и ОС."},
            {"id": 6, "type": "choice", "question": "Метод <code>f.readlines()</code> возвращает:", "options": ["Строку", "Список строк", "Байты", "Словарь"], "correct": 1, "explanation": "readlines() читает все строки файла в список."},
            {"id": 7, "type": "choice", "question": "Как сериализовать словарь в JSON строку?", "options": ["json.read(d)", "json.dumps(d)", "json.serialize(d)", "json.write(d)"], "correct": 1, "explanation": "json.dumps() преобразует Python-объект в JSON строку."},
            {"id": 8, "type": "fill", "question": "json.loads() выполняет:", "options": ["Загрузку файла", "Парсинг JSON строки в Python-объект", "Сохранение в JSON файл", "Сжатие данных"], "correct": 1, "explanation": "json.loads() парсит строку JSON и возвращает Python-объект."},
            {"id": 9, "type": "choice", "question": "<code>os.path.join()</code> используется для:", "options": ["Объединения строк", "Построения пути к файлу", "Слияния файлов", "Поиска файла"], "correct": 1, "explanation": "os.path.join() объединяет компоненты пути с учётом ОС."},
            {"id": 10, "type": "choice", "question": "Как узнать текущую директорию?", "options": ["os.dir()", "os.getcwd()", "os.current()", "os.path.now()"], "correct": 1, "explanation": "os.getcwd() возвращает текущую рабочую директорию."}
        ]
    }
]

TYPING_EXERCISES = {
    "easy": [
        "x = 10",
        "print('Hello')",
        "name = 'Python'",
        "age = 25",
        "result = True",
    ],
    "medium": [
        "for i in range(10):",
        "if x > 0 and x < 100:",
        "def greet(name):",
        "return x * x + 1",
        "lst = [1, 2, 3, 4, 5]",
    ],
    "hard": [
        "squares = [x**2 for x in range(10)]",
        "def factorial(n): return 1 if n <= 1 else n * factorial(n-1)",
        "with open('file.txt', 'r') as f: data = f.read()",
        "result = {k: v for k, v in d.items() if v > 0}",
        "try:\n    x = int(input())\nexcept ValueError:\n    print('Error')",
    ]
}

SPEED_TASKS = [
    {"id": 1, "description": "Создайте переменную x равную 42", "answer": "x = 42", "hint": "x = ..."},
    {"id": 2, "description": "Напишите цикл for от 0 до 9", "answer": "for i in range(10):", "hint": "for ... in range(...):"},
    {"id": 3, "description": "Определите функцию add с параметрами a и b", "answer": "def add(a, b):", "hint": "def ...(...):" },
    {"id": 4, "description": "Создайте пустой список nums", "answer": "nums = []", "hint": "nums = [...]"},
    {"id": 5, "description": "Выведите 'Hello, World!'", "answer": "print('Hello, World!')", "hint": "print(...)"},
]

# ──────────────────────────────────────────────────────────────
# ROUTES — AUTH
# ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user, tracks=TRACKS)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')
        
        if not username or not email or not password:
            error = 'Заполните все поля'
        elif len(password) < 6:
            error = 'Пароль должен содержать минимум 6 символов'
        elif password != confirm:
            error = 'Пароли не совпадают'
        else:
            conn = get_db()
            existing = conn.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email)).fetchone()
            if existing:
                error = 'Пользователь с таким именем или email уже существует'
            else:
                conn.execute(
                    'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
                    (username, email, hash_password(password))
                )
                conn.commit()
                user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
                session['user_id'] = user['id']
                session['username'] = user['username']
                conn.close()
                return redirect(url_for('dashboard'))
            conn.close()
    
    return render_template('auth/register.html', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        conn = get_db()
        user = conn.execute(
            'SELECT * FROM users WHERE (username = ? OR email = ?) AND password_hash = ?',
            (username, username, hash_password(password))
        ).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            # Update last active
            conn = get_db()
            conn.execute('UPDATE users SET last_active = ? WHERE id = ?',
                        (datetime.now().isoformat(), user['id']))
            conn.commit()
            conn.close()
            return redirect(url_for('dashboard'))
        else:
            error = 'Неверные имя пользователя или пароль'
    
    return render_template('auth/login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ──────────────────────────────────────────────────────────────
# ROUTES — DASHBOARD
# ──────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    conn = get_db()
    
    progress_data = {}
    for track in TRACKS:
        # Получаем детальную информацию по каждой задаче
        tasks_progress = conn.execute(
            'SELECT task_id, completed, attempts FROM track_progress WHERE user_id = ? AND track_id = ?',
            (user['id'], track['id'])
        ).fetchall()
        
        # Превращаем в словарь для быстрого поиска в Jinja
        t_prog = {row['task_id']: dict(row) for row in tasks_progress}
        
        completed_count = sum(1 for r in tasks_progress if r['completed'] == 1)
        total_attempts = sum(r['attempts'] for r in tasks_progress)
        total_tasks = len(track['tasks'])
        percent = int((completed_count / total_tasks) * 100) if total_tasks > 0 else 0
        
        progress_data[track['id']] = {
            'completed': completed_count,
            'total': total_tasks,
            'percent': percent,
            'total_attempts': total_attempts,
            'tasks_detail': t_prog
        }
    
    typing_best = conn.execute(
        'SELECT difficulty, MAX(wpm) as best_wpm FROM typing_scores WHERE user_id = ? GROUP BY difficulty',
        (user['id'],)
    ).fetchall()
    conn.close()
    
    return render_template('dashboard/index.html',
                          user=user,
                          tracks=TRACKS,
                          progress=progress_data,
                          typing_best={r['difficulty']: r['best_wpm'] for r in typing_best})

@app.route('/leaderboard')
@login_required
def leaderboard():
    user = get_current_user()
    conn = get_db()
    # Получаем топ-50 пользователей по XP
    leaders = conn.execute(
        'SELECT username, xp, streak FROM users ORDER BY xp DESC LIMIT 50'
    ).fetchall()
    conn.close()
    
    return render_template('dashboard/leaderboard.html', user=user, leaders=leaders)

# ──────────────────────────────────────────────────────────────
# ROUTES — SANDBOX
# ──────────────────────────────────────────────────────────────

@app.route('/sandbox')
@login_required
def sandbox():
    user = get_current_user()
    conn = get_db()
    # Получаем историю сохраненных кодов пользователя
    history = conn.execute(
        'SELECT id, title, code, created_at FROM sandbox_history WHERE user_id = ? ORDER BY id DESC', 
        (user['id'],)
    ).fetchall()
    conn.close()
    
    # Преобразуем в список словарей для передачи в шаблон
    history_list = [dict(row) for row in history]
    
    return render_template('sandbox.html', user=user, history=history_list)

@app.route('/api/save-sandbox', methods=['POST'])
@login_required
def save_sandbox():
    data = request.get_json()
    title = data.get('title', 'Без названия').strip()
    code = data.get('code', '').strip()
    
    if not title:
        title = 'Без названия'
        
    conn = get_db()
    conn.execute(
        'INSERT INTO sandbox_history (user_id, title, code) VALUES (?, ?, ?)',
        (session['user_id'], title, code)
    )
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# ──────────────────────────────────────────────────────────────
# ROUTES — TRACKS
# ──────────────────────────────────────────────────────────────

@app.route('/tracks')
@login_required
def tracks():
    user = get_current_user()
    conn = get_db()
    progress_data = {}
    for track in TRACKS:
        completed = conn.execute(
            'SELECT COUNT(*) as cnt FROM track_progress WHERE user_id = ? AND track_id = ? AND completed = 1',
            (user['id'], track['id'])
        ).fetchone()['cnt']
        progress_data[track['id']] = {
            'completed': completed,
            'total': len(track['tasks']),
            'percent': int((completed / len(track['tasks'])) * 100)
        }
    conn.close()
    return render_template('tracks/list.html', user=user, tracks=TRACKS, progress=progress_data)

@app.route('/tracks/<int:track_id>/theory')
@login_required
def track_theory(track_id):
    user = get_current_user()
    track = next((t for t in TRACKS if t['id'] == track_id), None)
    if not track:
        return redirect(url_for('tracks'))
    return render_template('theory/detail.html', user=user, track=track)

@app.route('/tracks/<int:track_id>')
@login_required
def track_detail(track_id):
    user = get_current_user()
    track = next((t for t in TRACKS if t['id'] == track_id), None)
    if not track:
        return redirect(url_for('tracks'))
    
    conn = get_db()
    completed_ids = set(
        row['task_id'] for row in conn.execute(
            'SELECT task_id FROM track_progress WHERE user_id = ? AND track_id = ? AND completed = 1',
            (user['id'], track_id)
        ).fetchall()
    )
    conn.close()
    
    # Find next uncompleted task
    next_task_id = None
    for task in track['tasks']:
        if task['id'] not in completed_ids:
            next_task_id = task['id']
            break
    
    return render_template('tracks/detail.html',
                          user=user,
                          track=track,
                          completed_ids=completed_ids,
                          next_task_id=next_task_id)

@app.route('/tracks/<int:track_id>/task/<int:task_id>')
@login_required
def task(track_id, task_id):
    user = get_current_user()
    track = next((t for t in TRACKS if t['id'] == track_id), None)
    if not track:
        return redirect(url_for('tracks'))
    
    task_obj = next((t for t in track['tasks'] if t['id'] == task_id), None)
    if not task_obj:
        return redirect(url_for('track_detail', track_id=track_id))
    
    conn = get_db()
    progress = conn.execute(
        'SELECT * FROM track_progress WHERE user_id = ? AND track_id = ? AND task_id = ?',
        (user['id'], track_id, task_id)
    ).fetchone()
    
    completed_count = conn.execute(
        'SELECT COUNT(*) as cnt FROM track_progress WHERE user_id = ? AND track_id = ? AND completed = 1',
        (user['id'], track_id)
    ).fetchone()['cnt']
    conn.close()
    
    # Calculate next task
    task_ids = [t['id'] for t in track['tasks']]
    current_idx = task_ids.index(task_id)
    next_task_id = task_ids[current_idx + 1] if current_idx + 1 < len(task_ids) else None
    
    return render_template('tracks/task.html',
                          user=user,
                          track=track,
                          task=task_obj,
                          progress=progress,
                          completed_count=completed_count,
                          next_task_id=next_task_id,
                          task_number=current_idx + 1,
                          total_tasks=len(track['tasks']))

# ──────────────────────────────────────────────────────────────
# API — ANSWER CHECKING (Backend validation)
# ──────────────────────────────────────────────────────────────

@app.route('/api/check-answer', methods=['POST'])
@login_required
def check_answer():
    data = request.get_json()
    track_id = data.get('track_id')
    task_id = data.get('task_id')
    answer_index = data.get('answer_index')
    
    # Find the task
    track = next((t for t in TRACKS if t['id'] == track_id), None)
    if not track:
        return jsonify({'error': 'Track not found'}), 404
    
    task_obj = next((t for t in track['tasks'] if t['id'] == task_id), None)
    if not task_obj:
        return jsonify({'error': 'Task not found'}), 404
    
    # Backend validation — correct answer is stored server-side only
    is_correct = (answer_index == task_obj['correct'])
    
    user_id = session['user_id']
    conn = get_db()
    
    # Update progress
    existing = conn.execute(
        'SELECT * FROM track_progress WHERE user_id = ? AND track_id = ? AND task_id = ?',
        (user_id, track_id, task_id)
    ).fetchone()
    
    if existing:
        # Если задача уже была когда-то решена, мы ничего не меняем.
        # Если же она решается ВПЕРВЫЕ и ответ верный:
        if is_correct and not existing['completed']:
            conn.execute(
                'UPDATE track_progress SET completed = 1, score = 100, attempts = 1, completed_at = ? WHERE user_id = ? AND track_id = ? AND task_id = ?',
                (datetime.now().isoformat(), user_id, track_id, task_id)
            )
            # Начисляем XP
            conn.execute('UPDATE users SET xp = xp + 10 WHERE id = ?', (user_id,))
        # Если ответ неверный, мы БОЛЬШЕ НЕ увеличиваем attempts в базе данных,
        # оставляя там 0 или 1, чтобы не накручивать счетчик кликами.
    else:
        # Если записи в таблице еще нет (первое касание задачи)
        conn.execute(
            'INSERT INTO track_progress (user_id, track_id, task_id, completed, score, attempts, completed_at) VALUES (?, ?, ?, ?, ?, ?, ?)',
            (user_id, track_id, task_id, 
             1 if is_correct else 0, 
             100 if is_correct else 0, 
             1 if is_correct else 0,  # Ставим 1 попытку только если задача РЕШЕНА
             datetime.now().isoformat() if is_correct else None)
        )
        if is_correct:
            conn.execute('UPDATE users SET xp = xp + 10 WHERE id = ?', (user_id,))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        'correct': is_correct,
        'explanation': task_obj['explanation'],
        'correct_answer': task_obj['correct'],
        'correct_text': task_obj['options'][task_obj['correct']]
    })

# ──────────────────────────────────────────────────────────────
# ROUTES — TYPING TRAINER
# ──────────────────────────────────────────────────────────────

@app.route('/typing')
@login_required
def typing_trainer():
    user = get_current_user()
    conn = get_db()
    scores = conn.execute(
        'SELECT * FROM typing_scores WHERE user_id = ? ORDER BY completed_at DESC LIMIT 10',
        (user['id'],)
    ).fetchall()
    best_scores = conn.execute(
        'SELECT difficulty, MAX(wpm) as wpm, MAX(accuracy) as acc FROM typing_scores WHERE user_id = ? GROUP BY difficulty',
        (user['id'],)
    ).fetchall()
    conn.close()
    return render_template('typing/index.html',
                          user=user,
                          exercises=TYPING_EXERCISES,
                          scores=scores,
                          best_scores={r['difficulty']: dict(r) for r in best_scores})

@app.route('/api/typing-score', methods=['POST'])
@login_required
def save_typing_score():
    data = request.get_json()
    difficulty = data.get('difficulty')
    wpm = data.get('wpm', 0)
    accuracy = data.get('accuracy', 0)
    
    if difficulty not in ('easy', 'medium', 'hard'):
        return jsonify({'error': 'Invalid difficulty'}), 400
    
    conn = get_db()
    conn.execute(
        'INSERT INTO typing_scores (user_id, difficulty, wpm, accuracy) VALUES (?, ?, ?, ?)',
        (session['user_id'], difficulty, int(wpm), float(accuracy))
    )
    # Award XP for completion
    conn.execute('UPDATE users SET xp = xp + 5 WHERE id = ?', (session['user_id'],))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'xp_earned': 5})

# ──────────────────────────────────────────────────────────────
# ROUTES — SPEED CODING
# ──────────────────────────────────────────────────────────────

@app.route('/speed')
@login_required
def speed_coding():
    user = get_current_user()
    return render_template('typing/speed.html', user=user, tasks=SPEED_TASKS)

@app.route('/api/check-speed', methods=['POST'])
@login_required
def check_speed():
    data = request.get_json()
    task_id = data.get('task_id')
    user_answer = data.get('answer', '').strip()
    time_seconds = data.get('time_seconds', 0)
    
    task_obj = next((t for t in SPEED_TASKS if t['id'] == task_id), None)
    if not task_obj:
        return jsonify({'error': 'Task not found'}), 404
    
    # Normalize comparison
    is_correct = user_answer.strip() == task_obj['answer'].strip()
    
    if is_correct:
        conn = get_db()
        conn.execute(
            'INSERT INTO speed_scores (user_id, task_id, time_seconds, correct) VALUES (?, ?, ?, 1)',
            (session['user_id'], task_id, time_seconds)
        )
        conn.execute('UPDATE users SET xp = xp + 15 WHERE id = ?', (session['user_id'],))
        conn.commit()
        conn.close()
    
    return jsonify({
        'correct': is_correct,
        'expected': task_obj['answer'],
        'time': time_seconds
    })

@app.route('/api/get-typing-exercise', methods=['POST'])
@login_required
def get_typing_exercise():
    data = request.get_json()
    difficulty = data.get('difficulty', 'easy')
    exercises = TYPING_EXERCISES.get(difficulty, TYPING_EXERCISES['easy'])
    import random
    return jsonify({'text': random.choice(exercises)})

# ──────────────────────────────────────────────────────────────
# ROUTES — PROFILE
# ──────────────────────────────────────────────────────────────

@app.route('/profile')
@login_required
def profile():
    user = get_current_user()
    conn = get_db()
    
    # 1. Собираем статистику пользователя
    total_completed = conn.execute(
        'SELECT COUNT(*) as cnt FROM track_progress WHERE user_id = ? AND completed = 1',
        (user['id'],)
    ).fetchone()['cnt']
    
    best_wpm = conn.execute(
        'SELECT MAX(wpm) as best FROM typing_scores WHERE user_id = ?',
        (user['id'],)
    ).fetchone()['best'] or 0
    
    speed_count = conn.execute(
        'SELECT COUNT(*) as cnt FROM speed_scores WHERE user_id = ?',
        (user['id'],)
    ).fetchone()['cnt']
    
    conn.close()

    # ВЫСЧИТЫВАЕМ ОБЩЕЕ КОЛИЧЕСТВО ЗАДАЧ (исправление ошибки)
    total_tasks = sum(len(track['tasks']) for track in TRACKS)

    # 2. Динамически вычисляем достижения (Бейджи)
    badges = [
        {
            "id": "first_blood", "name": "Первый шаг", "icon": "👶", 
            "desc": "Реши свою самую первую задачу.", 
            "unlocked": total_completed >= 1
        },
        {
            "id": "streak_3", "name": "В потоке", "icon": "🔥", 
            "desc": "Заходи и решай задачи 3 дня подряд.", 
            "unlocked": user['streak'] >= 3
        },
        {
            "id": "typewriter", "name": "Печатная машинка", "icon": "⌨️", 
            "desc": "Достигни скорости 40 WPM в тренажере.", 
            "unlocked": best_wpm >= 40
        },
        {
            "id": "flash", "name": "Флэш", "icon": "⚡", 
            "desc": "Пройди хотя бы одно испытание на спид-кодинг.", 
            "unlocked": speed_count > 0
        },
        {
            "id": "dedication", "name": "Упорство", "icon": "💪", 
            "desc": "Успешно заверши 30 любых заданий из треков.", 
            "unlocked": total_completed >= 30
        },
        {
            "id": "master", "name": "Мастер Python", "icon": "🎓", 
            "desc": "Накопи 500 XP за любые активности.", 
            "unlocked": user['xp'] >= 500
        }
    ]
    
    return render_template('dashboard/profile.html',
                          user=user,
                          total_completed=total_completed,
                          best_wpm=best_wpm,
                          speed_count=speed_count,
                          badges=badges,
                          total_tasks=total_tasks)

# ──────────────────────────────────────────────────────────────
# MINI-GAMES DATA
# ──────────────────────────────────────────────────────────────

BUG_TASKS = [
    {
        "id": 1, 
        "title": "Забывчивая функция",
        "code": "def greet(name)\n    return f'Hello, {name}'", 
        "buggy_line": "def greet(name)", 
        "answer": "def greet(name):", 
        "hint": "Чего-то не хватает в конце определения функции...",
        "xp": 10
    },
    {
        "id": 2, 
        "title": "Выход за границы",
        "code": "nums = [1, 2, 3]\nprint(nums[3])", 
        "buggy_line": "print(nums[3])", 
        "answer": "print(nums[2])", 
        "hint": "Индексация списков в Python начинается с нуля.",
        "xp": 15
    },
    {
        "id": 3, 
        "title": "Опасное сравнение",
        "code": "if x = 10:\n    print('Десятка!')", 
        "buggy_line": "if x = 10:", 
        "answer": "if x == 10:", 
        "hint": "Один знак равенства — это присваивание, а не сравнение.",
        "xp": 10
    },
    {
        "id": 4, 
        "title": "Неправильная склейка",
        "code": "age = 20\nprint('Мне ' + age + ' лет')", 
        "buggy_line": "print('Мне ' + age + ' лет')", 
        "answer": "print('Мне ' + str(age) + ' лет')", 
        "hint": "Нельзя просто так сложить строку и число. Число нужно преобразовать.",
        "xp": 20
    }
]

# ──────────────────────────────────────────────────────────────
# ALGORITHMS GAME DATA
# ──────────────────────────────────────────────────────────────

ALGO_TASKS = [
    {
        "id": 1,
        "title": "Сортировка Пузырьком",
        "description": "Собери логику одного прохода пузырьковой сортировки: сравниваем и меняем элементы местами.",
        "blocks": [
            {"id": "b1", "code": "arr[i], arr[i+1] = arr[i+1], arr[i]"},
            {"id": "b2", "code": "for i in range(len(arr) - 1):"},
            {"id": "b3", "code": "if arr[i] > arr[i+1]:"}
        ],
        "correct_order": ["b2", "b3", "b1"],
        "xp": 30
    },
    {
        "id": 2,
        "title": "Поиск максимума",
        "description": "Найди максимальное значение в списке чисел.",
        "blocks": [
            {"id": "b1", "code": "max_val = num"},
            {"id": "b2", "code": "for num in arr:"},
            {"id": "b3", "code": "max_val = arr[0]"},
            {"id": "b4", "code": "if num > max_val:"}
        ],
        "correct_order": ["b3", "b2", "b4", "b1"],
        "xp": 20
    },
    {
        "id": 3,
        "title": "Факториал числа",
        "description": "Собери цикл, который вычисляет факториал числа n (произведение всех чисел от 1 до n).",
        "blocks": [
            {"id": "b1", "code": "result *= i"},
            {"id": "b2", "code": "return result"},
            {"id": "b3", "code": "result = 1"},
            {"id": "b4", "code": "for i in range(1, n + 1):"}
        ],
        "correct_order": ["b3", "b4", "b1", "b2"],
        "xp": 25
    },
    {
        "id": 4,
        "title": "Разворот строки",
        "description": "Напиши алгоритм, который читает строку посимвольно и собирает ее задом наперед.",
        "blocks": [
            {"id": "b1", "code": "for char in s:"},
            {"id": "b2", "code": "return rev_str"},
            {"id": "b3", "code": "rev_str = ''"},
            {"id": "b4", "code": "rev_str = char + rev_str"}
        ],
        "correct_order": ["b3", "b1", "b4", "b2"],
        "xp": 30
    },
    {
        "id": 5,
        "title": "Счетчик гласных",
        "description": "Посчитай, сколько гласных букв содержится в слове.",
        "blocks": [
            {"id": "b1", "code": "if char in vowels:"},
            {"id": "b2", "code": "for char in word:"},
            {"id": "b3", "code": "count += 1"},
            {"id": "b4", "code": "vowels = 'aeiou'; count = 0"}
        ],
        "correct_order": ["b4", "b2", "b1", "b3"],
        "xp": 25
    },
    {
        "id": 6,
        "title": "Проверка на палиндром",
        "description": "Определи функцию, которая возвращает True, если строка читается одинаково с обеих сторон.",
        "blocks": [
            {"id": "b1", "code": "s = s.lower()"},
            {"id": "b2", "code": "return s == s[::-1]"},
            {"id": "b3", "code": "def is_palindrome(s):"}
        ],
        "correct_order": ["b3", "b1", "b2"],
        "xp": 15
    },
    {
        "id": 7,
        "title": "Словарь частотностей",
        "description": "Подсчитай, сколько раз каждый элемент встречается в списке, используя словарь.",
        "blocks": [
            {"id": "b1", "code": "counts = {}"},
            {"id": "b2", "code": "else: counts[item] = 1"},
            {"id": "b3", "code": "for item in lst:"},
            {"id": "b4", "code": "if item in counts: counts[item] += 1"}
        ],
        "correct_order": ["b1", "b3", "b4", "b2"],
        "xp": 35
    },
    {
        "id": 8,
        "title": "Безопасный ввод",
        "description": "Создай бесконечный цикл, который прерывается, если пользователь вводит слово 'exit'.",
        "blocks": [
            {"id": "b1", "code": "if user_input == 'exit': break"},
            {"id": "b2", "code": "while True:"},
            {"id": "b3", "code": "print('Эхо:', user_input)"},
            {"id": "b4", "code": "user_input = input()"}
        ],
        "correct_order": ["b2", "b4", "b1", "b3"],
        "xp": 20
    },
    {
        "id": 9,
        "title": "List Comprehension",
        "description": "Собери логику генератора списка: оставляем только четные числа.",
        "blocks": [
            {"id": "b1", "code": "evens = [x for x in nums if x % 2 == 0]"},
            {"id": "b2", "code": "print(evens)"},
            {"id": "b3", "code": "nums = [1, 2, 3, 4, 5]"}
        ],
        "correct_order": ["b3", "b1", "b2"],
        "xp": 20
    },
    {
        "id": 10,
        "title": "Последовательность Фибоначчи",
        "description": "Сгенерируй числа Фибоначчи (каждое следующее равно сумме двух предыдущих).",
        "blocks": [
            {"id": "b1", "code": "fib.append(next_val)"},
            {"id": "b2", "code": "for i in range(2, n):"},
            {"id": "b3", "code": "fib = [0, 1]"},
            {"id": "b4", "code": "next_val = fib[-1] + fib[-2]"}
        ],
        "correct_order": ["b3", "b2", "b4", "b1"],
        "xp": 35
    },
    {
        "id": 11,
        "title": "Обработка исключений",
        "description": "Попытайся прочитать файл, а если его нет — перехвати ошибку.",
        "blocks": [
            {"id": "b1", "code": "except FileNotFoundError:"},
            {"id": "b2", "code": "print('Файл не найден!')"},
            {"id": "b3", "code": "print(f.read())"},
            {"id": "b4", "code": "try:\n    with open('data.txt') as f:"}
        ],
        "correct_order": ["b4", "b3", "b1", "b2"],
        "xp": 25
    },
    {
        "id": 12,
        "title": "Сумма элементов",
        "description": "Напиши алгоритм, который складывает все числа в списке.",
        "blocks": [
            {"id": "b1", "code": "total += num"},
            {"id": "b2", "code": "return total"},
            {"id": "b3", "code": "for num in arr:"},
            {"id": "b4", "code": "total = 0"}
        ],
        "correct_order": ["b4", "b3", "b1", "b2"],
        "xp": 15
    },
    {
        "id": 13,
        "title": "Простое число",
        "description": "Проверь, делится ли число n на что-то кроме 1 и самого себя.",
        "blocks": [
            {"id": "b1", "code": "for i in range(2, int(n**0.5) + 1):"},
            {"id": "b2", "code": "if n <= 1: return False"},
            {"id": "b3", "code": "return True"},
            {"id": "b4", "code": "if n % i == 0: return False"}
        ],
        "correct_order": ["b2", "b1", "b4", "b3"],
        "xp": 40
    },
    {
        "id": 14,
        "title": "Объединение в словарь",
        "description": "Используй функцию zip() для объединения списка ключей и значений в словарь.",
        "blocks": [
            {"id": "b1", "code": "keys = ['a', 'b', 'c']"},
            {"id": "b2", "code": "my_dict = dict(zip(keys, values))"},
            {"id": "b3", "code": "values = [1, 2, 3]"}
        ],
        "correct_order": ["b1", "b3", "b2"],
        "xp": 20
    },
    {
        "id": 15,
        "title": "Безопасное деление",
        "description": "Создай функцию, которая предотвращает ошибку деления на ноль.",
        "blocks": [
            {"id": "b1", "code": "return a / b"},
            {"id": "b2", "code": "if b == 0: return None"},
            {"id": "b3", "code": "def safe_divide(a, b):"}
        ],
        "correct_order": ["b3", "b2", "b1"],
        "xp": 15
    },
    {
        "id": 16,
        "title": "Сумма двух (Two Sum)",
        "description": "Найди индексы двух чисел в массиве, которые в сумме дают target.",
        "blocks": [
            {"id": "b1", "code": "return [i, j]"},
            {"id": "b2", "code": "for i in range(len(arr)):"},
            {"id": "b3", "code": "for j in range(i + 1, len(arr)):"},
            {"id": "b4", "code": "if arr[i] + arr[j] == target:"}
        ],
        "correct_order": ["b2", "b3", "b4", "b1"],
        "xp": 45
    }
]

@app.route('/games/algorithms')
@login_required
def algo_game():
    user = get_current_user()
    import random
    task = random.choice(ALGO_TASKS)
    # Перемешиваем блоки для пользователя
    shuffled_blocks = task['blocks'].copy()
    random.shuffle(shuffled_blocks)
    return render_template('games/algorithms.html', user=user, task=task, blocks=shuffled_blocks)

@app.route('/api/check-algo', methods=['POST'])
@login_required
def check_algo():
    data = request.get_json()
    task_id = data.get('task_id')
    user_order = data.get('order', []) # Массив ID блоков
    
    task = next((t for t in ALGO_TASKS if t['id'] == task_id), None)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
        
    is_correct = (user_order == task['correct_order'])
    
    if is_correct:
        conn = get_db()
        conn.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (task['xp'], session['user_id']))
        conn.commit()
        conn.close()
        
    return jsonify({
        'correct': is_correct,
        'xp_earned': task['xp'] if is_correct else 0
    })

# ──────────────────────────────────────────────────────────────
# ROUTES — GAMES
# ──────────────────────────────────────────────────────────────

@app.route('/games')
@login_required
def games_hub():
    user = get_current_user()
    return render_template('games/hub.html', user=user)

@app.route('/games/bugs', methods=['GET', 'POST'])
@login_required
def bug_hunter():
    user = get_current_user()
    import random
    # Выбираем случайную задачу для игры
    task = random.choice(BUG_TASKS)
    return render_template('games/bugs.html', user=user, task=task)

@app.route('/api/check-bug', methods=['POST'])
@login_required
def check_bug():
    data = request.get_json()
    task_id = data.get('task_id')
    user_answer = data.get('answer', '').strip()
    
    task = next((t for t in BUG_TASKS if t['id'] == task_id), None)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # Сравниваем ответ пользователя с правильным (убирая лишние пробелы)
    is_correct = user_answer.replace(" ", "") == task['answer'].replace(" ", "")
    
    if is_correct:
        conn = get_db()
        # Начисляем XP за найденный баг
        conn.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (task['xp'], session['user_id']))
        conn.commit()
        conn.close()
        
    return jsonify({
        'correct': is_correct,
        'expected': task['answer'],
        'xp_earned': task['xp'] if is_correct else 0
    })



def upgrade_db():
    conn = get_db()
    try:
        # Пытаемся добавить колонку для аватарки (по умолчанию будет робот)
        conn.execute('ALTER TABLE users ADD COLUMN avatar TEXT DEFAULT "🤖"')
        conn.commit()
    except sqlite3.OperationalError:
        pass # Если колонка уже есть, просто игнорируем ошибку
    conn.close()

# ──────────────────────────────────────────────────────────────
# AVATAR & CERTIFICATE
# ──────────────────────────────────────────────────────────────

@app.route('/api/update-avatar', methods=['POST'])
@login_required
def update_avatar():
    data = request.get_json()
    new_avatar = data.get('avatar', '🤖')
    
    conn = get_db()
    conn.execute('UPDATE users SET avatar = ? WHERE id = ?', (new_avatar, session['user_id']))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'avatar': new_avatar})

@app.route('/certificate')
@login_required
def certificate():
    user = get_current_user()
    conn = get_db()
    
    # Считаем, сколько всего заданий на платформе
    total_tasks = sum(len(track['tasks']) for track in TRACKS)
    
    # Считаем, сколько решил пользователь
    completed_tasks = conn.execute(
        'SELECT COUNT(*) as cnt FROM track_progress WHERE user_id = ? AND completed = 1',
        (user['id'],)
    ).fetchone()['cnt']
    conn.close()
    
    # Если пройдено не 100%, не даем посмотреть сертификат
    if completed_tasks < total_tasks:
        return redirect(url_for('profile'))
        
    return render_template('certificate.html', user=user, date=datetime.now().strftime("%d.%m.%Y"))

# ──────────────────────────────────────────────────────────────
# INTERNSHIP DATA (Стажировка - 30 задач)
# ──────────────────────────────────────────────────────────────

INTERNSHIP_TASKS = {
    "easy": [
        {
            "id": 1, "title": "Первая задача", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Привет! Твоя первая задача элементарна.", "Напиши код, который выведет строку 'Привет, мир!'"],
            "initial_code": "# Выведи 'Привет, мир!'\n", "expected_output": "Привет, мир!", "xp": 10
        },
        {
            "id": 2, "title": "Калькулятор", "lead_name": "Маша (Junior)", "avatar": "👩",
            "messages": ["Слушай, помоги посчитать.", "У нас есть переменные a=15 и b=27. Выведи их сумму."],
            "initial_code": "a = 15\nb = 27\n# Выведи сумму\n", "expected_output": "42", "xp": 10
        },
        {
            "id": 3, "title": "Длина пароля", "lead_name": "Олег (Безопасник)", "avatar": "🕵️",
            "messages": ["Нужно проверить длину введенного пароля.", "Выведи количество символов в строке password."],
            "initial_code": "password = 'SuperSecret123'\n# Выведи длину строки\n", "expected_output": "14", "xp": 15
        },
        {
            "id": 4, "title": "Первый и последний", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["У нас список серверов.", "Выведи первый и последний элементы списка, каждый с новой строки."],
            "initial_code": "servers = ['Alpha', 'Beta', 'Gamma', 'Delta']\n# Твой код:\n", "expected_output": "Alpha\nDelta", "xp": 15
        },
        {
            "id": 5, "title": "Проверка возраста", "lead_name": "HR", "avatar": "👩‍💼",
            "messages": ["Напиши проверку.", "Если age >= 18 выведи 'Доступ разрешен', иначе 'Доступ запрещен'."],
            "initial_code": "age = 20\n# Твой код:\n", "expected_output": "Доступ разрешен", "xp": 15
        },
        {
            "id": 6, "title": "Повторение - мать учения", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Нам нужен цикл.", "Выведи числа от 1 до 5 включительно (каждое с новой строки)."],
            "initial_code": "# Используй for или while\n", "expected_output": "1\n2\n3\n4\n5", "xp": 20
        },
        {
            "id": 7, "title": "Конвертация типов", "lead_name": "Маша (Junior)", "avatar": "👩",
            "messages": ["API вернуло цену в виде строки.", "Преобразуй '1500' в число, умножь на 2 и выведи результат."],
            "initial_code": "price_str = '1500'\n# Твой код:\n", "expected_output": "3000", "xp": 15
        },
        {
            "id": 8, "title": "Четное или нет?", "lead_name": "Олег (QA)", "avatar": "🕵️",
            "messages": ["Нужна функция проверки.", "Если число number четное, выведи 'Четное', иначе 'Нечетное'."],
            "initial_code": "number = 42\n# Твой код:\n", "expected_output": "Четное", "xp": 15
        },
        {
            "id": 9, "title": "Сумма списка", "lead_name": "Бухгалтер", "avatar": "👵",
            "messages": ["У меня тут массив расходов.", "Посчитай и выведи общую сумму с помощью встроенной функции sum()."],
            "initial_code": "expenses = [120, 50, 330, 100]\n# Твой код:\n", "expected_output": "600", "xp": 15
        },
        {
            "id": 10, "title": "Замена в строке", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Текст пришел с ошибкой.", "Замени все '-' на пробелы и выведи исправленный текст."],
            "initial_code": "text = 'Python-is-awesome'\n# Твой код:\n", "expected_output": "Python is awesome", "xp": 20
        }
    ],
    "medium": [
        {
            "id": 1, "title": "Чистка базы email-адресов", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Маркетологи выгрузили базу email, но там каша.", "Приведи все к нижнему регистру, удали дубли, отсортируй по алфавиту и выведи каждый с новой строки."],
            "initial_code": "emails = ['User@mail.com', 'admin@Corp.com', 'user@mail.com', 'test@Test.com']\n\n# Твой код:\n", 
            "expected_output": "admin@corp.com\ntest@test.com\nuser@mail.com", "xp": 50
        },
        {
            "id": 2, "title": "Частотный словарь", "lead_name": "Маша (Data Scientist)", "avatar": "👩‍🔬",
            "messages": ["У нас есть список тегов.", "Выведи, сколько раз встречается тег 'python' с помощью метода count()."],
            "initial_code": "tags = ['python', 'js', 'python', 'java', 'c++', 'python']\n# Твой код:\n", "expected_output": "3", "xp": 30
        },
        {
            "id": 3, "title": "Только четные", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Используй List Comprehension.", "Сделай новый список только из четных чисел массива и выведи его."],
            "initial_code": "nums = [1, 2, 3, 4, 5, 6, 7, 8]\n# Твой код:\n", "expected_output": "[2, 4, 6, 8]", "xp": 40
        },
        {
            "id": 4, "title": "Палиндром", "lead_name": "Олег (QA)", "avatar": "🕵️",
            "messages": ["Напиши проверку на палиндром.", "Выведи True, если строка читается одинаково с обеих сторон (используй срез [::-1])."],
            "initial_code": "word = 'radar'\n# Твой код:\n", "expected_output": "True", "xp": 35
        },
        {
            "id": 5, "title": "Объединение словарей", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["У нас два словаря с настройками.", "Объедини их в один (dict1.update(dict2)) и выведи значение по ключу 'theme'."],
            "initial_code": "d1 = {'lang': 'ru', 'theme': 'light'}\nd2 = {'theme': 'dark', 'font': 'arial'}\n# Твой код:\n", "expected_output": "dark", "xp": 40
        },
        {
            "id": 6, "title": "Факториал", "lead_name": "Маша (Junior)", "avatar": "👩",
            "messages": ["Помоги с математикой.", "Выведи факториал числа 5 (5 * 4 * 3 * 2 * 1). Можешь использовать цикл или math.factorial."],
            "initial_code": "import math\nn = 5\n# Твой код:\n", "expected_output": "120", "xp": 35
        },
        {
            "id": 7, "title": "Удаление гласных", "lead_name": "Дизайнер", "avatar": "🎨",
            "messages": ["Для логотипа нужно сократить слово.", "Удали все гласные (a, e, i, o, u) из строки и выведи результат."],
            "initial_code": "text = 'developer'\nvowels = 'aeiou'\n# Твой код:\n", "expected_output": "dvlpr", "xp": 45
        },
        {
            "id": 8, "title": "Безопасный доступ", "lead_name": "Олег (Безопасник)", "avatar": "🕵️",
            "messages": ["Скрипт падает, если ключа нет в словаре.", "Используй метод get(), чтобы получить 'port'. Если его нет, выведи 8080."],
            "initial_code": "config = {'host': 'localhost'}\n# Твой код:\n", "expected_output": "8080", "xp": 30
        },
        {
            "id": 9, "title": "Разворот слов", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Нужно развернуть порядок слов в предложении.", "Разбей строку, разверни список и склей обратно через пробел."],
            "initial_code": "sentence = 'Hello world python'\n# Твой код:\n", "expected_output": "python world Hello", "xp": 45
        },
        {
            "id": 10, "title": "Форматирование", "lead_name": "Бухгалтер", "avatar": "👵",
            "messages": ["Сделай красивый вывод.", "Используй f-строку, чтобы вывести 'Товар: Apple, Цена: 150'."],
            "initial_code": "item = 'Apple'\nprice = 150\n# Твой код:\n", "expected_output": "Товар: Apple, Цена: 150", "xp": 30
        }
    ],
    "hard": [
        {
            "id": 1, "title": "Сумма двух (Two Sum)", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Классика с собеседований.", "Найди в списке два числа, сумма которых равна 9. Выведи их индексы в виде списка [i, j]."],
            "initial_code": "nums = [2, 7, 11, 15]\ntarget = 9\n# Выведи индексы:\n", "expected_output": "[0, 1]", "xp": 70
        },
        {
            "id": 2, "title": "Числа Фибоначчи", "lead_name": "Маша (Data Scientist)", "avatar": "👩‍🔬",
            "messages": ["Нужна генерация ряда.", "Выведи первые 7 чисел Фибоначчи в виде списка."],
            "initial_code": "# 0, 1, 1, 2, 3, 5, 8\n# Выведи список:\n", "expected_output": "[0, 1, 1, 2, 3, 5, 8]", "xp": 60
        },
        {
            "id": 3, "title": "Валидация скобок", "lead_name": "Олег (QA)", "avatar": "🕵️",
            "messages": ["Проверь правильность закрытия скобок.", "Если строка '()[]{}' правильная, выведи True. Иначе False."],
            "initial_code": "s = '()[]{}'\n# Твой код:\n", "expected_output": "True", "xp": 80
        },
        {
            "id": 4, "title": "Плоский список", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Массив пришел вложенным.", "Преврати [[1,2], [3,4]] в [1, 2, 3, 4] и выведи."],
            "initial_code": "nested = [[1, 2], [3, 4]]\n# Твой код:\n", "expected_output": "[1, 2, 3, 4]", "xp": 65
        },
        {
            "id": 5, "title": "Исключения", "lead_name": "Сервер", "avatar": "🖥️",
            "messages": ["Скрипт ломается при делении на ноль.", "Напиши try/except. При ZeroDivisionError выведи 'Ошибка деления'."],
            "initial_code": "try:\n    print(10 / 0)\n# Допиши except:\n", "expected_output": "Ошибка деления", "xp": 50
        },
        {
            "id": 6, "title": "Группировка анаграмм", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Нужно сгруппировать слова, состоящие из одинаковых букв.", "Вход: ['eat', 'tea', 'tan', 'nat']. Выведи количество групп."],
            "initial_code": "words = ['eat', 'tea', 'tan', 'nat']\n# Твой код (подсказка: отсортируй буквы в слове и используй как ключ словаря):\n", "expected_output": "2", "xp": 90
        },
        {
            "id": 7, "title": "Транспонирование матрицы", "lead_name": "Маша (Data Scientist)", "avatar": "👩‍🔬",
            "messages": ["Нужно перевернуть матрицу.", "Вход: [[1, 2], [3, 4]]. Выведи транспонированную: [[1, 3], [2, 4]]."],
            "initial_code": "matrix = [[1, 2], [3, 4]]\n# Твой код:\n", "expected_output": "[[1, 3], [2, 4]]", "xp": 75
        },
        {
            "id": 8, "title": "Шифр Цезаря", "lead_name": "Олег (Безопасник)", "avatar": "🕵️",
            "messages": ["Зашифруй строку сдвигом на 1 вправо.", "Например, 'abc' -> 'bcd'. Выведи результат для 'hal'."],
            "initial_code": "text = 'hal'\n# Твой код (используй ord() и chr()):\n", "expected_output": "ibm", "xp": 80
        },
        {
            "id": 9, "title": "Класс Банка", "lead_name": "Алексей (Tech Lead)", "avatar": "🧔",
            "messages": ["Напиши класс Account с атрибутом balance.", "Сделай методы deposit(amount) и withdraw(amount). Пополни на 100, сними 40, выведи баланс."],
            "initial_code": "# Создай класс Account\n\n\n\nacc = Account(0)\nacc.deposit(100)\nacc.withdraw(40)\nprint(acc.balance)\n", "expected_output": "60", "xp": 70
        },
        {
            "id": 10, "title": "Декоратор", "lead_name": "Архитектор", "avatar": "🧠",
            "messages": ["Напиши простой декоратор @hello, который печатает 'Hi' перед вызовом функции.", "Задекорируй функцию func(), которая печатает 'World'."],
            "initial_code": "# Напиши декоратор\n\n\n\n\n@hello\ndef func():\n    print('World')\n\nfunc()", "expected_output": "Hi\nWorld", "xp": 100
        }
    ]
}

# ──────────────────────────────────────────────────────────────
# ROUTES — INTERNSHIP
# ──────────────────────────────────────────────────────────────

@app.route('/internship')
@login_required
def internship_hub():
    user = get_current_user()
    conn = get_db()
    # Получаем все решенные задачи пользователя
    rows = conn.execute(
        'SELECT task_id, difficulty FROM internship_progress WHERE user_id = ?', 
        (user['id'],)
    ).fetchall()
    conn.close()
    
    # Собираем выполненные задачи в множество (формат: "easy_1", "hard_5")
    completed_tasks = {f"{row['difficulty']}_{row['task_id']}" for row in rows}
    
    return render_template('internship/hub.html', user=user, tasks=INTERNSHIP_TASKS, completed_tasks=completed_tasks)

@app.route('/internship/<difficulty>/<int:task_id>')
@login_required
def internship_task(difficulty, task_id):
    user = get_current_user()
    
    if difficulty not in INTERNSHIP_TASKS:
        return redirect(url_for('internship_hub'))
        
    tasks_list = INTERNSHIP_TASKS[difficulty]
    
    task = None
    current_idx = -1
    for idx, t in enumerate(tasks_list):
        if t['id'] == task_id:
            task = t
            current_idx = idx
            break
            
    if not task:
        return redirect(url_for('internship_hub'))
        
    # Вычисляем ID следующей задачи внутри текущей сложности
    next_task_id = None
    if current_idx != -1 and current_idx < len(tasks_list) - 1:
        next_task_id = tasks_list[current_idx + 1]['id']
        
    conn = get_db()
    # Проверяем, решена ли задача
    progress = conn.execute(
        'SELECT * FROM internship_progress WHERE user_id = ? AND task_id = ? AND difficulty = ?',
        (user['id'], task_id, difficulty)
    ).fetchone()
    is_completed = bool(progress)
    
    # Получаем историю отправок кода
    history = conn.execute(
        'SELECT code, is_correct, created_at FROM internship_history WHERE user_id = ? AND task_id = ? AND difficulty = ? ORDER BY id DESC',
        (user['id'], task_id, difficulty)
    ).fetchall()
    history_list = [dict(row) for row in history]
    conn.close()
    
    # Если история есть, загружаем последний отправленный код, иначе дефолтный
    last_code = history_list[0]['code'] if history_list else task['initial_code']
        
    return render_template('internship/task.html', 
                           user=user, 
                           task=task, 
                           difficulty=difficulty,
                           task_id=task_id, # Передаем явно ID текущей задачи
                           next_task_id=next_task_id,
                           is_completed=is_completed,
                           history=history_list,
                           last_code=last_code)

@app.route('/api/internship-success', methods=['POST'])
@login_required
def internship_success():
    data = request.get_json()
    task_xp = data.get('xp', 0)
    task_id = data.get('task_id')
    difficulty = data.get('difficulty')
    
    conn = get_db()
    # Начисляем XP
    conn.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (task_xp, session['user_id']))
    
    # Сохраняем прогресс конкретной задачи
    if task_id and difficulty:
        try:
            conn.execute(
                'INSERT INTO internship_progress (user_id, task_id, difficulty) VALUES (?, ?, ?)',
                (session['user_id'], task_id, difficulty)
            )
        except sqlite3.IntegrityError:
            pass # Если уже есть в базе, игнорируем ошибку
            
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})


@app.route('/api/internship-attempt', methods=['POST'])
@login_required
def internship_attempt():
    data = request.get_json()
    task_xp = data.get('xp', 0)
    task_id = data.get('task_id')
    difficulty = data.get('difficulty')
    code = data.get('code', '')
    is_correct = 1 if data.get('is_correct') else 0
    
    conn = get_db()
    
    # 1. Сохраняем код в историю попыток
    conn.execute(
        'INSERT INTO internship_history (user_id, task_id, difficulty, code, is_correct) VALUES (?, ?, ?, ?, ?)',
        (session['user_id'], task_id, difficulty, code, is_correct)
    )
    
    # 2. Если решение верное, сохраняем прогресс и выдаем XP (если не было решено ранее)
    if is_correct:
        try:
            conn.execute(
                'INSERT INTO internship_progress (user_id, task_id, difficulty) VALUES (?, ?, ?)',
                (session['user_id'], task_id, difficulty)
            )
            conn.execute('UPDATE users SET xp = xp + ? WHERE id = ?', (task_xp, session['user_id']))
        except sqlite3.IntegrityError:
            pass # Задача уже была решена ранее, опыт повторно не даем
            
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

def init_internship_db():
    conn = get_db()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS internship_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            completed_at TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, task_id, difficulty)
        )
    ''')
    # Новая таблица для истории попыток
    conn.execute('''
        CREATE TABLE IF NOT EXISTS internship_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id INTEGER NOT NULL,
            difficulty TEXT NOT NULL,
            code TEXT NOT NULL,
            is_correct INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now', 'localtime'))
        )
    ''')
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    upgrade_db() 
    init_internship_db()
    app.run(debug=True, port=5000)
