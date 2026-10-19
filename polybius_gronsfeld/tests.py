import random

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase

from . import services
from .square import (
    CYRILLIC_LETTERS, CYRILLIC_DIGITS,
    LATIN_LETTERS, LATIN_DIGITS,
    build_square, build_lookup_tables,
)

UK_KEY = "БЕЗПЕКА"
LAT_KEY = "SECURITY"


def encrypt(language, algorithm, key, text, **options):
    return services.process(language, algorithm, "encrypt", key, text, **options)


def decrypt(language, algorithm, key, text):
    return services.process(language, algorithm, "decrypt", key, text)


class ControlVectorTests(SimpleTestCase):
    VECTORS = [
        ("Полібій coordinates, укр.", "coordinates", "uk", UK_KEY, "СЛАВА", "44 35 16 21 16"),
        ("Полібій coordinates, лат.", "coordinates", "lat", LAT_KEY, "HELLO", "32 12 35 35 42"),
        ("Полібій row shift, укр.", "row-shift", "uk", UK_KEY, "СЛАВА", "ЧТЖИЖ"),
        ("Полібій row shift, лат.", "row-shift", "lat", LAT_KEY, "HELLO", "OYVVZ"),
        ("Гронсфельд, укр.", "gronsfeld", "uk", "31415", "СЛАВА УКРАЇНІ", "ФМҐГД ЦЛФБНРЇ"),
        ("Гронсфельд, лат.", "gronsfeld", "lat", "2718", "HELLO WORLD", "JLMTQ DPZNK"),
    ]

    def test_encrypt_matches_expected(self):
        for name, algorithm, language, key, plain, expected in self.VECTORS:
            with self.subTest(name):
                self.assertEqual(encrypt(language, algorithm, key, plain), expected)

    def test_decrypt_restores_plaintext(self):
        for name, algorithm, language, key, plain, expected in self.VECTORS:
            with self.subTest(name):
                self.assertEqual(decrypt(language, algorithm, key, expected), plain)


class SquareTests(SimpleTestCase):
    def test_ukrainian_square(self):
        self.assertEqual(
            build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, UK_KEY),
            ["БЕЗПКА", "ВГҐДЄЖ", "ИІЇЙЛМ", "НОРСТУ", "ФХЦЧШЩ", "ЬЮЯ012"],
        )

    def test_latin_square(self):
        self.assertEqual(
            build_square(LATIN_LETTERS, LATIN_DIGITS, LAT_KEY),
            ["SECURI", "TYABDF", "GHJKLM", "NOPQVW", "XZ0123", "456789"],
        )

    def test_size_and_uniqueness(self):
        for letters, digits, keyword in ((CYRILLIC_LETTERS, CYRILLIC_DIGITS, "ЄДНІСТЬ"),
                                         (LATIN_LETTERS, LATIN_DIGITS, "Zebra9")):
            with self.subTest(keyword):
                square = build_square(letters, digits, keyword)
                symbols = "".join(square)
                self.assertEqual(len(square), 6)
                self.assertTrue(all(len(row) == 6 for row in square))
                self.assertEqual(len(set(symbols)), 36)
                self.assertEqual(set(symbols), set(letters + digits))

    def test_repeats_removed_keeping_first_occurrence(self):
        self.assertEqual(build_square(LATIN_LETTERS, LATIN_DIGITS, "BANANA")[0], "BANCDE")

    def test_keyword_is_uppercased(self):
        self.assertEqual(build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, "безпека"),
                         build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, UK_KEY))

    def test_keyword_is_nfc_normalized(self):
        decomposed = "ЇЖАК"  # Ї як І + U+0308
        composed = "ЇЖАК"
        self.assertNotEqual(decomposed, composed)
        self.assertEqual(build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, decomposed),
                         build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, composed))

    def test_invalid_keywords_rejected(self):
        cases = {
            "порожнє": ("uk", ""),
            "лише цифри": ("uk", "012"),
            "пробіл": ("lat", "SECRET KEY"),
            "латиниця в укр. квадраті": ("uk", "SECURITY"),
            "кирилиця в лат. квадраті": ("lat", "БЕЗПЕКА"),
            "розділовий знак": ("lat", "KEY!"),
        }
        for name, (language, keyword) in cases.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    services.make_square(language, keyword)

    def test_lookup_tables_are_inverse(self):
        square = build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, UK_KEY)
        to_coord, from_coord = build_lookup_tables(square)
        self.assertEqual(len(to_coord), 36)
        self.assertEqual(len(from_coord), 36)
        for symbol, coord in to_coord.items():
            self.assertEqual(from_coord[coord], symbol)


