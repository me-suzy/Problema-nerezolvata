# -*- coding: utf-8 -*-
"""
Teste pentru compara_taguri.py

    python test_compara_taguri.py

Testele acopera:
  1. exemplul mic din "1. Specificatii.txt" (9 taguri RO vs 6 taguri EN)
  2. fisierele model din repo (atrageti-clientii-ca-un-magnet.html vs
     do-you-attract-clients-like-a-magnet.html) -> 5.C, 11.B, 17.B
  3. cazul "taguri asemanatoare" (BABA OARBA vs Leadership) izolat
  4. fisiere identice -> nimic in plus
  5. tag in plus in EN -> raportat ca "doar in EN", nimic WRONG in RO
  6. link EN gresit (steagul RO din EN trimite la alt fisier) -> perechea nu se compara

Rezultatele pentru fisierele model (raport, aliniere, fisier EN combinat) se scriu in
folderul "Rezultate test_compara_taguri".
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compara_taguri as ct  # noqa: E402

REPO = os.path.join(HERE, 'repo')
# folderul in care testul scrie raportul, alinierea si fisierul EN combinat pentru fisierele model
OUT_DIR = os.path.join(HERE, 'Rezultate test_compara_taguri')

SPEC_RO = """<!-- ARTICOL START -->
<p class="text_obisnuit"><span class="text_obisnuit2">Stiu ca este dificil sa conduci la inceput, </span>dar dupa 10 luni inveti.</p>
<p class="text_obisnuit2">Imi place sa merg la scoala si sa invat, mai ales in timpul saptamanii.</p>
<p class="text_obisnuit">Sunt un bun conducator auto, dar am facut si greseli din care am invatat.</p>
<p class="text_obisnuit">În fond, cele scrise de mine, sunt adevarate.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">Ma iubesti?</span> Cat de mult? </p>
<p class="text_obisnuit">Iubesc sa conduc masina.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">Stiu ca este dificil sa conduci la inceput, </span>dar dupa 4-5 luni inveti.</p>
<p class="text_obisnuit">Totul se repetă, chiar și ochii care nu se vad.</p>
<p class="text_obisnuit2">BEE servesc o cafea 2 mai buna</p>
<!-- ARTICOL FINAL -->"""

SPEC_EN = """<!-- ARTICOL START -->
<p class="text_obisnuit2">I like going to school and learning, especially during the week.</p>
<p class="text_obisnuit">I'm a good driver, but I've also made mistakes that I've learned from.</p>
<p class="text_obisnuit">Basically, what I wrote is true.</p>
<p class="text_obisnuit">I love driving.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">I know it's difficult to drive at first, </span> but after 4-5 months you learn.</p>
<p class="text_obisnuit">Everything is repeated, even the eyes that can't see.</p>
<!-- ARTICOL FINAL -->"""

SPEC_OUTPUT = """<!-- ARTICOL START -->
<p class="text_obisnuit"><span class="text_obisnuit2">Stiu ca este dificil sa conduci la inceput, </span>dar dupa 10 luni inveti.</p>
<p class="text_obisnuit2">I like going to school and learning, especially during the week.</p>
<p class="text_obisnuit">I'm a good driver, but I've also made mistakes that I've learned from.</p>
<p class="text_obisnuit">Basically, what I wrote is true.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">Ma iubesti?</span> Cat de mult? </p>
<p class="text_obisnuit">I love driving.</p>
<p class="text_obisnuit"><span class="text_obisnuit2">I know it's difficult to drive at first, </span> but after 4-5 months you learn.</p>
<p class="text_obisnuit">Everything is repeated, even the eyes that can't see.</p>
<p class="text_obisnuit2">BEE servesc o cafea 2 mai buna</p>
<!-- ARTICOL FINAL -->"""


def run(ro_html, en_html, flexible=False):
    ro = ct.parse_tags(ct.extract_article(ro_html)[1])
    en = ct.parse_tags(ct.extract_article(en_html)[1])
    ops, total, ratio = ct.align(ro, en, flexible)
    wrong = [ro[i].number for op, i, j, _ in ops if op == 'R']
    en_only = [en[j].number for op, i, j, _ in ops if op == 'E']
    return ro, en, ops, wrong, en_only


class TestSpecExample(unittest.TestCase):
    def test_identifiers(self):
        ro = ct.parse_tags(ct.extract_article(SPEC_RO)[1])
        self.assertEqual([t.ident for t in ro],
                         ['1(A)(β)', '2(B)(β)', '3(C)(β)', '4(C)(β)', '5(A)(α)',
                          '6(C)(α)', '7(A)(β)', '8(C)(β)', '9(B)(β)'])
        en = ct.parse_tags(ct.extract_article(SPEC_EN)[1])
        self.assertEqual([t.ident for t in en],
                         ['1(B)(β)', '2(C)(β)', '3(C)(α)', '4(C)(α)', '5(A)(β)', '6(C)(β)'])

    def test_wrong_tags(self):
        ro, en, ops, wrong, en_only = run(SPEC_RO, SPEC_EN)
        self.assertEqual(wrong, [1, 5, 9])
        self.assertEqual(en_only, [])

    def test_merged_output(self):
        ro, en, ops, wrong, en_only = run(SPEC_RO, SPEC_EN)
        merged = ct.build_merged(SPEC_EN, ro, en, ops)
        got = [t.html for t in ct.parse_tags(ct.extract_article(merged)[1])]
        want = [t.html for t in ct.parse_tags(ct.extract_article(SPEC_OUTPUT)[1])]
        self.assertEqual(got, want)


class TestModelFiles(unittest.TestCase):
    def setUp(self):
        self.ro_path = os.path.join(REPO, 'atrageti-clientii-ca-un-magnet.html')
        self.en_path = os.path.join(REPO, 'do-you-attract-clients-like-a-magnet.html')
        if not (os.path.exists(self.ro_path) and os.path.exists(self.en_path)):
            self.skipTest('fisierele model nu sunt in folderul repo/')

    def test_counts_and_wrong(self):
        ro, en, ops, wrong, en_only = run(ct.read(self.ro_path), ct.read(self.en_path))
        self.assertEqual(ct.count_kinds(ro), {'A': 2, 'B': 6, 'C': 9})
        self.assertEqual(ct.count_kinds(en), {'A': 2, 'B': 4, 'C': 8})
        self.assertEqual(wrong, [5, 11, 17])
        self.assertEqual(en_only, [])
        texts = [ro[n - 1].text for n in wrong]
        self.assertTrue(texts[0].startswith('GASCA ESTE ACASA'))
        self.assertTrue(texts[1].startswith('BABA OARBA'))
        self.assertTrue(texts[2].startswith('COCO CHANNEL'))

    def test_writes_results_folder(self):
        """Scrie rezultatele pentru fisierele model in 'Rezultate test_compara_taguri'."""
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):
            r = ct.compare_files(self.ro_path, self.en_path, out_dir=OUT_DIR, merge=True)
        self.assertEqual([t.number for t in r['wrong']], [5, 11, 17])
        for name in ('rezultate.txt', 'aliniere.txt', 'do-you-attract-clients-like-a-magnet.html'):
            self.assertTrue(os.path.exists(os.path.join(OUT_DIR, name)), name)


class TestSimilarTags(unittest.TestCase):
    RO = """<!-- ARTICOL START -->
