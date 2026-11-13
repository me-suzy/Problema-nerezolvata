#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compara_taguri.py
=================

Gaseste tagurile <p> din fisierul RO care NU au corespondent in fisierul EN
(si invers), intre <!-- ARTICOL START --> si <!-- ARTICOL FINAL -->.

Identificatori per tag (conform specificatiilor):
    Numar   - pozitia tagului in fisier (1, 2, 3 ...)
    Litera  - A = <p class="text_obisnuit"> cu <span class="text_obisnuit2"> inauntru
              B = <p class="text_obisnuit2">
              C = <p class="text_obisnuit"> fara span
    Grecesc - alfa (< 7 cuvinte), beta (7..14 cuvinte), gamma (> 14 cuvinte)

Metoda
------
Comparatia secventiala "linie cu linie" esueaza cand doua taguri RO vecine au
aceiasi identificatori (ex. "BABA OARBA ..." si "Leadership: ..."), pentru ca
alege mereu primul tag si apoi il elimina gresit pe al doilea.

Aici se foloseste ALINIEREA GLOBALA prin programare dinamica (Needleman-Wunsch,
acelasi principiu ca Gale-Church pentru alinierea traducerilor): se cauta
alinierea RO <-> EN care MINIMIZEAZA costul total, tinand cont simultan de toate
tagurile dinainte si dupa (exact "procesul cartezian" descris in specificatii,
dar facut matematic, pe toata lista deodata, nu pe ferestre de 4 taguri).

Costul unei perechi RO-EN (mai mic = mai probabil sa fie traducere):
    * litera diferita                 -> perechea este INTERZISA
    * raport de lungime (cuvinte)     -> |ln(cuv_ro / (r * cuv_en))|, r = raportul
                                         mediu RO/EN al documentului (calculat automat)
    * semnatura de punctuatie         -> diferente la numarul de '?', '!', ':', ';',
                                         ghilimele, paranteze, propozitii
    * numere                          -> numerele care apar doar intr-o parte
    * cuvinte scrise cu MAJUSCULE     -> diferenta la numarul lor
    * cuvinte identice in ambele      -> bonus (nume proprii, "Leadership", "etc.")
Un tag lasat fara pereche costa GAP (1.0). Nimic din cod nu depinde de limba
sau de cuvinte-cheie: doar numere, structura si statistica textului.

Utilizare
---------
    python compara_taguri.py
        fara argumente: compara tot site-ul, folderele SITE_RO si SITE_EN (vezi mai jos),
        in modul --tip-flexibil, cu rezultatele in folderul "Rezultate comparatii site - tip-flexibil"
        de langa script
    python compara_taguri.py RO.html EN.html [-o DIR_OUTPUT] [--merge] [-v]
    python compara_taguri.py --ro-dir d:/3/ro --en-dir d:/3/en -o d:/3/Rezultate

In DIR_OUTPUT se scriu:
    rezultate.txt      - raportul (acelasi text ca pe ecran); fisierele cu taguri fara
                         corespondent au titlul marcat "------- PROBLEMA----------"
    aliniere.txt       - tabelul complet de aliniere RO <-> EN, cu costuri
    <nume_EN>.html     - doar cu --merge: fisierul EN in care tagurile RO fara corespondent
                         au fost inserate la locul lor (OUTPUT din "1. Specificatii")
