# -*- coding: utf-8 -*-
r"""
caz-nou.py  -  clauze noi peste compara_taguri.py
==================================================

Ce face
-------
Refoloseste alinierea globala din compara_taguri.py (programare dinamica, cost minim pe tot
articolul) si ADAUGA la costul unei perechi RO-EN noua clauze care privesc ALFABETUL, LIMBA,
NUMERELE, LINK-URILE, NUMELE PROPRII si "GUNOIUL" inserat in text. Pe langa cost, fiecare tag
primeste OBSERVATII (ce clauza l-a atins), tiparite intr-o sectiune noua a raportului.

Nimic nu depinde de cuvinte-cheie: toate clauzele numara caractere, categorii Unicode,
repetitii si potriviri intre cele doua texte.

Clauzele (constantele W_* sunt mai jos, se pot ajusta)
-------------------------------------------------------
 1. ALFABET      - literele fiecarui tag sunt numarate pe alfabete (latin, chirilic, grec, arab,
                   ebraic, CJK). Alfabet dominant diferit intre RO si EN => perechea aproape
                   interzisa (W_SCRIPT). Litere "straine" strecurate intr-un text latin (de ex. un
                   "е" chirilic in "Lеadership") => observatie + penalizare pe diferenta (W_FOREIGN).
 2. DIACRITICE   - numarul de a/i/s/t romanesti (ăâîșț, si variantele cu sedila). Un tag EN cu
                   diacritice romanesti = paragraf ramas netradus; un tag RO lung fara nicio
                   diacritica = probabil text in alta limba. Doar observatii, fara cost.
 3. IDENTIC      - daca RO si EN au >= 80% cuvinte identice, "traducerea" este de fapt acelasi
                   text (netradus). Observatie pe pereche.
 4. NUMERE       - numerele se NORMALIZEAZA inainte de comparare: 2.000 = 2,000 = 2000,
                   3:20 = 3: 20, al XVI-lea = 16th (cifre romane -> arabe). Daca dupa normalizare
                   numerele coincid, penalizarea pe numere a scriptului de baza este returnata.
 5. LINK-URI     - URL-uri si adrese de e-mail trebuie sa fie identice in RO si EN; fiecare link
                   prezent intr-o singura parte costa W_URL si da observatie.
 6. NUME PROPRII - cuvintele cu majuscula care nu sunt la inceput de propozitie (nume) ar trebui
                   sa apara in ambele texte; fiecare nume prezent intr-o singura parte costa W_NAME.
 7. REPETITII    - aceeasi pereche de cuvinte consecutive de >= 3 ori ("BABA OARBA" x6) sau acelasi
                   cuvant cu MAJUSCULE de >= 3 ori, intr-un paragraf de sub 80 de cuvinte, sau siruri
                   de simboluri ("+++", "***", "-----") = text inserat/gunoi. Observatie +
                   penalizare pe diferenta (W_REPEAT, W_MARKER).
 8. DIALOG       - un paragraf care incepe cu linie de dialog sau ghilimele ar trebui sa inceapa la
                   fel si in traducere (W_DIALOG).
 9. SIMBOLURI    - emoji, stelute, sageti si alte simboluri (categoria Unicode "So") se pastreaza
                   in traducere; diferenta costa W_SYMBOL.

Utilizare
---------
    python caz-nou.py                       -> ruleaza cazul de test construit in script (sectiunea
                                               CAZ DEMO) si verifica rezultatul asteptat
    python caz-nou.py RO.html EN.html       -> compara doua fisiere cu clauzele noi
    optiuni: --tip-flexibil (ca in compara_taguri.py), -o DIR (implicit "Rezultate caz-nou")

Rapoartele se scriu in "Rezultate caz-nou\rezultate.txt" si "...\aliniere.txt".
"""

import argparse
import os
import re
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import compara_taguri as ct  # noqa: E402  (alinierea, parsarea si raportul de baza)

OUT_DEFAULT = os.path.join(HERE, 'Rezultate caz-nou')