<p class="text_obisnuit">Se pare că pe orice piaţă unde primează calitatea serviciilor, cei mai câştigaţi întreprinzători sunt aceia care ocupă locul cel mai favorabil.</p>
<p class="text_obisnuit2">BABA OARBA Produsul pe care îl promovezi este rezultatul involuntar al unei erori de BABA OARBA percepţie şi de reproducere a unei imagini care invită la extragerea unei concluzii BABA OARBA sumbre privitoare la amplasamentul său? BABA OARBA BABA OARBA BABA OARBA</p>
<p class="text_obisnuit2">Leadership: Produsul pe care îl promovezi este rezultatul involuntar al unei erori de percepţie şi de reproducere a unei imagini care invită la extragerea unei concluzii sumbre privitoare la amplasamentul său?</p>
<p class="text_obisnuit">Cel mai important lucru pe care trebuie să-l faci este să găseşti o metodă prin care să-i determini pe clienţi să depindă de produsul tău.</p>
<!-- ARTICOL FINAL -->"""
    EN = """<!-- ARTICOL START -->
<p class="text_obisnuit">It seems that on any market where the quality of the services it's on the first place, the entrepreneurs who are winners are those who have the favorable place.</p>
<p class="text_obisnuit2">Leadership: Is the product you are promoting the involuntary result of an image perception and reproduction error that calls for a bleak conclusion regarding its location?</p>
<p class="text_obisnuit">The most important thing you have to do is to find a method through which you can make your clients depend on your product.</p>
<!-- ARTICOL FINAL -->"""

    def test_picks_the_right_one(self):
        ro, en, ops, wrong, en_only = run(self.RO, self.EN)
        self.assertEqual(wrong, [2])          # BABA OARBA, nu "Leadership"
        self.assertEqual(en_only, [])


class TestReordered(unittest.TestCase):
    """Un paragraf mutat pe alta pozitie in EN nu este WRONG, ci 'in alta ordine'."""
    RO = """<!-- ARTICOL START -->