Scriptul doar citeste fisierele RO si EN; nu le modifica si nu le copiaza.
"""

import argparse
import glob
import html as htmlmod
import math
import os
import re
import statistics
import sys
import unicodedata
from dataclasses import dataclass, field

# Folderele site-ului, folosite cand scriptul este rulat fara argumente
SITE_RO = r'E:\Carte\BB\17 - Site Leadership\Principal\ro'
SITE_EN = r'E:\Carte\BB\17 - Site Leadership\Principal\en'
SITE_OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Rezultate comparatii site - tip-flexibil')

START_MARK = '<!-- ARTICOL START -->'
END_MARK = '<!-- ARTICOL FINAL -->'

P_RE = re.compile(r'<p\s+class=["\'](text_obisnuit2?)["\'][^>]*>(.*?)</p\s*>', re.S | re.I)
SPAN_RE = re.compile(r'<span\s+class=["\']text_obisnuit2["\']', re.I)
HTML_TAG_RE = re.compile(r'<[^>]+>')
NUM_RE = re.compile(r'\d+(?:[.,:/\-]\d+)*')
CAPS_RE = re.compile(r'(?<![\w])[A-ZĂÂÎȘŞȚŢ]{2,}(?![\w])')
SENT_RE = re.compile(r'[.!?…]+(?=\s|$)')
TOKEN_RE = re.compile(r"[^\W_]+", re.U)

# Parametrii costului
GAP = 1.0          # costul unui tag ramas fara pereche
W_PUNCT = 0.25     # per unitate de diferenta la fiecare semn de punctuatie
W_NUM = 0.5        # per numar prezent doar intr-o parte
W_CAPS = 0.2       # per cuvant cu MAJUSCULE in plus/minus
W_SHARED = 0.15    # bonus per cuvant identic in ambele taguri
W_TYPE = 0.7       # (doar cu --tip-flexibil) penalizare pentru litera diferita
SUSPECT = 1.5      # perechile cu cost >= SUSPECT sunt listate ca "suspecte"
MEAN_SUSPECT = 0.6 # cost mediu pe fisier peste care EN-ul este, de regula, alt articol
PUNCT_KEYS = ('?', '!', ':', ';', '"', '(', 'propozitii')


# ----------------------------------------------------------------------------
# Extragere si identificatori
# ----------------------------------------------------------------------------

@dataclass
class Tag:
    number: int                 # pozitia originala in fisier (1-based)
    kind: str                   # A / B / C
    html: str                   # tagul complet, asa cum e in fisier
    text: str                   # textul vizibil (fara taguri HTML)
    words: int                  # numar de cuvinte (text.split())
    greek: str                  # α / β / γ
    punct: dict = field(default_factory=dict)
    numbers: tuple = ()
    caps: int = 0
    tokens: frozenset = frozenset()

    @property
    def ident(self):
        return f"{self.number}({self.kind})({self.greek})"

    @property
    def short(self):
        return f"{self.number}.{self.kind}"

    def one_line(self):
        return re.sub(r'\s*\n\s*', ' ', self.html.strip())


def greek_for(words):
    if words < 7:
        return 'α'
    if words <= 14:
        return 'β'
    return 'γ'


def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def visible_text(inner_html):
    txt = HTML_TAG_RE.sub(' ', inner_html)
    txt = htmlmod.unescape(txt)
    txt = txt.replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', txt).strip()


def tag_kind(css_class, inner_html):
    if css_class.lower() == 'text_obisnuit2':
        return 'B'
    if SPAN_RE.search(inner_html):
        return 'A'
    return 'C'


def features(text):
    norm = (text.replace('\u201c', '"').replace('\u201d', '"').replace('\u201e', '"')
                .replace('\u00ab', '"').replace('\u00bb', '"'))
    punct = {k: norm.count(k) for k in PUNCT_KEYS if k != 'propozitii'}
    punct['propozitii'] = len(SENT_RE.findall(norm))
    numbers = tuple(sorted(NUM_RE.findall(norm)))
    caps = len(CAPS_RE.findall(norm))
    toks = frozenset(strip_accents(t.lower()) for t in TOKEN_RE.findall(norm)
                     if len(t) >= 4)
    return punct, numbers, caps, toks


def extract_article(content):
    """Returneaza (inainte, articol, dupa) sau None daca lipsesc marcajele."""
    s = content.find(START_MARK)
    e = content.find(END_MARK, s + len(START_MARK) if s >= 0 else 0)
    if s < 0 or e < 0:
        return None
    s_end = s + len(START_MARK)
    return content[:s_end], content[s_end:e], content[e:]


def parse_tags(article_html):
    """Tagurile <p> din articol, numerotate dupa pozitia in fisier.
       Tagurile fara text vizibil (ex. <p class="text_obisnuit"></p>) sunt
       sarite, dar pastreaza numerotarea celorlalte."""
    tags = []
    for n, m in enumerate(P_RE.finditer(article_html), start=1):
        css, inner = m.group(1), m.group(2)
        text = visible_text(inner)
        if not text:
            continue
        words = len(text.split())
        punct, numbers, caps, toks = features(text)
        tags.append(Tag(number=n, kind=tag_kind(css, inner), html=m.group(0),
                        text=text, words=words, greek=greek_for(words),
                        punct=punct, numbers=numbers, caps=caps, tokens=toks))
    return tags


# ----------------------------------------------------------------------------
# Aliniere (programare dinamica)
# ----------------------------------------------------------------------------

def pair_cost(a, b, ratio):
    """Costul ca tagul RO `a` sa fie traducerea tagului EN `b` (acelasi tip)."""
    len_cost = abs(math.log((a.words + 1) / (ratio * (b.words + 1))))
    punct_cost = sum(min(abs(a.punct[k] - b.punct[k]), 3) * W_PUNCT
                     for k in PUNCT_KEYS)
    num_cost = len(set(a.numbers) ^ set(b.numbers)) * W_NUM
    caps_cost = min(abs(a.caps - b.caps), 4) * W_CAPS
    bonus = min(len(a.tokens & b.tokens), 4) * W_SHARED
    return max(0.0, len_cost + punct_cost + num_cost + caps_cost - bonus)


def align_once(ro, en, ratio, flexible=False):
    """Needleman-Wunsch. Returneaza lista de operatii:
       ('M', i, j, cost)   tag RO i <-> tag EN j
       ('R', i, None, GAP) tag RO i fara corespondent (TAG WRONG)
       ('E', None, j, GAP) tag EN j fara corespondent
       flexible=False: litera (A/B/C) trebuie sa coincida (specificatii).
       flexible=True : litera diferita este doar penalizata cu W_TYPE, astfel
                       incat acelasi paragraf cu alta clasa CSS sa fie totusi
                       imperecheat (si raportat ca "clasa diferita").
    """
    n, m = len(ro), len(en)
    INF = float('inf')
    D = [[INF] * (m + 1) for _ in range(n + 1)]
    B = [[None] * (m + 1) for _ in range(n + 1)]
    D[0][0] = 0.0
    for i in range(n + 1):
        for j in range(m + 1):
            if i == 0 and j == 0:
                continue
            best, op = INF, None
            if i > 0 and j > 0:
                same = ro[i - 1].kind == en[j - 1].kind
                if same or flexible:
                    c = D[i - 1][j - 1] + pair_cost(ro[i - 1], en[j - 1], ratio) \
                        + (0.0 if same else W_TYPE)
                    if c < best:
                        best, op = c, 'M'
            if i > 0:
                c = D[i - 1][j] + GAP
                if c < best:
                    best, op = c, 'R'
            if j > 0:
                c = D[i][j - 1] + GAP
                if c < best:
                    best, op = c, 'E'
            D[i][j], B[i][j] = best, op
    ops = []
    i, j = n, m
    while i > 0 or j > 0:
        op = B[i][j]
        if op == 'M':
            ops.append(('M', i - 1, j - 1, D[i][j] - D[i - 1][j - 1]))
            i, j = i - 1, j - 1
        elif op == 'R':
            ops.append(('R', i - 1, None, GAP))
            i -= 1
        else:
            ops.append(('E', None, j - 1, GAP))
            j -= 1
    ops.reverse()
    return ops, D[n][m]


REORDER_MAX = 0.20     # scor maxim (cost + REORDER_W_DIST * distanta) pentru "alta ordine"
REORDER_DIST = 5       # distanta maxima (in pozitii) pentru un paragraf mutat
REORDER_W_DIST = 0.05  # penalizare per pozitie de distanta


def pair_leftovers(ro, en, ops, ratio, flexible):
    """Trecere finala: tagurile ramase fara pereche (R si E) sunt comparate
       intre ele si in afara ordinii. O pereche cu cost foarte mic SI pozitii
       apropiate este acelasi paragraf mutat -> ('X', i, j, cost), nu WRONG.
       (Masurat pe site, pe 11 perechi verificate manual: scorul
       cost + 0.05*distanta este <= 0.2 pentru reordonarile reale si > 0.2
       pentru paragrafele fara legatura dar de lungime apropiata. Regula este
       intentionat conservatoare: o reordonare ratata ramane vizibila ca
       WRONG + "doar in EN", pe cand o pereche falsa ar ascunde un WRONG.)"""
    r_idx = [i for op, i, j, _ in ops if op == 'R']
    e_idx = [j for op, i, j, _ in ops if op == 'E']
    if not r_idx or not e_idx:
        return ops
    cands = []
    for i in r_idx:
        for j in e_idx:
            same = ro[i].kind == en[j].kind
            if not (same or flexible):
                continue
            dist = abs(ro[i].number - en[j].number)
            if dist > REORDER_DIST:
                continue
            c = pair_cost(ro[i], en[j], ratio) + (0.0 if same else W_TYPE)
            score = c + REORDER_W_DIST * dist
            if score <= REORDER_MAX:
                cands.append((score, c, i, j))
    cands.sort()
    used_r, used_e, moved = set(), set(), {}
    for _, c, i, j in cands:
        if i in used_r or j in used_e:
            continue
        used_r.add(i); used_e.add(j); moved[i] = (j, c)
    if not moved:
        return ops
    new_ops = []
    for op, i, j, c in ops:
        if op == 'R' and i in moved:
            new_ops.append(('X', i, moved[i][0], moved[i][1]))
        elif op == 'E' and j in used_e:
            continue          # tagul EN e acum pereche a unui tag RO mutat
        else:
            new_ops.append((op, i, j, c))
    return new_ops


def align(ro, en, flexible=False):
    """Doua treceri: prima cu raport 1.0, a doua cu raportul RO/EN real
       (mediana perechilor gasite), ca sa nu depinda de stilul traducerii.
       La final, tagurile ramase sunt imperecheate si in afara ordinii ('X')."""
    ops, total = align_once(ro, en, 1.0, flexible)
    pairs = [(ro[i].words + 1) / (en[j].words + 1) for op, i, j, _ in ops if op == 'M']
    ratio = statistics.median(pairs) if pairs else 1.0
    ratio = min(max(ratio, 0.5), 2.0)
    if abs(ratio - 1.0) > 1e-9:
        ops, total = align_once(ro, en, ratio, flexible)
    ops = pair_leftovers(ro, en, ops, ratio, flexible)
    return ops, total, ratio


# ----------------------------------------------------------------------------
# Raportare
# ----------------------------------------------------------------------------

def count_kinds(tags):
    c = {'A': 0, 'B': 0, 'C': 0}
    for t in tags:
        c[t.kind] += 1
    return c


def plural(n, kind):
    return f"{n} {'tag' if n == 1 else 'taguri'} de tipul ({kind})"


def build_report(ro_name, ro, en, ops, verbose=False, warning=None):
    ro_counts, en_counts = count_kinds(ro), count_kinds(en)
    wrong = [ro[i] for op, i, j, _ in ops if op == 'R']
    en_only = [en[j] for op, i, j, _ in ops if op == 'E']
    lines = []
    lines.append(file_header(ro_name, bool(wrong or en_only or warning)))
    if warning:
        lines.append("")
        lines.append(f"ATENȚIE: {warning}")
    if verbose:
        lines.append("")
        lines.append("Identificatori RO:")
        lines += [f"  {t.ident} {t.words} cuv.  {t.text[:70]}" for t in ro]
        lines.append("Identificatori EN:")
        lines += [f"  {t.ident} {t.words} cuv.  {t.text[:70]}" for t in en]
    lines.append("")
    lines.append("Statistici:")
    lines.append("")
    lines.append(f"Tag-uri în RO: {ro_counts}")
    lines.append(f"Tag-uri în EN: {en_counts}")
    for k in 'ABC':
        lines.append(f"Diferența pentru tag-uri de tip {k}: {ro_counts[k] - en_counts[k]}")
    pair_costs = [c for op, i, j, c in ops if op in ('M', 'X')]
    if pair_costs:
        lines.append(f"Cost mediu al perechilor RO-EN: {sum(pair_costs) / len(pair_costs):.2f} "
                     f"({len(pair_costs)} perechi; peste {MEAN_SUSPECT} înseamnă, de regulă, alt text)")
    lines.append("")
    wc = count_kinds(wrong)
    parts = [plural(wc[k], k) for k in 'ABC' if wc[k]]
    if parts:
        lines.append("În RO există în plus față de EN următoarele: " + " și ".join(parts))
    else:
        lines.append("În RO nu există taguri în plus față de EN.")
    lines.append("")
    lines.append("Tag-uri care nu au corespondent în EN (WRONG TAGS):")
    lines.append("")
    for t in wrong:
        lines.append(f"{t.short} {t.one_line()}")
    if not wrong:
        lines.append("(niciunul)")
    if en_only:
        lines.append("")
        lines.append("Tag-uri din EN care nu au corespondent în RO:")
        lines.append("")
        for t in en_only:
            lines.append(f"{t.short} {t.one_line()}")
    moved = [(ro[i], en[j], c) for op, i, j, c in ops if op == 'X']
    if moved:
        lines.append("")
        lines.append("Perechi în altă ordine (paragraful există în EN, dar pe altă poziție):")
        lines.append("")
        for a, b, c in moved:
            lines.append(f"RO {a.short} <-> EN {b.short} cost={c:.2f} | {a.text[:60]} ~ {b.text[:60]}")
    diff_kind = [(ro[i], en[j]) for op, i, j, _ in ops if op in ('M', 'X') and ro[i].kind != en[j].kind]
    if diff_kind:
        lines.append("")
        lines.append("Perechi cu clasă diferită (aceeași traducere, dar litera A/B/C diferă):")
        lines.append("")
        for a, b in diff_kind:
            lines.append(f"RO {a.short} <-> EN {b.short} | {a.text[:60]} ~ {b.text[:60]}")
    suspect = [(ro[i], en[j], c) for op, i, j, c in ops if op == 'M' and c >= SUSPECT]
    if suspect:
        lines.append("")
        lines.append(f"Perechi suspecte (cost >= {SUSPECT}; de verificat manual):")
        lines.append("")
        for a, b, c in suspect:
            lines.append(f"RO {a.short} ({a.words} cuv.) <-> EN {b.short} ({b.words} cuv.) cost={c:.2f} "
                         f"| {a.text[:50]} ~ {b.text[:50]}")
    return "\n".join(lines), wrong, en_only


def file_header(ro_name, problem):
    """Linia de titlu a unui fisier in rapoarte; fisierele cu taguri fara corespondent
       (in RO sau in EN) sau cu link EN gresit primesc marcajul PROBLEMA, ca sa fie usor de gasit."""
    return f"---------Fișier: {ro_name}" + (" ------- PROBLEMA----------" if problem else "")


def build_alignment_table(ro_name, ro, en, ops, ratio, total):
    lines = [file_header(ro_name, any(op in ('R', 'E') for op, *_ in ops)),
             f"raport mediu cuvinte RO/EN = {ratio:.3f}   cost total = {total:.3f}",
             ""]
    for op, i, j, cost in ops:
        if op in ('M', 'X'):
            a, b = ro[i], en[j]
            label = 'match  ' if op == 'M' else 'mutat  '
            lines.append(f"RO {a.ident:<10} {a.words:>4} cuv. | EN {b.ident:<10} {b.words:>4} cuv. "
                         f"| {label} cost={cost:.3f} | {a.text[:40]!r} ~ {b.text[:40]!r}")
        elif op == 'R':
            a = ro[i]
            lines.append(f"RO {a.ident:<10} {a.words:>4} cuv. | {'---':<22} "
                         f"| TAG WRONG (în plus în RO)   | {a.text[:60]!r}")
        else:
            b = en[j]
            lines.append(f"{'---':<22} | EN {b.ident:<10} {b.words:>4} cuv. "
                         f"| doar în EN                  | {b.text[:60]!r}")
    return "\n".join(lines)


def build_merged(en_content, ro, en, ops):
    """Fisierul EN cu tagurile RO fara corespondent inserate la locul lor."""
    before, article, after = extract_article(en_content)
    indent_m = re.search(r'\n([ \t]*)<p\s', article)
    indent = indent_m.group(1) if indent_m else '\t\t'
    body = []
    for op, i, j, _ in ops:
        if op == 'M' or op == 'E':
            body.append(en[j].html.strip())
        elif op == 'X':
            body.append(en[j].html.strip())   # paragraf mutat: se pune traducerea EN la pozitia din RO
        else:
            body.append(ro[i].html.strip())
    new_article = "\n\n" + "\n".join(indent + h for h in body) + "\n\n   "
    return before + new_article + after


# ----------------------------------------------------------------------------
# Fisiere
# ----------------------------------------------------------------------------

def read(path):
    """Citeste UTF-8 (cu sau fara BOM); daca fisierul nu e UTF-8 valid,
       cade pe Windows-1252 (fisiere vechi), apoi pe Latin-1."""
    with open(path, 'rb') as f:
        raw = f.read()
    for enc in ('utf-8-sig', 'cp1252', 'latin-1'):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode('utf-8', errors='replace')


def compare_files(ro_path, en_path, out_dir=None, merge=True, verbose=False, append=False,
                  flexible=False):
    ro_content, en_content = read(ro_path), read(en_path)
    ro_parts, en_parts = extract_article(ro_content), extract_article(en_content)
    if ro_parts is None or en_parts is None:
        msg = (f"---------Fișier: {os.path.basename(ro_path)}\nLipsesc marcajele ARTICOL START/FINAL "
               f"({'RO' if ro_parts is None else 'EN'}).")
        print(msg)
        return None
    ro, en = parse_tags(ro_parts[1]), parse_tags(en_parts[1])
    ops, total, ratio = align(ro, en, flexible)
    warning = None
    back = extract_ro_filename(en_content)
    if back and back != os.path.basename(ro_path):
        warning = (f"fișierul EN trimite înapoi (steagul RO) la {back}, nu la acest fișier; "
                   f"este probabil traducerea altui articol, iar comparația de mai jos nu are sens.")
    report, wrong, en_only = build_report(os.path.basename(ro_path), ro, en, ops, verbose, warning)
    table = build_alignment_table(os.path.basename(ro_path), ro, en, ops, ratio, total)
    print(report)
    print()
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        mode = 'a' if append else 'w'
        with open(os.path.join(out_dir, 'rezultate.txt'), mode, encoding='utf-8') as f:
            f.write(report + "\n\n")
        with open(os.path.join(out_dir, 'aliniere.txt'), mode, encoding='utf-8') as f:
            f.write(table + "\n\n")
        if merge:
            merged = build_merged(en_content, ro, en, ops)
            with open(os.path.join(out_dir, os.path.basename(en_path)), 'w', encoding='utf-8') as f:
                f.write(merged)
    return {'ro': ro, 'en': en, 'ops': ops, 'wrong': wrong, 'en_only': en_only,
            'ratio': ratio, 'report': report, 'table': table}


def extract_en_filename(ro_content):
    """Numele fisierului EN din sectiunea FLAGS (href=".../en/xxx.html")."""
    flags = re.search(r'<!-- FLAGS[_\d]* -->(.*?)<!-- FLAGS -->', ro_content, re.S)
    hay = flags.group(1) if flags else ro_content
    m = re.search(r'href="https?://[^"]*/en/([^"/]+\.html?)"', hay)
    return m.group(1) if m else None


def extract_ro_filename(en_content):
    """Numele fisierului RO spre care trimite steagul RO din sectiunea FLAGS a fisierului EN
       (<a href="https://site/xxx.html"><img ... flag_lang_ro ...>)."""
    flags = re.search(r'<!-- FLAGS[_\d]* -->(.*?)<!-- FLAGS -->', en_content, re.S)
    hay = flags.group(1) if flags else en_content
    m = re.search(r'href="https?://[^"/]+/([^"/]+\.html?)"[^>]*>\s*<img[^>]*flag_lang_ro', hay)
    return m.group(1) if m else None


def find_pairs(ro_dir, en_dir):
    """Perechile RO-EN din folderul RO. Fisierul EN se ia din steagul EN al fisierului RO.
       Daca steagul RO din fisierul EN trimite la ALT fisier RO, EN-ul este traducerea altui
       articol (link copiat gresit): perechea ajunge in `mismatched` si nu se compara."""
    pairs, missing, mismatched = [], [], []
    for ro_file in sorted(glob.glob(os.path.join(ro_dir, '*.htm*'))):
        en_name = extract_en_filename(read(ro_file)) or os.path.basename(ro_file)
        en_file = os.path.join(en_dir, en_name)
        if not os.path.exists(en_file):
            missing.append((ro_file, en_name))
            continue
        back = extract_ro_filename(read(en_file))
        if back and back != os.path.basename(ro_file):
            mismatched.append((ro_file, en_name, back))
        else:
            pairs.append((ro_file, en_file))
    return pairs, missing, mismatched


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('ro', nargs='?', help='fisierul RO')
    ap.add_argument('en', nargs='?', help='fisierul EN')
    ap.add_argument('--ro-dir', help='folder cu fisiere RO (mod batch)')
    ap.add_argument('--en-dir', help='folder cu fisiere EN (mod batch)')
    ap.add_argument('-o', '--output-dir', help='folder de output (rezultate.txt, aliniere.txt, html combinat)')
    ap.add_argument('--merge', action='store_true',
                    help='scrie si fisierul EN combinat (EN + tagurile RO lipsa, la locul lor); implicit nu')
    ap.add_argument('-v', '--verbose', action='store_true', help='afiseaza identificatorii fiecarui tag')
    ap.add_argument('--tip-flexibil', action='store_true',
                    help='litera A/B/C diferita nu mai interzice perechea, doar o penalizeaza; '
                         'perechile cu clasa diferita sunt raportate separat')
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    if not any((args.ro, args.en, args.ro_dir, args.en_dir)):
        # fara argumente: tot site-ul, in modul flexibil
        if not (os.path.isdir(SITE_RO) and os.path.isdir(SITE_EN)):
            ap.error(f'nu gasesc folderele site-ului:\n  {SITE_RO}\n  {SITE_EN}\n'
                     f'(schimba SITE_RO / SITE_EN la inceputul scriptului sau da --ro-dir si --en-dir)')
        args.ro_dir, args.en_dir, args.tip_flexibil = SITE_RO, SITE_EN, True
        args.output_dir = args.output_dir or SITE_OUT
        print(f"Rulare fara argumente: compar tot site-ul (--tip-flexibil)\n"
              f"  RO: {SITE_RO}\n  EN: {SITE_EN}\n  rezultate in: {args.output_dir}\n")

    if args.ro_dir and args.en_dir:
        pairs, missing, mismatched = find_pairs(args.ro_dir, args.en_dir)
        print(f"Am găsit {len(pairs)} perechi RO-EN; {len(missing)} fișiere RO fără pereche EN; "
              f"{len(mismatched)} fișiere RO al căror link EN duce la traducerea altui articol.\n")
        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)
            for name in ('rezultate.txt', 'aliniere.txt'):
                open(os.path.join(args.output_dir, name), 'w', encoding='utf-8').close()
        total_wrong, errors = 0, []
        for ro_file, en_file in pairs:
            try:
                r = compare_files(ro_file, en_file, args.output_dir, args.merge, args.verbose,
                                  append=True, flexible=args.tip_flexibil)
            except Exception as exc:  # un fisier stricat nu opreste tot batch-ul
                errors.append((ro_file, repr(exc)))
                print(f"---------Fișier: {os.path.basename(ro_file)}\nEROARE: {exc!r}\n")
                continue
            if r:
                total_wrong += len(r['wrong'])
        if errors and args.output_dir:
            with open(os.path.join(args.output_dir, 'erori.txt'), 'w', encoding='utf-8') as f:
                f.write("\n".join(f"{p}\t{e}" for p, e in errors) + "\n")
        print(f"Fișiere cu erori: {len(errors)}")
        for ro_file, en_name in missing:
            print(f"---------Fișier: {os.path.basename(ro_file)}\nNu există fișierul EN: {en_name}\n")
        if mismatched:
            lines = ["Fișiere RO al căror link EN (steagul EN) duce la traducerea ALTUI articol "
                     "(steagul RO din fișierul EN trimite în altă parte). Aceste articole RO nu au "
                     "traducere și nu au fost comparate:", ""]
            for ro_file, en_name, back in mismatched:
                exists = os.path.exists(os.path.join(args.ro_dir, back))
                lines.append(f"{os.path.basename(ro_file)}  ->  en/{en_name}  (care este traducerea lui "
                             f"ro/{back}{'' if exists else ' - fișier RO inexistent'})")
            block = "\n".join(lines)
            print(block + "\n")
            if args.output_dir:
                with open(os.path.join(args.output_dir, 'rezultate.txt'), 'a', encoding='utf-8') as f:
                    f.write(block + "\n")
        print(f"Fișiere RO cu link EN greșit (traducerea altui articol): {len(mismatched)}")
        print(f"TOTAL taguri RO fără corespondent în EN: {total_wrong}")
        return 0

    if not (args.ro and args.en):
        ap.error('dă fie RO.html EN.html, fie --ro-dir și --en-dir')
    compare_files(args.ro, args.en, args.output_dir, args.merge, args.verbose,
                  flexible=args.tip_flexibil)
    return 0


if __name__ == '__main__':
    sys.exit(main())
