"""Collation tables for the Mods list sort keys and letter headers in all 18 game languages (fml_patch fmlColl).

A sort key is one group character (which script the name starts with, in the order the game language wants) plus
one or two rank characters per letter. Ranks are private-use characters, so plain string comparison sorts by them:
  Latin    U+E100 + base letter * 4 + level   (level 1..3 = a language's own letters: Czech C, then its own C-caron)
  Cyrillic U+E200 + position in the unified Russian / Ukrainian alphabet (Yo ranks as Ye)
  Arabic   U+E300 + position in the Arabic alphabet (every presentation form = its letter, alef variants = alef,
           lam-alef ligatures = lam + alef, harakat and tatweel dropped)
  Kana     U+E400 + gojuon position (katakana = hiragana, small = large, voiced = unvoiced, long-vowel mark dropped)
Hangul syllables and CJK ideographs keep their own character (Unicode order is already right for Hangul; ideographs
have no reading to sort by). Anything else (digits, symbols, other cased scripts) keeps its lower-case character.
The header is the first significant letter's group: the base letter (or the language's own letter) upper case, the
Cyrillic / Arabic letter, the kana row, the Hangul initial as its syllable with a (ga, na, da ...), the ideograph
header, or "#" for digits and symbols. ref_key() is the reference the bytecode follows (used by the tests)."""
import unicodedata

DROP, NONE = '', ''      # rank of a dropped character / no second rank
SCRIPTS = ['sym', 'digit', 'latin', 'cyr', 'arab', 'hangul', 'kana', 'cjk', 'other']
LANG_IDX_NOTE = 'fmlNames index FAVS_IDX + 1: the game text language code in lower case (newer scripts only)'

# --- Latin: every letter whose decomposition starts with an ASCII letter, plus the ones without a decomposition
LATIN_EXTRA = {'ł': 'l', 'Ł': 'l', 'đ': 'd', 'Đ': 'd', 'ø': 'o', 'Ø': 'o', 'ı': 'i', 'ħ': 'h', 'Ħ': 'h',
               'ŧ': 't', 'Ŧ': 't', 'ð': 'd', 'Ð': 'd', 'ŀ': 'l', 'Ŀ': 'l', 'ƀ': 'b', 'ɨ': 'i', 'ʉ': 'u',
               'ſ': 's', 'ƒ': 'f', 'Ƒ': 'f'}
LATIN_TWO = {'ß': 'ss', 'ẞ': 'ss', 'æ': 'ae', 'Æ': 'ae', 'œ': 'oe', 'Œ': 'oe', 'ĳ': 'ij', 'Ĳ': 'ij',
             'þ': 'th', 'Þ': 'th', 'ﬀ': 'ff', 'ﬁ': 'fi', 'ﬂ': 'fl', 'ﬃ': 'ff', 'ﬄ': 'ff', 'ﬅ': 'st', 'ﬆ': 'st'}


def latin_base(ch):
    if ch in LATIN_EXTRA:
        return LATIN_EXTRA[ch]
    if 0xFF21 <= ord(ch) <= 0xFF3A or 0xFF41 <= ord(ch) <= 0xFF5A:
        ch = unicodedata.normalize('NFKC', ch)      # full-width letters (Japanese / Chinese / Korean input)
    d = unicodedata.normalize('NFD', ch)
    b = d[0].lower()
    if 'a' <= b <= 'z' and all(unicodedata.combining(x) for x in d[1:]):
        return b
    return None


def lrank(base, level=0):
    return chr(0xE100 + (ord(base) - 97) * 4 + level)


# a language's own letters: char -> (base, level, header)
def _own(spec):
    out = {}
    for base, level, letters in spec:
        for ch in letters:
            out[ch] = (base, level, letters[0] if letters[0].isupper() else letters[0].upper())
    return out