# ----------------------------------------------------------------------------
# Greutatile clauzelor noi
# ----------------------------------------------------------------------------
W_SCRIPT = 1.5    # alfabet dominant diferit (practic interzice perechea)
W_FOREIGN = 0.10  # per litera din alt alfabet strecurata in text (diferenta RO-EN), max 1.0
W_URL = 0.60      # per URL / e-mail prezent intr-o singura parte
W_NAME = 0.15     # per nume propriu prezent intr-o singura parte, max 0.6
W_REPEAT = 0.15   # per cuvant repetat anormal (diferenta RO-EN), max 0.9; mic, fiindca scriptul de
                  # baza penalizeaza deja MAJUSCULELE si lungimea in plus ale textului inserat
W_MARKER = 0.15   # per sir de simboluri ("+++", "***") prezent intr-o singura parte
W_DIALOG = 0.25   # paragraf de dialog intr-o parte, narativ in cealalta
W_SYMBOL = 0.20   # per simbol/emoji diferit, max 0.6
IDENTIC = 0.80    # prag de cuvinte identice peste care RO si EN sunt "acelasi text"

# ----------------------------------------------------------------------------
# Clauza 1: alfabete
# ----------------------------------------------------------------------------
SCRIPTS = {
    'latin':    re.compile(r'[A-Za-zÀ-ɏḀ-ỿ]'),
    'chirilic': re.compile(r'[Ѐ-ӿ]'),
    'grec':     re.compile(r'[Ͱ-Ͽἀ-῿]'),
    'arab':     re.compile(r'[؀-ۿ]'),
    'ebraic':   re.compile(r'[֐-׿]'),
    'CJK':      re.compile(r'[぀-ヿ一-鿿가-힯]'),
}
# Clauza 2: diacritice romanesti (inclusiv variantele vechi cu sedila)
DIACRITICE_RE = re.compile(r'[ăâîșțşţĂÂÎȘȚŞŢ]')
# Clauza 5: link-uri
URL_RE = re.compile(r'https?://\S+|www\.\S+|[\w.+-]+@[\w-]+\.[\w.]+')
# Clauza 6: nume proprii = cuvant cu majuscula + litere mici, precedat de un cuvant cu litere mici
# (deci nu la inceput de propozitie, nu dupa ":", "—", ghilimele sau simboluri)
NAME_RE = re.compile(r'(?<=[a-zăâîșțşţ,;)] )([A-ZĂÂÎȘȚŞŢ][a-zăâîșțşţ]{2,})\b')
# Clauza 7: siruri de simboluri (acelasi caracter non-alfanumeric repetat de 3+ ori)
MARKER_RE = re.compile(r'([^\w\s])\1{2,}')
# Clauza 4: cifre romane (>= 2 litere, ca sa nu prindem pronumele englez "I")
ROMAN_RE = re.compile(r'\b(?=[MDCLXVI]{2,}\b)M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})\b')
ROMAN_VAL = {'I': 1, 'V': 5, 'X': 10, 'L': 50, 'C': 100, 'D': 500, 'M': 1000}


def roman_to_int(s):
    total = 0
    for i, ch in enumerate(s):
        v = ROMAN_VAL[ch]
        total += -v if i + 1 < len(s) and ROMAN_VAL[s[i + 1]] > v else v
    return total


def normalized_numbers(text):
    """Multimea numerelor din text, normalizate: fara separatori de mii, descompuse pe
       componente (3:20 -> 3, 20), cifrele romane transformate in arabe."""
    out = set()
    for raw in ct.NUM_RE.findall(text):
        if re.fullmatch(r'\d{1,3}([.,]\d{3})+', raw):     # 2.000 / 2,000 -> 2000
            raw = re.sub(r'[.,]', '', raw)
        out.update(p.lstrip('0') or '0' for p in re.split(r'\D+', raw) if p)
    for m in ROMAN_RE.finditer(text):
        if m.group(0):
            out.add(str(roman_to_int(m.group(0))))
    return out


def script_counts(text):
    return {name: len(rx.findall(text)) for name, rx in SCRIPTS.items()}