class CoordinatesTests(SimpleTestCase):
    def test_first_and_last_cells(self):
        self.assertEqual(encrypt("uk", "coordinates", UK_KEY, "Б"), "11")
        self.assertEqual(encrypt("uk", "coordinates", UK_KEY, "2"), "66")
        self.assertEqual(decrypt("uk", "coordinates", UK_KEY, "11 66"), "Б2")

    def test_first_and_last_rows(self):
        self.assertEqual(encrypt("uk", "coordinates", UK_KEY, "БЕЗПКА"), "11 12 13 14 15 16")
        self.assertEqual(encrypt("uk", "coordinates", UK_KEY, "ЬЮЯ012"), "61 62 63 64 65 66")

    def test_invalid_tokens_rejected(self):
        for bad in ("00", "17", "67", "7", "1", "111", "ab", "11  12", "11 12 ", " 11",
                    "11,12", "１１"):
            with self.subTest(repr(bad)):
                with self.assertRaises(ValueError):
                    decrypt("uk", "coordinates", UK_KEY, bad)

    def test_empty_text_gives_empty_result(self):
        self.assertEqual(encrypt("uk", "coordinates", UK_KEY, ""), "")
        self.assertEqual(decrypt("uk", "coordinates", UK_KEY, ""), "")

    def test_token_61_is_a_valid_cell(self):
        # клітинка (6, 1) існує: без неї Ь неможливо розшифрувати
        self.assertEqual(decrypt("uk", "coordinates", UK_KEY, "61"), "Ь")

    def test_error_message_names_the_token(self):
        with self.assertRaises(ValueError) as caught:
            decrypt("uk", "coordinates", UK_KEY, "11 17")
        self.assertIn("'17'", str(caught.exception))

    def test_strict_mode_rejects_space_and_punctuation(self):
        for text in ("СЛОВО ОДИН", "СЛОВО!", "A"):
            with self.subTest(text):
                with self.assertRaises(ValueError):
                    encrypt("uk", "coordinates", UK_KEY, text)

    def test_lowercase_input_is_uppercased(self):
        self.assertEqual(encrypt("lat", "coordinates", "security", "hello"), "32 12 35 35 42")

    def test_decrypt_has_no_separators_between_letters(self):
        self.assertEqual(decrypt("uk", "coordinates", UK_KEY, "44 35 16 21 16"), "СЛАВА")

    def test_multiline_text_keeps_line_breaks(self):
        cipher = encrypt("lat", "coordinates", LAT_KEY, "HELLO\n\nWORLD\n")
        self.assertEqual(cipher, "32 12 35 35 42\n\n46 42 15 35 25\n")
        self.assertEqual(decrypt("lat", "coordinates", LAT_KEY, cipher), "HELLO\n\nWORLD\n")

    def test_strip_spaces_is_an_explicit_operation(self):
        self.assertEqual(encrypt("lat", "coordinates", LAT_KEY, "HE LLO", strip_spaces=True),
                         "32 12 35 35 42")
        with self.assertRaises(ValueError):
            encrypt("lat", "coordinates", LAT_KEY, "HE LLO")

    def test_strip_spaces_rejected_for_decrypt(self):
        with self.assertRaises(ValueError):
            services.process("lat", "coordinates", "decrypt", LAT_KEY, "11", strip_spaces=True)


class RowShiftTests(SimpleTestCase):
    def test_wraps_from_sixth_row_to_first(self):
        self.assertEqual(encrypt("uk", "row-shift", UK_KEY, "Ь"), "Б")
        self.assertEqual(encrypt("lat", "row-shift", LAT_KEY, "4"), "S")

    def test_decrypt_wraps_from_first_row_to_sixth(self):
        self.assertEqual(decrypt("uk", "row-shift", UK_KEY, "Б"), "Ь")
        self.assertEqual(decrypt("lat", "row-shift", LAT_KEY, "S"), "4")

    def test_foreign_characters_preserved(self):
        self.assertEqual(encrypt("uk", "row-shift", UK_KEY, "СЛАВА, ОК!"), "ЧТЖИЖ, ХЄ!")

    def test_every_cell_moves_exactly_one_row(self):
        from .square import build_shift_tables
        square = build_square(CYRILLIC_LETTERS, CYRILLIC_DIGITS, UK_KEY)
        shift_down, shift_up = build_shift_tables(square)
        for r, row in enumerate(square):
            for c, symbol in enumerate(row):
                self.assertEqual(shift_down[symbol], square[(r + 1) % 6][c])
                self.assertEqual(shift_up[symbol], square[(r - 1) % 6][c])