<p class="text_obisnuit">Primul paragraf vorbește despre începuturile leadershipului și despre curaj.</p>
<p class="text_obisnuit">Al doilea paragraf, cel mutat, descrie eforturile de străpungere a limitelor personale, cu răbdare și disciplină zilnică, pentru că nimic durabil nu se construiește în grabă, iar fiecare pas mic adună în timp o distanță pe care nimeni nu o vede la început.</p>
<p class="text_obisnuit">Al treilea paragraf este despre perfecțiune: geometria secretă a formei?</p>
<p class="text_obisnuit">Al patrulea paragraf încheie discuția despre limitări și margini, despre alunecarea spre periferie și despre felul în care revenim mereu la centru.</p>
<!-- ARTICOL FINAL -->"""
    EN = """<!-- ARTICOL START -->
<p class="text_obisnuit">The first paragraph talks about leadership beginnings and courage.</p>
<p class="text_obisnuit">The third paragraph is about perfection: the secret geometry of form?</p>
<p class="text_obisnuit">The fourth paragraph ends the discussion about limitations and margins, about slipping to the periphery and how we always return to the centre.</p>
<p class="text_obisnuit">The second paragraph, the moved one, describes the efforts to break through personal limits, with patience and daily discipline, because nothing durable is built in a hurry, and every small step adds up over time to a distance nobody sees at first.</p>
<!-- ARTICOL FINAL -->"""

    def test_moved_paragraph(self):
        ro, en, ops, wrong, en_only = run(self.RO, self.EN)
        self.assertEqual((wrong, en_only), ([], []))
        moved = [(ro[i].number, en[j].number) for op, i, j, _ in ops if op == 'X']
        self.assertEqual(moved, [(2, 4)])


class TestEdgeCases(unittest.TestCase):
    def test_identical(self):
        ro, en, ops, wrong, en_only = run(SPEC_RO, SPEC_RO)
        self.assertEqual(wrong, [])
        self.assertEqual(en_only, [])

    def test_extra_in_en(self):
        ro, en, ops, wrong, en_only = run(SPEC_EN, SPEC_RO)
        self.assertEqual(wrong, [])
        self.assertEqual(en_only, [1, 5, 9])

    def test_missing_markers(self):
        self.assertIsNone(ct.extract_article('<p class="text_obisnuit">x</p>'))

    def test_empty_tags_are_skipped_but_numbering_is_kept(self):
        html = """<!-- ARTICOL START -->
<p class="text_obisnuit">Unu doi trei.</p>
<p class="text_obisnuit2"></p>
<p class="text_obisnuit">Patru cinci.</p>
<!-- ARTICOL FINAL -->"""
        tags = ct.parse_tags(ct.extract_article(html)[1])
        self.assertEqual([t.number for t in tags], [1, 3])


class TestFlexibleType(unittest.TestCase):
    """--tip-flexibil: acelasi paragraf cu alta clasa CSS se imperecheaza,
       dar rezultatele din specificatii raman neschimbate."""
    RO = """<!-- ARTICOL START -->
<p class="text_obisnuit">Primul paragraf, destul de lung ca să conteze în comparație, cu multe cuvinte.</p>
<p class="text_obisnuit2">Al doilea paragraf este scris cu clasa text_obisnuit2 în română, dar nu și în engleză.</p>
<p class="text_obisnuit">Al treilea paragraf încheie articolul cu o concluzie scurtă.</p>
<!-- ARTICOL FINAL -->"""
    EN = """<!-- ARTICOL START -->