def extra_features(tag):
    """Trasaturile noi ale unui tag (calculate o singura data, pastrate pe obiect)."""
    if hasattr(tag, '_nou'):
        return tag._nou
    t = tag.text
    sc = script_counts(t)
    total_letters = sum(sc.values()) or 1
    dominant = max(sc, key=sc.get) if total_letters > 1 else 'latin'
    foreign = total_letters - sc[dominant]              # litere din alte alfabete decat cel dominant
    # repetitii anormale: aceeasi PERECHE de cuvinte consecutive de >= 3 ori ("baba oarba" x6,
    # "strutul imens" x3) sau acelasi cuvant cu MAJUSCULE de >= 3 ori. Un singur cuvant obisnuit
    # repetat ("este", "pentru", "your") este normal intr-un paragraf si nu se numara.
    # Perechile se numara doar daca ambele cuvinte au >= 4 litere ("pentru ca", "if you",
    # "services and" sunt perechi normale de cuvinte de legatura).
    toks = ct.TOKEN_RE.findall(t)
    freq = {}
    for w1, w2 in zip(toks, toks[1:]):
        if len(w1) >= 4 and len(w2) >= 4:
            k = ct.strip_accents(f"{w1} {w2}".lower())
            freq[k] = freq.get(k, 0) + 1
    repeated = {w: n for w, n in freq.items() if n >= 3}
    for w in toks:
        if len(w) >= 3 and w.isupper() and not any(w.lower() in k.split() for k in repeated):
            freq[w] = freq.get(w, 0) + 1
    repeated = sorted((w, n) for w, n in freq.items() if n >= 3 and tag.words < 80)
    f = {
        'scripts': sc, 'dominant': dominant, 'foreign': foreign,
        'diacritice': len(DIACRITICE_RE.findall(t)),
        'numere': normalized_numbers(t),
        'urls': set(u.rstrip('.,;') for u in URL_RE.findall(t)),
        'nume': set(ct.strip_accents(n.lower()) for n in NAME_RE.findall(t)),
        'repetate': repeated,
        # markerele se cauta fara simboluri/emoji (acelea sunt numarate la clauza 9)
        'markere': set(m.group(0)[0] * 3 for m in MARKER_RE.finditer(
            ''.join(c for c in t if unicodedata.category(c) != 'So'))),
        'dialog': bool(re.match(r'^\s*[-–—"„«“]', t)),
        'simboluri': sum(1 for c in t if unicodedata.category(c) == 'So'),
        'cuvinte_norm': frozenset(ct.strip_accents(w.lower()) for w in ct.TOKEN_RE.findall(t)
                                  if len(w) >= 3),
    }
    tag._nou = f
    return f


def tag_observations(tag, lang):
    """Observatii pe un singur tag (lang = 'RO' sau 'EN')."""
    f = extra_features(tag)
    obs = []
    if f['dominant'] != 'latin':
        obs.append(f"alfabet {f['dominant']} ({f['scripts'][f['dominant']]} litere)")
    elif f['foreign']:
        altele = ", ".join(f"{k} {v}" for k, v in f['scripts'].items() if v and k != 'latin')
        obs.append(f"{f['foreign']} litere din alt alfabet strecurate in text latin ({altele})")
    if lang == 'EN' and f['diacritice'] >= 2:
        obs.append(f"{f['diacritice']} diacritice romanesti in EN (paragraf netradus?)")
    if lang == 'RO' and tag.words >= 15 and f['diacritice'] == 0 and f['dominant'] == 'latin':
        obs.append("RO fara nicio diacritica (text in alta limba?)")
    for w, n in f['repetate']:
        obs.append(f"cuvantul '{w}' apare {n} ori (text inserat?)")
    if f['markere']:
        obs.append("siruri de simboluri inserate: " + " ".join(sorted(f['markere'])))
    if f['simboluri']:
        obs.append(f"{f['simboluri']} simboluri/emoji")
    return obs


