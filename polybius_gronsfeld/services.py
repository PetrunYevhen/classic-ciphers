from . import ciphers
from .square import (
    CYRILLIC_LETTERS, CYRILLIC_DIGITS,
    LATIN_LETTERS, LATIN_DIGITS,
    build_square,
)

LANGUAGES = {"uk": "Українська", "lat": "Латинська"}
ALPHABETS = {
    "uk": (CYRILLIC_LETTERS, CYRILLIC_DIGITS),
    "lat": (LATIN_LETTERS, LATIN_DIGITS),
}

ALGORITHMS = {
    "coordinates": "Полібій: координати",
    "row-shift": "Полібій: зсув за рядками",
    "gronsfeld": "Гронсфельд",
}
POLYBIUS_CLASSES = {
    "coordinates": ciphers.PolybiusCoordinates,
    "row-shift": ciphers.PolybiusRowShift,
}

OPERATIONS = {"encrypt": "Шифрувати", "decrypt": "Розшифрувати"}


def make_square(language, keyword):
    if language not in ALPHABETS:
        raise ValueError(f"Непідтримувана мова: {language!r}.")
    letters, digits = ALPHABETS[language]
    return build_square(letters, digits, keyword)


def _make_cipher(language, algorithm, key):
    if algorithm in POLYBIUS_CLASSES:
        return POLYBIUS_CLASSES[algorithm](make_square(language, key))
    if algorithm == "gronsfeld":
        gronsfeld_class = getattr(ciphers, "Gronsfeld", None)
        if gronsfeld_class is None:
            raise ValueError("Шифр Гронсфельда ще не реалізовано в ciphers.py.")
        return gronsfeld_class(ALPHABETS[language][0], key)
    raise ValueError(f"Непідтримуваний алгоритм: {algorithm!r}.")


def process(language, algorithm, operation, key, text, strip_spaces=False):
    """Усі перевірки виконуються до обробки; результат повертається лише повністю."""
    if language not in LANGUAGES:
        raise ValueError(f"Непідтримувана мова: {language!r}.")
    if operation not in OPERATIONS:
        raise ValueError(f"Непідтримувана операція: {operation!r}.")
    cipher = _make_cipher(language, algorithm, key)
    action = getattr(cipher, operation)

    if strip_spaces:
        if operation != "encrypt":
            raise ValueError("Вилучення пробілів застосовується лише до шифрування.")
        text = "".join(character for character in text if not character.isspace())

    if algorithm == "coordinates":
        # рядки шифруються окремо, щоб зберегти переноси й кінцевий перенос
        return "\n".join(action(line) if line else "" for line in text.split("\n"))
    return action(text)
