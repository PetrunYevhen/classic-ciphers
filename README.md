# Лабораторна робота 2. Квадрат Полібія та шифр Гронсфельда

Навчальна веб-програма (Django) з трьома режимами: `coordinates`, `row shift`, Гронсфельд.
Алфавіти: український і латинський. Не призначена для реального захисту даних.

## Середовище

* Python 3.14.6 (перевірено)
* Django 6.1.2 (залежності: asgiref, sqlparse; див. `requirements.txt`)

## Запуск (з кореня репозиторію)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 manage.py runserver
```

Відкрити http://127.0.0.1:8000/.

## Тести

```bash
python3 manage.py test
```

## Структура

* `polybius_gronsfeld/square.py` — алфавіти, побудова квадрата 6x6, таблиці пошуку
* `polybius_gronsfeld/ciphers.py` — класи `PolybiusCoordinates`, `PolybiusRowShift`, `Gronsfeld`
* `polybius_gronsfeld/services.py` — вибір алгоритму та перевірки (без Django)
* `polybius_gronsfeld/views.py`, `urls.py`, `templates/` — веб-інтерфейс
* `polybius_gronsfeld/tests.py` — автоматизовані тести