def pair_extra(a, b):
    """Costul suplimentar al perechii RO `a` - EN `b` si observatiile pe pereche.
       Returneaza (cost_extra, [(clauza, cost, detaliu), ...])."""
    fa, fb = extra_features(a), extra_features(b)
    items = []
    if fa['dominant'] != fb['dominant']:
        items.append(('alfabet', W_SCRIPT, f"{fa['dominant']} vs {fb['dominant']}"))
    d = abs(fa['foreign'] - fb['foreign'])
    if d:
        items.append(('litere straine', min(d * W_FOREIGN, 1.0), f"{fa['foreign']} vs {fb['foreign']}"))
    # numere: scriptul de baza a penalizat diferentele brute; dupa normalizare returnam ce a fost nedrept
    raw_diff = len(set(a.numbers) ^ set(b.numbers))
    norm_diff = len(fa['numere'] ^ fb['numere'])
    if norm_diff != raw_diff:
        items.append(('numere normalizate', (norm_diff - raw_diff) * ct.W_NUM,
                      f"brut {raw_diff} diferente, normalizat {norm_diff}"))
    only = fa['urls'] ^ fb['urls']
    if only:
        items.append(('link-uri', len(only) * W_URL, " ".join(sorted(only))))
    names = fa['nume'] ^ fb['nume']
    if names:
        items.append(('nume proprii', min(len(names) * W_NAME, 0.6), " ".join(sorted(names))))
    d = abs(len(fa['repetate']) - len(fb['repetate']))
    if d:
        items.append(('repetitii', min(d * W_REPEAT, 0.9), f"{len(fa['repetate'])} vs {len(fb['repetate'])} cuvinte repetate"))
    mk = fa['markere'] ^ fb['markere']
    if mk:
        items.append(('markere', len(mk) * W_MARKER, " ".join(sorted(mk))))
    if fa['dialog'] != fb['dialog']:
        items.append(('dialog', W_DIALOG, f"RO {'dialog' if fa['dialog'] else 'narativ'}, EN {'dialog' if fb['dialog'] else 'narativ'}"))
    d = abs(fa['simboluri'] - fb['simboluri'])
    if d:
        items.append(('simboluri', min(d * W_SYMBOL, 0.6), f"{fa['simboluri']} vs {fb['simboluri']}"))
    common = fa['cuvinte_norm'] & fb['cuvinte_norm']
    smaller = min(len(fa['cuvinte_norm']), len(fb['cuvinte_norm'])) or 1
    if len(common) / smaller >= IDENTIC and smaller >= 4:
        items.append(('identic', 0.0, f"{len(common)}/{smaller} cuvinte identice: EN = RO, netradus"))
    return sum(c for _, c, _ in items), items


_base_pair_cost = ct.pair_cost


def pair_cost_nou(a, b, ratio):
    """Costul de baza (tip, lungime, punctuatie, numere, MAJUSCULE, cuvinte comune) + clauzele noi."""
    extra, _ = pair_extra(a, b)
    return max(0.0, _base_pair_cost(a, b, ratio) + extra)


ct.pair_cost = pair_cost_nou   # alinierea din compara_taguri foloseste de acum costul nou


# ----------------------------------------------------------------------------
# Raport
# ----------------------------------------------------------------------------

def build_extra_report(ro, en, ops):
    lines = ["", "Observații (clauze noi) pe taguri:", ""]
    found = False
    for lang, tags in (('RO', ro), ('EN', en)):
        for t in tags:
            obs = tag_observations(t, lang)
            if obs:
                found = True
                lines.append(f"{lang} {t.short} ({t.words} cuv.) | {t.text[:45]!r}")
                lines += [f"      - {o}" for o in obs]
    if not found:
        lines.append("(niciuna)")
    lines += ["", "Clauze noi active pe perechi (cost suplimentar fata de scriptul de baza):", ""]
    found = False
    for op, i, j, cost in ops:
        if op not in ('M', 'X'):
            continue
        extra, items = pair_extra(ro[i], en[j])
        if items:
            found = True
            lines.append(f"RO {ro[i].short} <-> EN {en[j].short}  cost total={cost:.2f}  din care clauze noi={extra:+.2f}")
            lines += [f"      - {name}: {c:+.2f}  ({det})" for name, c, det in items]
    if not found:
        lines.append("(niciuna)")
    return "\n".join(lines)


