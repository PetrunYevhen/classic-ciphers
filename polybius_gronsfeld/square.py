import unicodedata
from string import ascii_uppercase
from dataclasses import dataclass

CYRILLIC_LETTERS = 'АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ'
LATIN_LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
CYRILLIC_DIGITS = '012'
LATIN_DIGITS = '0123456789'

def build_square(letters, digits, keyword):
    base = letters + digits
    key = unicodedata.normalize("NFC", keyword).upper()

    if not key:
        raise ValueError("Ключове слово не може бути порожнім.")

    invalid = [character for character in key if character not in base]
    if invalid:
        raise ValueError(f"Ключове слово містить недопустимі символи: {invalid}")
    if not any(character in letters for character in key):
        raise ValueError("Ключове слово має містити хоча б одну літеру.")

    sequence = "".join(dict.fromkeys(key))
    for character in base:
        if character not in sequence:
            sequence += character

    assert len(sequence) == 36
    return [sequence[start:start + 6] for start in range(0, 36, 6)]

def build_lookup_tables(square):
    to_coord = {}
    from_coord = {}
    for row_number, row in enumerate(square, start=1):
        for column_number, letter in enumerate(row, start=1):
            coord = f"{row_number}{column_number}"
            to_coord[letter] = coord
            from_coord[coord] = letter

    return to_coord, from_coord

def build_shift_tables(square):
    shift_down = {}
    shift_up = {}

    for r, row in enumerate(square):
        for c, symbol in enumerate(row):
            shift_down[symbol] = square[(r+1) % 6][c]
            shift_up[symbol] = square[(r-1) % 6][c]

    return shift_down, shift_up