<p class="text_obisnuit">The first paragraph, long enough to matter in the comparison, with many words.</p>
<p class="text_obisnuit">The second paragraph is written with the text_obisnuit2 class in Romanian, but not in English.</p>
<p class="text_obisnuit">The third paragraph ends the article with a short conclusion.</p>
<!-- ARTICOL FINAL -->"""

    def test_strict_reports_both_sides(self):
        ro, en, ops, wrong, en_only = run(self.RO, self.EN)
        self.assertEqual((wrong, en_only), ([2], [2]))

    def test_flexible_pairs_them(self):
        ro, en, ops, wrong, en_only = run(self.RO, self.EN, flexible=True)
        self.assertEqual((wrong, en_only), ([], []))
        diff = [(ro[i].number, en[j].number) for op, i, j, _ in ops if op == 'M' and ro[i].kind != en[j].kind]
        self.assertEqual(diff, [(2, 2)])

    def test_spec_and_model_unchanged_in_flexible_mode(self):
        ro, en, ops, wrong, en_only = run(SPEC_RO, SPEC_EN, flexible=True)
        self.assertEqual((wrong, en_only), ([1, 5, 9], []))
        ro_path = os.path.join(REPO, 'atrageti-clientii-ca-un-magnet.html')
        en_path = os.path.join(REPO, 'do-you-attract-clients-like-a-magnet.html')
        if os.path.exists(ro_path) and os.path.exists(en_path):
            ro, en, ops, wrong, en_only = run(ct.read(ro_path), ct.read(en_path), flexible=True)
            self.assertEqual((wrong, en_only), ([5, 11, 17], []))


class TestPairLinks(unittest.TestCase):
    """Steagul RO din fisierul EN trebuie sa trimita inapoi la fisierul RO comparat; altfel EN-ul
       este traducerea altui articol (link EN copiat gresit in RO) si perechea nu se compara."""
    FLAGS = ('<!-- FLAGS_1 --><a href="https://site.com/{ro}"><img src="x/flag_lang_ro.jpg" alt="ro"></a> '
             '<a href="https://site.com/en/{en}"><img src="x/flag_lang_en.jpg" alt="en"></a><!-- FLAGS -->\n')

    def test_extract_ro_filename(self):
        en = self.FLAGS.format(ro='articol.html', en='article.html') + SPEC_EN
        self.assertEqual(ct.extract_ro_filename(en), 'articol.html')
        self.assertIsNone(ct.extract_ro_filename(SPEC_EN))

    def test_find_pairs_separates_wrong_links(self):
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            ro_dir, en_dir = os.path.join(d, 'ro'), os.path.join(d, 'en')
            os.makedirs(ro_dir), os.makedirs(en_dir)
            def w(path, text):
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(text)
            # pereche buna: bun.html <-> good.html (good.html trimite inapoi la bun.html)
            w(os.path.join(ro_dir, 'bun.html'), self.FLAGS.format(ro='bun.html', en='good.html') + SPEC_RO)
            w(os.path.join(en_dir, 'good.html'), self.FLAGS.format(ro='bun.html', en='good.html') + SPEC_EN)
            # link gresit: nou.html trimite la good.html, care este traducerea lui bun.html
            w(os.path.join(ro_dir, 'nou.html'), self.FLAGS.format(ro='nou.html', en='good.html') + SPEC_RO)
            # EN lipsa
            w(os.path.join(ro_dir, 'orfan.html'), self.FLAGS.format(ro='orfan.html', en='nope.html') + SPEC_RO)
            pairs, missing, mismatched = ct.find_pairs(ro_dir, en_dir)
            self.assertEqual([os.path.basename(r) for r, e in pairs], ['bun.html'])
            self.assertEqual([(os.path.basename(r), e) for r, e in missing], [('orfan.html', 'nope.html')])
            self.assertEqual([(os.path.basename(r), e, b) for r, e, b in mismatched],
                             [('nou.html', 'good.html', 'bun.html')])
            # in mod single, raportul primeste un avertisment (raportul se tipareste; il inghitim)
            import contextlib, io
            with contextlib.redirect_stdout(io.StringIO()):
                r1 = ct.compare_files(os.path.join(ro_dir, 'nou.html'), os.path.join(en_dir, 'good.html'), merge=False)
                r2 = ct.compare_files(os.path.join(ro_dir, 'bun.html'), os.path.join(en_dir, 'good.html'), merge=False)
            self.assertIn('ATENȚIE', r1['report'])
            self.assertNotIn('ATENȚIE', r2['report'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