def compare(ro_path, en_path, out_dir, flexible=False, verbose=False, append=False):
    ro_c, en_c = ct.read(ro_path), ct.read(en_path)
    ro = ct.parse_tags(ct.extract_article(ro_c)[1])
    en = ct.parse_tags(ct.extract_article(en_c)[1])
    ops, total, ratio = ct.align(ro, en, flexible)
    report, wrong, en_only = ct.build_report(os.path.basename(ro_path), ro, en, ops, verbose)
    report += "\n" + build_extra_report(ro, en, ops)
    table = ct.build_alignment_table(os.path.basename(ro_path), ro, en, ops, ratio, total)
    print(report + "\n")
    os.makedirs(out_dir, exist_ok=True)
    mode = 'a' if append else 'w'
    with open(os.path.join(out_dir, 'rezultate.txt'), mode, encoding='utf-8') as f:
        f.write(report + "\n\n")
    with open(os.path.join(out_dir, 'aliniere.txt'), mode, encoding='utf-8') as f:
        f.write(table + "\n\n")
    return ro, en, ops, wrong, en_only


# ----------------------------------------------------------------------------
# CAZ DEMO: doua articole construite ca sa atinga fiecare clauza
# ----------------------------------------------------------------------------
# Numerotarea tagurilor = pozitia in fisier (RO are 12 taguri, EN are 12). Ce trebuie sa iasa:
#   RO 1 / EN 1   traducere normala                           -> pereche buna
#   RO 2 / EN 2   2.000 km, al XVI-lea  vs  2,000 km, 16th    -> pereche buna; numerele normalizate coincid
#   RO 3          paragraf in chirilica, fara traducere       -> WRONG + observatie "alfabet chirilic"
#   RO 4 / EN 3   "Lеadеrship" cu e chirilic strecurat        -> pereche, observatie "litere straine"
#   RO 5 / EN 4   EN a ramas in romana                        -> pereche, observatii "diacritice in EN", "identic"
#   RO 6 / EN 5   RO a ramas in engleza                       -> pereche, observatii "RO fara diacritice", "identic"
#   RO 7 / EN 6   link diferit                                -> pereche, clauza "link-uri"
#   RO 8 / EN 7   gunoi "+++ STRUTUL IMENS" x3 in RO          -> pereche suspecta, observatii repetitii + markere
#   EN 8          citat in greaca, doar in EN                 -> doar in EN + observatie "alfabet grec"
#   RO 9 / EN 9   traducere normala                           -> pereche buna
#   RO 10 / EN 10 dialog in ambele                            -> pereche buna (clauza dialog tace)
#   RO 11 / EN 11 stelute ★★★ doar in RO                      -> pereche, clauza "simboluri"
#   RO 12 / EN 12 numele Eisenstein, Prokofiev lipsesc din EN -> pereche, clauza "nume proprii"

DEMO_RO = """<!-- ARTICOL START -->
<p class="text_obisnuit2">Adu-i pe oameni la pragul apropierii de un nou adevăr, înălțându-te deasupra gândirii obișnuite.</p>
<p class="text_obisnuit">Într-o zi au fost capturați 18 albatroși pe o insulă pierdută în Pacific. Duși la 2.000 km și la 7.000 km depărtare, toți au ajuns acasă în câteva zile, ca în veacul al XVI-lea, când corăbiile se orientau după stele.</p>
<p class="text_obisnuit">Это предложение осталось на русском языке, потому что кто-то вставил его сюда по ошибке и никто не заметил.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">Lеadеrship:</span> Imaginea pe care o atribui produsului tău corespunde cu realitatea pe care o percep cumpărătorii?</p>
<p class="text_obisnuit">Oamenii se împart în două categorii: oameni și neoameni, spune o veche zicală. Depinde de tine în care dintre ele vrei să intri.</p>
<p class="text_obisnuit">The sea looks at the sand without impoverishing the giver, and cannot give him what he has never had in the first place.</p>
<p class="text_obisnuit">Mai multe detalii despre acest subiect găsiți în articolul https://neculaifantanaru.com/legea-valorii.html publicat anul trecut.</p>
<p class="text_obisnuit2">+++ STRUTUL IMENS +++ STRUTUL IMENS +++ STRUTUL IMENS Produsul pe care îl promovezi este rezultatul involuntar al unei erori de percepție și de reproducere a unei imagini?</p>
<p class="text_obisnuit">Cel mai important lucru pe care trebuie să-l faci este să găsești o metodă prin care să te deosebești de ceilalți.</p>
<p class="text_obisnuit">— Iată răspunsul! gândi contele. Îți mulțumesc, tată, îți mulțumesc!</p>
<p class="text_obisnuit">★★★ Nisipul nu se lasă dus în larg de valurile mării, el rămâne întotdeauna aproape de țărm.</p>
<p class="text_obisnuit">Întâlnirea dintre Eisenstein și Prokofiev este un fenomen în istoria artelor, doi artiști cu o singură sensibilitate.</p>
<!-- ARTICOL FINAL -->"""