OWN = {
    'cz': _own([('c', 1, 'Čč'), ('r', 1, 'Řř'), ('s', 1, 'Šš'), ('z', 1, 'Žž')]),
    'pl': _own([('a', 1, 'Ąą'), ('c', 1, 'Ćć'), ('e', 1, 'Ęę'), ('l', 1, 'Łł'), ('n', 1, 'Ńń'), ('o', 1, 'Óó'),
                ('s', 1, 'Śś'), ('z', 1, 'Źź'), ('z', 2, 'Żż')]),
    'hu': _own([('o', 1, 'ÖöŐőÕõ'), ('u', 1, 'ÜüŰűÛû')]),    # õ / û: old spellings of ő / ű
    'tr': _own([('c', 1, 'Çç'), ('g', 1, 'Ğğ'), ('i', 1, 'İiÎî'), ('o', 1, 'Öö'), ('s', 1, 'Şş'), ('u', 1, 'Üü')]),
    'es': _own([('n', 1, 'Ññ')]),
}
OWN['esmx'] = OWN['es']

# --- Cyrillic: the Russian and Ukrainian alphabets merged (each language only uses its own letters)
CYR = ['Аа', 'Бб', 'Вв', 'Гг', 'Ґґ', 'Дд', 'ЕеЁё', 'Єє', 'Жж', 'Зз', 'Ии', 'Іі', 'Її', 'Йй', 'Кк', 'Лл', 'Мм', 'Нн',
       'Оо', 'Пп', 'Рр', 'Сс', 'Тт', 'Уу', 'Фф', 'Хх', 'Цц', 'Чч', 'Шш', 'Щщ', 'Ъъ', 'Ыы', 'Ьь', 'Ээ', 'Юю', 'Яя']

# --- Arabic: letters in alphabet order; variants share their letter's rank
AR = [('ء',), ('ا', 'آ', 'أ', 'إ', 'ٱ'), ('ب',), ('پ',), ('ت',), ('ث',), ('ج',), ('چ',), ('ح',), ('خ',), ('د',),
      ('ذ',), ('ر',), ('ز',), ('ژ',), ('س',), ('ش',), ('ص',), ('ض',), ('ط',), ('ظ',), ('ع',), ('غ',), ('ف', 'ڤ'),
      ('ق',), ('ك', 'ک'), ('گ',), ('ل',), ('م',), ('ن',), ('ه', 'ة', 'ھ', 'ہ', 'ە', 'ۀ', 'ۂ', 'ۃ'), ('و', 'ؤ'),
      ('ي', 'ى', 'ئ', 'ی', 'ې', 'ۍ', 'ێ')]
AR_DROP = [chr(c) for c in list(range(0x064B, 0x0660)) + [0x0670, 0x0640, 0x06D6, 0x06D7, 0x06D8, 0x06D9, 0x06DA,
                                                         0x06DB, 0x06DC, 0x06DF, 0x06E0, 0x06E1, 0x06E2, 0x06E3,
                                                         0x06E4, 0x06E7, 0x06E8, 0x06EA, 0x06EB, 0x06EC, 0x06ED]]

# --- kana: gojuon rows; each entry = the hiragana letters sharing a rank
KANA_ROWS = [('あ', 'あいうえお'), ('か', 'かきくけこ'), ('さ', 'さしすせそ'), ('た', 'たちつてと'), ('な', 'なにぬねの'),
             ('は', 'はひふへほ'), ('ま', 'まみむめも'), ('や', 'やゆよ'), ('ら', 'らりるれろ'), ('わ', 'わゐゑをん')]
KANA_SMALL = {'ぁ': 'あ', 'ぃ': 'い', 'ぅ': 'う', 'ぇ': 'え', 'ぉ': 'お', 'っ': 'つ', 'ゃ': 'や', 'ゅ': 'ゆ', 'ょ': 'よ',
              'ゎ': 'わ', 'ゕ': 'か', 'ゖ': 'け', 'ゔ': 'う'}
HANGUL_HDR = '가가나다다라마바바사사아자자차카타파하'   # the 19 initials, doubled ones under their single one
IDEO_HDR = {'cn': '汉'}
IDEO_DEFAULT = '漢'

