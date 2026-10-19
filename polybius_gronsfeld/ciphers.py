import unicodedata
from .square import build_square, build_lookup_tables, build_shift_tables


class PolybiusCoordinates:
    def __init__(self, square):
        self.square = square
        self.to_coord, self.from_coord = build_lookup_tables(square)

    def encrypt(self, text):
        text = unicodedata.normalize("NFC", text).upper()
        coords = []
        for position, symbol in enumerate(text, start=1):
            if symbol not in self.to_coord:
                raise ValueError(f"Символ {symbol!r} на позиції {position} відсутній у квадраті.")
            coords.append(self.to_coord[symbol])

        return " ".join(coords)

    def decrypt(self, cipher):
        tokens = cipher.split(" ")
        symbol = []
        for number, token in enumerate(tokens, start=1):
            is_valid = len(token) == 2 and all(character in "123456" for character in token)
            if not is_valid:
                raise ValueError(f"Токен {number}: {token!r} не є координатою. "
                    "Очікується дві цифри від 1 до 6.")
            symbol.append(self.from_coord[token])
        return "".join(symbol)

class PolybiusRowShift:
    def __init__(self, square):
        self.square = square
        self.shift_down, self.shift_up = build_shift_tables(square)

    def encrypt(self, text):
        text = unicodedata.normalize("NFC", text).upper()
        return "".join(self.shift_down.get(symbol, symbol) for symbol in text)

    def decrypt(self, cipher):
        cipher = unicodedata.normalize("NFC", cipher).upper()
        return "".join(self.shift_up.get(symbol, symbol) for symbol in cipher)

class Gronsfeld:
    def __init__(self, letters, key):
        if not isinstance(key, str):
            raise ValueError("Цифровий ключ має бути рядком.")
        if not key:
            raise ValueError("Цифровий ключ не може бути порожнім.")
        if not all(character in "0123456789" for character in key):
            raise ValueError("Цифровий ключ має містити лише цифри 0-9.")
        if key.strip("0") == "":
            raise ValueError("Цифровий ключ не може складатися лише з нулів.")

        self.letters = letters
        self.shifts = [int(character) for character in key]
        self.index_of = {letter: index for index, letter in enumerate(letters)}

    def _shift(self, text, direction):
        text = unicodedata.normalize("NFC", text).upper()

        result = []
        used = 0
        for symbol in text:
            if symbol not in self.index_of:
                result.append(symbol)
                continue
            shift = self.shifts[used % len(self.shifts)]
            new_index = (self.index_of[symbol] + direction * shift) % len(self.letters)
            result.append(self.letters[new_index])
            used += 1

        return "".join(result)

    def encrypt(self, text):
        return self._shift(text, 1)

    def decrypt(self, cipher):
        return self._shift(cipher, -1)