DEMO_EN = """<!-- ARTICOL START -->
<p class="text_obisnuit2">Bring people to the brink of approaching a new truth, exalting yourself above the ordinary way of thinking.</p>
<p class="text_obisnuit">One day, 18 albatrosses were captured on a lost island in the Pacific. Taken 2,000 km and 7,000 km away, they all arrived home in a few days, as in the 16th century, when ships navigated by the stars.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">Leadership:</span> Does the image you attribute to your product correspond to the reality perceived by the buyers?</p>
<p class="text_obisnuit">Oamenii se împart în două categorii: oameni și neoameni, spune o veche zicală. Depinde de tine în care dintre ele vrei să intri.</p>
<p class="text_obisnuit">The sea looks at the sand without impoverishing the giver, and cannot give him what he has never had in the first place.</p>
<p class="text_obisnuit">More details on this subject can be found in the article https://neculaifantanaru.com/en/the-law-of-value.html published last year.</p>
<p class="text_obisnuit2">Is the product you are promoting the involuntary result of an error of perception and of reproducing an image?</p>
<p class="text_obisnuit">Γνῶθι σεαυτόν, έλεγαν οι αρχαίοι Έλληνες, και αυτή η φράση παραμένει η αρχή κάθε ηγεσίας.</p>
<p class="text_obisnuit">The most important thing you have to do is to find a method through which you can set yourself apart from the others.</p>
<p class="text_obisnuit">— Here is the answer! thought the count. Thank you, father, thank you!</p>
<p class="text_obisnuit">The sand is not carried away by the waves of the sea, it always remains close to the shore.</p>
<p class="text_obisnuit">The meeting between the director and the composer is a phenomenon in the history of arts, two artists with a single sensibility.</p>
<!-- ARTICOL FINAL -->"""

DEMO_WRONG = [3]        # taguri RO asteptate fara corespondent
DEMO_EN_ONLY = [8]      # taguri EN asteptate fara corespondent (citatul grec)


def run_demo(out_dir, flexible=False):
    os.makedirs(out_dir, exist_ok=True)
    ro_path = os.path.join(out_dir, 'caz-nou-RO.html')
    en_path = os.path.join(out_dir, 'caz-nou-EN.html')
    with open(ro_path, 'w', encoding='utf-8') as f:
        f.write(DEMO_RO)
    with open(en_path, 'w', encoding='utf-8') as f:
        f.write(DEMO_EN)
    ro, en, ops, wrong, en_only = compare(ro_path, en_path, out_dir, flexible)
    got = ([t.number for t in wrong], [t.number for t in en_only])
    print(f"WRONG: {got[0]} (asteptat {DEMO_WRONG})   doar in EN: {got[1]} (asteptat {DEMO_EN_ONLY})")
    ok = got == (DEMO_WRONG, DEMO_EN_ONLY)
    print("REZULTAT CORECT" if ok else "REZULTAT DIFERIT DE CEL ASTEPTAT")
    print(f"Fisierele (caz-nou-RO.html, caz-nou-EN.html, rezultate.txt, aliniere.txt) sunt in: {out_dir}")
    return 0 if ok else 2


def main(argv=None):
    ap = argparse.ArgumentParser(description="compara_taguri + clauze noi (alfabet, diacritice, numere "
                                             "normalizate, link-uri, nume, repetitii, dialog, simboluri)")
    ap.add_argument('ro', nargs='?')
    ap.add_argument('en', nargs='?')
    ap.add_argument('-o', '--output-dir', default=OUT_DEFAULT)
    ap.add_argument('-v', '--verbose', action='store_true')
    ap.add_argument('--tip-flexibil', action='store_true')
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    if args.ro and args.en:
        compare(args.ro, args.en, args.output_dir, args.tip_flexibil, args.verbose)
        return 0
    return run_demo(args.output_dir, args.tip_flexibil)


if __name__ == '__main__':
    sys.exit(main())