# --- script order per game language: GORD[script index] = the group character
ORDER = {
    None: ['sym', 'digit', 'latin', 'cyr', 'arab', 'hangul', 'kana', 'cjk', 'other'],
    'ru': ['sym', 'digit', 'cyr', 'latin', 'arab', 'hangul', 'kana', 'cjk', 'other'],
    'ar': ['sym', 'digit', 'arab', 'latin', 'cyr', 'hangul', 'kana', 'cjk', 'other'],
    'kr': ['sym', 'digit', 'hangul', 'latin', 'cyr', 'arab', 'kana', 'cjk', 'other'],
    'jp': ['sym', 'digit', 'kana', 'cjk', 'latin', 'cyr', 'arab', 'hangul', 'other'],
    'cn': ['sym', 'digit', 'cjk', 'latin', 'cyr', 'arab', 'hangul', 'kana', 'other'],
}
ORDER['ua'] = ORDER['ru']
ORDER['zh'] = ORDER['cn']
LANGS = ['ar', 'br', 'cn', 'cz', 'de', 'en', 'es', 'esmx', 'fr', 'hu', 'it', 'jp', 'kr', 'pl', 'ru', 'tr', 'ua', 'zh']


def gord(lang):
    order = ORDER.get(lang, ORDER[None])
    return ''.join(chr(ord('A') + order.index(s)) for s in SCRIPTS)


def build():
    """-> (SRC, RANK, RANK2, HDR, GRP): parallel strings; GRP = script index digit"""
    rows = {}

    def put(ch, r1, r2, hdr, grp):
        if ch not in rows:
            rows[ch] = (r1, r2, hdr, str(SCRIPTS.index(grp)))

    for cp in list(range(0x41, 0x5B)) + list(range(0x61, 0x7B)) + list(range(0xC0, 0x250)) + \
            list(range(0x1E00, 0x1F00)) + list(range(0xFB00, 0xFB07)) + list(range(0xFF21, 0xFF3B)) + \
            list(range(0xFF41, 0xFF5B)):
        ch = chr(cp)
        if ch in LATIN_TWO:
            two = LATIN_TWO[ch]
            put(ch, lrank(two[0]), lrank(two[1]), two[0].upper(), 'latin')
            continue
        b = latin_base(ch)
        if b:
            put(ch, lrank(b), NONE, b.upper(), 'latin')
    for i, letters in enumerate(CYR):
        for ch in letters:
            put(ch, chr(0xE200 + i), NONE, letters[0], 'cyr')
    ar_rank = {}
    for i, group in enumerate(AR):
        for ch in group:
            ar_rank[ch] = (chr(0xE300 + i), group[0])
            put(ch, chr(0xE300 + i), NONE, group[0], 'arab')
    for ch in AR_DROP:
        put(ch, DROP, NONE, '#', 'arab')
    # Arabic-Indic and Persian digits rank as their ASCII digit
    for i in range(10):
        put(chr(0x0660 + i), str(i), NONE, '#', 'digit')
        put(chr(0x06F0 + i), str(i), NONE, '#', 'digit')
    # invisible marks (direction marks, zero-width, no-break / ideographic spaces) never count
    for cp in list(range(0x200B, 0x2010)) + list(range(0x202A, 0x202F)) + list(range(0x2066, 0x206A)) + \
            [0xFEFF, 0x00A0, 0x3000]:
        put(chr(cp), DROP, NONE, '#', 'sym')
    # presentation forms (and the yeh / heh forms the game's own text uses): their letters
    for cp in list(range(0xFB50, 0xFE00)) + list(range(0xFE70, 0xFEFF)) + [0x06BE, 0x06C1, 0x06CC]:
        ch = chr(cp)
        if ch in rows:
            continue
        d = unicodedata.normalize('NFKC', ch)
        letters = [x for x in d if x in ar_rank]
        if not letters:
            if d and all(x in AR_DROP or unicodedata.combining(x) or x == ' ' for x in d):
                put(ch, DROP, NONE, '#', 'arab')
            continue
        r2 = ar_rank[letters[1]][0] if len(letters) > 1 else NONE
        put(ch, ar_rank[letters[0]][0], r2, ar_rank[letters[0]][1], 'arab')
    kana_rank = {}
    pos = 0
    for row_hdr, letters in KANA_ROWS:
        for ch in letters:
            kana_rank[ch] = (chr(0xE400 + pos), row_hdr)
            pos += 1
    for cp in list(range(0x3041, 0x3097)) + list(range(0x30A1, 0x30FB)) + list(range(0xFF66, 0xFF9E)):
        ch = chr(cp)
        h = unicodedata.normalize('NFKC', ch)
        if 0x30A1 <= ord(h[0]) <= 0x30F6:
            h = chr(ord(h[0]) - 0x60) + h[1:]
        h = {'ヷ': 'わ', 'ヸ': 'ゐ', 'ヹ': 'ゑ', 'ヺ': 'を', 'ヴ': 'う'}.get(h, h)
        h = KANA_SMALL.get(h, h)
        base = unicodedata.normalize('NFD', h)[0]
        if base in kana_rank:
            put(ch, kana_rank[base][0], NONE, kana_rank[base][1], 'kana')
    for ch in 'ーｰ゛゜ﾞﾟ':
        put(ch, DROP, NONE, '#', 'kana')
    src = ''.join(rows)
    return (src, ''.join(r[0] for r in rows.values()), ''.join(r[1] for r in rows.values()),
            ''.join(r[2] for r in rows.values()), ''.join(r[3] for r in rows.values()))


