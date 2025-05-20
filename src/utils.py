# Utils.py
# Pdfix utils

import math

from pdfixsdk.Pdfix import PdfMatrix

pi = 3.1415926535897932384626433832795

# Mapping from ISO 639-1 language codes to Tesseract language identifiers
iso_to_tesseract = {
    "af": "afr",  # Afrikaans
    "am": "amh",  # Amharic
    "ar": "ara",  # Arabic
    "as": "asm",  # Assamese
    "az": "aze",  # Azerbaijani
    "be": "bel",  # Belarusian
    "bn": "ben",  # Bengali
    "bo": "bod",  # Tibetan
    "bs": "bos",  # Bosnian
    "br": "bre",  # Breton
    "bg": "bul",  # Bulgarian
    "ca": "cat",  # Catalan
    "ceb": "ceb",  # Cebuano
    "cs": "ces",  # Czech
    "zh": "chi_sim",  # Chinese
    "chr": "chr",  # Cherokee
    "co": "cos",  # Corsican
    "cy": "cym",  # Welsh
    "da": "dan",  # Danish
    "de": "deu",  # German
    "dv": "div",  # Divehi
    "dz": "dzo",  # Dzongkha
    "el": "ell",  # Greek
    "en": "eng",  # English
    "eo": "epo",  # Esperanto
    "et": "est",  # Estonian
    "eu": "eus",  # Basque
    "fo": "fao",  # Faroese
    "fa": "fas",  # Persian
    "fi": "fin",  # Finnish
    "fr": "fra",  # French
    "gd": "gla",  # Scottish Gaelic
    "ga": "gle",  # Irish
    "gl": "glg",  # Galician
    "gu": "guj",  # Gujarati
    "ht": "hat",  # Haitian Creole
    "he": "heb",  # Hebrew
    "hi": "hin",  # Hindi
    "hr": "hrv",  # Croatian
    "hu": "hun",  # Hungarian
    "hy": "hye",  # Armenian
    "id": "ind",  # Indonesian
    "is": "isl",  # Icelandic
    "it": "ita",  # Italian
    "ja": "jpn",  # Japanese
    "kn": "kan",  # Kannada
    "ka": "kat",  # Georgian
    "kk": "kaz",  # Kazakh
    "km": "khm",  # Khmer
    "ky": "kir",  # Kyrgyz
    "ko": "kor",  # Korean
    "lo": "lao",  # Lao
    "la": "lat",  # Latin
    "lv": "lav",  # Latvian
    "lt": "lit",  # Lithuanian
    "lb": "ltz",  # Luxembourgish
    "ml": "mal",  # Malayalam
    "mr": "mar",  # Marathi
    "mk": "mkd",  # Macedonian
    "mt": "mlt",  # Maltese
    "mn": "mon",  # Mongolian
    "ne": "nep",  # Nepali
    "nl": "nld",  # Dutch
    "no": "nor",  # Norwegian
    "oc": "oci",  # Occitan
    "or": "ori",  # Odia
    "pa": "pan",  # Punjabi
    "pl": "pol",  # Polish
    "pt": "por",  # Portuguese
    "ps": "pus",  # Pashto
    "ro": "ron",  # Romanian
    "ru": "rus",  # Russian
    "sa": "san",  # Sanskrit
    "si": "sin",  # Sinhala
    "sk": "slk",  # Slovak
    "sl": "slv",  # Slovenian
    "es": "spa",  # Spanish
    "sq": "sqi",  # Albanian
    "sr": "srp",  # Serbian
    "su": "sun",  # Sundanese
    "sw": "swa",  # Swahili
    "sv": "swe",  # Swedish
    "ta": "tam",  # Tamil
    "tt": "tat",  # Tatar
    "te": "tel",  # Telugu
    "tg": "tgk",  # Tajik
    "th": "tha",  # Thai
    "tr": "tur",  # Turkish
    "uk": "ukr",  # Ukrainian
    "ur": "urd",  # Urdu
    "uz": "uzb",  # Uzbek
    "vi": "vie",  # Vietnamese
    "yi": "yid",  # Yiddish
    "yo": "yor",  # Yoruba
}


def pdf_matrix_concat(m: PdfMatrix, m1: PdfMatrix, prepend: bool) -> PdfMatrix:
    ret = PdfMatrix()
    if prepend:
        swap = m
        m = m1
        m1 = swap
    ret.a = m.a * m1.a + m.b * m1.c
    ret.b = m.a * m1.b + m.b * m1.d
    ret.c = m.c * m1.a + m.d * m1.c
    ret.d = m.c * m1.b + m.d * m1.d
    ret.e = m.e * m1.a + m.f * m1.c + m1.e
    ret.f = m.e * m1.b + m.f * m1.d + m1.f
    return ret


def pdf_matrix_rotate(m: PdfMatrix, radian: float, prepend: bool) -> PdfMatrix:
    cos_value = math.cos(radian)
    sin_value = math.sin(radian)
    m1 = PdfMatrix()
    m1.a = cos_value
    m1.b = sin_value
    m1.c = -sin_value
    m1.d = cos_value
    return pdf_matrix_concat(m, m1, prepend)


def pdf_matrix_translate(m: PdfMatrix, x: float, y: float, prepend: bool) -> PdfMatrix:
    ret = m
    if prepend:
        ret.e = m.e + x * m.a + y + m.c
        ret.f = m.f + y * m.d + x * m.b
    ret.e = m.e + x
    ret.f = m.f + y
    return ret


def pdf_matrix_inverse(orig: PdfMatrix) -> PdfMatrix:
    inverse = PdfMatrix()
    i = orig.a * orig.d - orig.b * orig.c
    if abs(i) == 0:
        return inverse
    j = -i
    inverse.a = orig.d / i
    inverse.b = orig.b / j
    inverse.c = orig.c / j
    inverse.d = orig.a / i
    inverse.e = (orig.c * orig.f - orig.d * orig.e) / i
    inverse.f = (orig.a * orig.f - orig.b * orig.e) / j
    return inverse


def pdf_matrix_scale(m: PdfMatrix, sx: float, sy: float, prepend: bool) -> PdfMatrix:
    m.a *= sx
    m.d *= sy
    if prepend:
        m.b *= sx
        m.c *= sy
    m.b *= sy
    m.c *= sx
    m.e *= sx
    m.f *= sy
    return m


def translate_iso_to_tesseract(iso_lang: str) -> str | None:
    """
    Translate ISO language code to Tesseract language identifier.

    Args:
        iso_lang (str): Tesseract language identifier

    Returns:
        Corresponding Tesseract language identifier (str) or None if not found.
    """
    # Extract the first part of the ISO language code (e.g., 'en' from 'en-US')
    iso_lang_part = iso_lang.split("-")[0].lower()
    return iso_to_tesseract.get(iso_lang_part)