class LanguageTests(SimpleTestCase):
    def test_special_ukrainian_letters(self):
        for letter in "ҐЄІЇ":
            with self.subTest(letter):
                cipher = encrypt("uk", "coordinates", UK_KEY, letter)
                self.assertEqual(decrypt("uk", "coordinates", UK_KEY, cipher), letter)

    def test_latin_a_and_z(self):
        self.assertEqual(encrypt("lat", "coordinates", LAT_KEY, "AZ"), "23 52")

    def test_alphabet_is_not_guessed(self):
        with self.assertRaises(ValueError):
            encrypt("uk", "coordinates", UK_KEY, "HELLO")
        with self.assertRaises(ValueError):
            encrypt("auto", "coordinates", UK_KEY, "СЛАВА")


class ModeValidationTests(SimpleTestCase):
    def test_unknown_operation_and_algorithm(self):
        with self.assertRaises(ValueError):
            services.process("lat", "coordinates", "hash", LAT_KEY, "A")
        with self.assertRaises(ValueError):
            encrypt("lat", "caesar", LAT_KEY, "A")


class GronsfeldTests(SimpleTestCase):
    def test_leading_zero_is_kept(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "01", "HELLO"), "HFLMO")
        self.assertNotEqual(encrypt("lat", "gronsfeld", "01", "HELLO"),
                            encrypt("lat", "gronsfeld", "1", "HELLO"))

    def test_key_nine(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "9", "ABC"), "JKL")
        self.assertEqual(decrypt("lat", "gronsfeld", "9", "JKL"), "ABC")

    def test_shift_wraps_modulo_alphabet_size(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "9", "Z"), "I")
        self.assertEqual(encrypt("uk", "gronsfeld", "9", "Я"), "Ж")

    def test_key_longer_than_text(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "1234567890123", "AAA"), "BCD")

    def test_long_key_roundtrip(self):
        key = "9081726354" * 10
        cipher = encrypt("uk", "gronsfeld", key, "ДОВГИЙ КЛЮЧ")
        self.assertEqual(decrypt("uk", "gronsfeld", key, cipher), "ДОВГИЙ КЛЮЧ")

    def test_invalid_keys_rejected(self):
        bad_keys = {
            "порожній": "", "лише нулі": "0000", "один нуль": "0", "літери": "12a",
            "пробіл": "1 2", "знак": "-5", "ціле число": 123,
        }
        for name, key in bad_keys.items():
            with self.subTest(name):
                with self.assertRaises(ValueError):
                    encrypt("lat", "gronsfeld", key, "HELLO")

    def test_space_does_not_consume_key_digit(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "12", "A A"), "B C")

    def test_digits_and_punctuation_do_not_advance_key(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "12", "A1,2.A!"), "B1,2.C!")

    def test_foreign_alphabet_letters_are_not_shifted(self):
        self.assertEqual(encrypt("uk", "gronsfeld", "5", "AБ"), "AЕ")

    def test_empty_text(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "123", ""), "")