def own_strings(lang):
    """-> (SEP, SEPR, SEPH) for a language's own letters ('' when none)"""
    own = OWN.get(lang, {})
    return (''.join(own), ''.join(lrank(b, lv) for b, lv, h in own.values()), ''.join(h for b, lv, h in own.values()))


SRC, RANK, RANK2, HDR, GRP = build()


def ref_key(label, lang):
    """the reference fmlColl: (key, header)"""
    sep, sepr, seph = own_strings(lang)
    order = gord(lang)
    key, hdr, grp = '', '', ''
    for j, ch in enumerate(label):
        s = sep.find(ch) if sep else -1
        if s >= 0:
            key += sepr[s]
            if not hdr:
                hdr, grp = seph[s], '2'
            continue
        k = SRC.find(ch)
        if k >= 0:
            if RANK[k] == DROP:
                continue
            key += RANK[k]
            if RANK2[k] != NONE:
                key += RANK2[k]
            if not hdr:
                hdr, grp = HDR[k], GRP[k]
            continue
        code = ord(ch)
        if 0xAC00 <= code <= 0xD7A3:
            key += ch
            if not hdr:
                hdr, grp = HANGUL_HDR[(code - 0xAC00) // 588], '5'
            continue
        if 0x4E00 <= code <= 0x9FFF or 0x3400 <= code <= 0x4DBF or 0xF900 <= code <= 0xFAFF:
            key += ch
            if not hdr:
                hdr, grp = IDEO_HDR.get(lang, IDEO_DEFAULT), '7'
            continue
        if not hdr and ch == ' ':
            continue
        lc = ch.lower()
        key += lc
        if not hdr:
            if 0x30 <= code <= 0x39:
                hdr, grp = '#', '1'
            elif lc != ch.upper():
                hdr, grp = ch.upper(), '8'
            else:
                hdr, grp = '#', '0'
    if not hdr:
        hdr, grp = '#', '0'
    return order[int(grp)] + key, hdr


if __name__ == '__main__':
    print(len(SRC), 'mapped characters;', 'own letters:', {k: len(v) for k, v in OWN.items()})
    assert len(SRC) == len(RANK) == len(RANK2) == len(HDR) == len(GRP)
    assert len(set(SRC)) == len(SRC)