class RoundTripTests(SimpleTestCase):
    STRICT = {
        "uk": ["СЛАВА", "УКРАЇНІ", "ҐЕДЗЬ", "ЄВРОПА", "ЇЖАК", "ШИФР012", "Я", "ЬЮЯ", "0",
               "ПРИВІТСВІТ", "ГРОНСФЕЛЬД", "ЩУКА", "КОЛО2", "ЙОГУРТ", "ХЛІБ"],
        "lat": ["HELLO", "WORLD", "ZEBRA", "A", "Z", "POLYBIUS", "GRONSFELD", "QUICKFOX9",
                "0123456789", "SECURITY", "ABCXYZ", "TESTING2026"],
    }
    FREE = {
        "uk": ["Слава Україні!", "Героям слава.\nРядок 2.", "Ґанок, єнот, їжак.", "Тест 123, 456;"],
        "lat": ["Hello, World!", "Line one\nLine two\n", "Quick brown fox, 42 jumps.", "  spaces  "],
    }
    KEYS = {"uk": UK_KEY, "lat": LAT_KEY}

    def assert_roundtrip(self, language, algorithm, key, message):
        cipher = encrypt(language, algorithm, key, message)
        self.assertEqual(decrypt(language, algorithm, key, cipher), message.upper())

    def test_coordinates(self):
        for language, messages in self.STRICT.items():
            for message in messages:
                with self.subTest(language=language, message=message):
                    self.assert_roundtrip(language, "coordinates", self.KEYS[language], message)

    def test_row_shift(self):
        for language in ("uk", "lat"):
            for message in self.STRICT[language] + self.FREE[language]:
                with self.subTest(language=language, message=message):
                    self.assert_roundtrip(language, "row-shift", self.KEYS[language], message)

    def test_gronsfeld(self):
        for language in ("uk", "lat"):
            for message in self.STRICT[language] + self.FREE[language]:
                for key in ("31415", "0001", "9", "2718281828"):
                    with self.subTest(language=language, message=message, key=key):
                        self.assert_roundtrip(language, "gronsfeld", key, message)

    def test_randomized_property(self):
        rng = random.Random(2026)  # фіксоване зерно: запуск відтворюваний
        alphabets = {"uk": (CYRILLIC_LETTERS, CYRILLIC_DIGITS), "lat": (LATIN_LETTERS, LATIN_DIGITS)}
        checks = 0
        for language, (letters, digits) in alphabets.items():
            symbols = letters + digits
            for _ in range(100):
                keyword = rng.choice(letters) + "".join(
                    rng.choice(symbols) for _ in range(rng.randint(0, 12)))
                digit_key = rng.choice("123456789") + "".join(
                    rng.choice("0123456789") for _ in range(rng.randint(0, 15)))
                strict = "".join(rng.choice(symbols) for _ in range(rng.randint(0, 40)))
                free = "".join(rng.choice(symbols + " .,!?-\n") for _ in range(rng.randint(0, 40)))
                self.assert_roundtrip(language, "coordinates", keyword, strict)
                self.assert_roundtrip(language, "row-shift", keyword, free)
                self.assert_roundtrip(language, "gronsfeld", digit_key, free)
                checks += 3
        self.assertEqual(checks, 600)


class FormattingTests(SimpleTestCase):
    def test_row_shift_keeps_spaces_newlines_and_punctuation(self):
        self.assertEqual(encrypt("lat", "row-shift", LAT_KEY, "HI, 5!\n"), "OF, E!\n")

    def test_gronsfeld_keeps_newlines(self):
        self.assertEqual(encrypt("lat", "gronsfeld", "12", "A\nA\n"), "B\nC\n")


class FileAndUiTests(SimpleTestCase):
    def post(self, **fields):
        data = {"language": "uk", "algorithm": "coordinates", "operation": "encrypt",
                "key": UK_KEY, "text": "СЛАВА", "action": "run"}
        data.update(fields)
        return self.client.post("/", data)

    def test_page_opens(self):
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_result_and_square_are_shown(self):
        response = self.post()
        self.assertContains(response, "44 35 16 21 16")
        self.assertContains(response, "Активний квадрат")

    def test_error_is_shown_as_text(self):
        response = self.post(text="СЛАВА!")
        self.assertContains(response, "Помилка:")
        self.assertNotContains(response, 'id="result"')

    def test_download_returns_utf8_attachment(self):
        response = self.post(action="download", algorithm="row-shift")
        self.assertEqual(response["Content-Type"], "text/plain; charset=utf-8")
        self.assertIn("attachment", response["Content-Disposition"])
        self.assertEqual(response.content.decode("utf-8"), "ЧТЖИЖ")

    def test_failed_run_returns_no_download(self):
        response = self.post(action="download", text="!")
        self.assertNotIn("Content-Disposition", response)
        self.assertContains(response, "Помилка:")

    def test_multiline_utf8_file_with_trailing_newline(self):
        uploaded = SimpleUploadedFile("in.txt", "ЛА\nВА\n".encode("utf-8"))
        response = self.post(file=uploaded, text="")
        self.assertContains(response, "35 16\n21 16\n")

    def test_utf8_bom_and_crlf_file(self):
        uploaded = SimpleUploadedFile("in.txt", b"\xef\xbb\xbf\xd0\x9b\xd0\x90\r\n")
        response = self.post(file=uploaded, text="")
        self.assertContains(response, "35 16")

    def test_invalid_utf8_file_is_reported(self):
        uploaded = SimpleUploadedFile("bad.txt", b"\xff\xfe\xfa")
        response = self.post(file=uploaded)
        self.assertContains(response, "UTF-8")
        self.assertContains(response, "Помилка:")
