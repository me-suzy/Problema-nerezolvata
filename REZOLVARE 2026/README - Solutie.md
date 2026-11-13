# Soluție: taguri RO fără corespondent în EN

## Ce este în acest folder

| Fișier | Rol |
|---|---|
| `repo/` | clona repo-ului GitHub `me-suzy/Problema-nerezolvata` (specificațiile și cele 2 fișiere model) |
| `compara_taguri.py` | **soluția** (Python 3, fără librării externe, nu are nevoie de BeautifulSoup) |
| `test_compara_taguri.py` | teste automate (exemplul din specificații + fișierele model + cazuri limită + controlul link-urilor) |
| `test_2_html.py` | compară direct cele două fișiere model din acest folder și verifică rezultatul (5, 11, 17) |
| `atrageti-clientii-ca-un-magnet.html`, `do-you-attract-clients-like-a-magnet.html` | cele două fișiere model (copie din `repo/`) |
| `Rezultate test_compara_taguri/` | scris de `test_compara_taguri.py` (sau de comanda de mai jos): `rezultate.txt` (raportul pentru fișierele model), `aliniere.txt` (tabelul RO ↔ EN cu costul fiecărei perechi), fișierul EN cu tagurile RO lipsă inserate la locul lor (OUTPUT din „1. Specificatii”) |
| `Rezultate test_2_html/` | aceleași trei fișiere, scrise de `test_2_html.py` |
| `Rezultate comparatii site - strict/`, `Rezultate comparatii site - tip-flexibil/` | rularea `compara_taguri.py` pe tot site-ul, în modul strict / `--tip-flexibil`: doar `rezultate.txt` și `aliniere.txt`; ce a afișat consola e în fișierele `... - consola.txt`; cifrele în `REZULTATE SITE - sumar.txt` |
| `VERIFICARE PERECHI SUSPECTE.txt` | verificarea manuală a celor 43 de perechi suspecte din prima rulare, pe categorii |
| `caz-nou.py`, `CAZ NOU - clauze.txt` | clauze suplimentare peste `compara_taguri.py` (alfabet, diacritice, numere normalizate, link-uri, nume proprii, repetiții, dialog, simboluri), cu un caz de test construit în script; rezultatele în `Rezultate caz-nou/` |

## Cum se rulează

Fără niciun argument (din orice folder sau direct din editor): compară tot site-ul, folderele `Principal\ro` și `Principal\en` (constantele `SITE_RO`, `SITE_EN` de la începutul scriptului), în modul `--tip-flexibil`, cu rezultatele în `Rezultate comparatii site - tip-flexibil\` de lângă script:

```bash
python compara_taguri.py
```

O pereche de fișiere:

```bash
python compara_taguri.py "repo/atrageti-clientii-ca-un-magnet.html" "repo/do-you-attract-clients-like-a-magnet.html" -o "Rezultate test_compara_taguri"
```

Toate fișierele din două foldere (perechea EN se ia din secțiunea `<!-- FLAGS -->`, `href=".../en/xxx.html"`, sau din numele identic):

```bash
python compara_taguri.py --ro-dir d:/3/ro --en-dir d:/3/en -o d:/3/Output
```

Testele (scriu și rezultatele pentru fișierele model în `Rezultate test_compara_taguri\`):

```bash
python test_compara_taguri.py
```

Doar cele două fișiere model din acest folder, cu verificarea rezultatului (scrie în `Rezultate test_2_html\`):

```bash
python test_2_html.py
```

Opțiuni: `-v` afișează identificatorii `Numar(Litera)(Grecesc)` ai fiecărui tag; `--merge` scrie și fișierul EN combinat (EN + tagurile RO lipsă, la locul lor); implicit scriptul nu scrie niciun HTML, doar analizează; `--tip-flexibil` (vezi mai jos).

În rapoarte, fișierele care au cel puțin un tag fără corespondent (în RO sau în EN) sau un link EN greșit au titlul marcat, ca să fie ușor de găsit: `---------Fișier: nume.html ------- PROBLEMA----------`.

Pe site-ul real (`Principal\ro` și `Principal\en`), ambele moduri, cu rezultatele în `Rezultate comparatii site - strict\` (strict, ca în specificații) și `Rezultate comparatii site - tip-flexibil\`:

```bash
python compara_taguri.py --ro-dir "E:\Carte\BB\17 - Site Leadership\Principal\ro" --en-dir "E:\Carte\BB\17 - Site Leadership\Principal\en" -o "Rezultate comparatii site - strict"
```

```bash
python compara_taguri.py --tip-flexibil --ro-dir "E:\Carte\BB\17 - Site Leadership\Principal\ro" --en-dir "E:\Carte\BB\17 - Site Leadership\Principal\en" -o "Rezultate comparatii site - tip-flexibil"
```

## Modul `--tip-flexibil` (învățat din datele reale)

Pe site, cea mai frecventă „diferență” nu este un paragraf netradus, ci **același paragraf cu altă clasă CSS**: în RO `text_obisnuit2` (B) sau cu `<span>` (A), iar în EN `text_obisnuit` (C). Regula strictă din specificații (litera trebuie să coincidă) raportează un asemenea paragraf de două ori: ca WRONG în RO și ca „doar în EN”.

Cu `--tip-flexibil`, litera diferită nu mai interzice perechea, ci doar o penalizează (`W_TYPE = 0.7`). Paragraful e împerecheat cu traducerea lui și apare într-o secțiune separată a raportului, „Perechi cu clasă diferită”, ca să poată fi corectată clasa. Rezultatele pe exemplul din specificații și pe fișierele model rămân identice în ambele moduri (test automat).

Raportul mai conține, în ambele moduri:
- „Tag-uri din EN care nu au corespondent în RO”;
- „Perechi în altă ordine”: paragraful există în EN, dar pe altă poziție (de ex. `adaosuri-III.html`, RO 37 ↔ EN 38). Alinierea păstrează ordinea, deci nu le poate împerechea; o trecere finală compară tagurile rămase și le împerechează dacă scorul `cost + 0.05 × distanța între poziții` este ≤ 0.2 (și distanța ≤ 5). Pragul a fost ales pe 11 perechi verificate manual pe site: reordonările reale au scor ≤ 0.2, pe când paragrafele fără legătură dar de lungime apropiată au scor peste 0.2 sau apar la distanțe de 14–100 de poziții. Regula e intenționat conservatoare: o reordonare ratată rămâne vizibilă ca WRONG + „doar în EN”, pe când o pereche falsă ar ascunde un WRONG;
- „Perechi suspecte (cost >= 1.5)”: perechi acceptate, dar cu lungimi foarte diferite (de ex. 19 cuvinte în RO și 77 în EN), de verificat manual;
- „Cost mediu al perechilor RO-EN” în statistici (vezi secțiunea următoare);
- fișierele fără marcaje `ARTICOL START/FINAL` și fișierele RO fără pereche EN sunt listate doar în consolă.

Tagurile `<p>` fără text vizibil sunt ignorate (dar numerotarea celorlalte rămâne cea din fișier). Fișierele care nu sunt UTF‑8 se citesc ca Windows‑1252; o eroare pe un fișier nu oprește rularea (vezi `erori.txt`).

## Controlul link-ului EN și costul mediu (învățat din verificarea perechilor suspecte)

Verificarea manuală a celor 43 de perechi suspecte din prima rulare (`VERIFICARE PERECHI SUSPECTE.txt`) a arătat că 17 dintre ele veneau din articole RO **a căror „traducere” era alt articol**: articolul RO e nou, iar link-ul EN din secțiunea FLAGS a fost copiat de la alt articol (de ex. `fiat-iustitia.html` trimite la `en/sidus-verbum.html`, care este traducerea lui `sidus-verbum.html`).

Scriptul face de aceea un **control exact**: citește steagul RO din fișierul EN (`<a href="https://site/xxx.html"><img … flag_lang_ro …>`). Dacă acesta trimite la alt fișier RO decât cel comparat, perechea nu se compară; în modul batch asemenea fișiere sunt listate la sfârșitul lui `rezultate.txt` („Fișiere RO al căror link EN duce la traducerea ALTUI articol”), împreună cu fișierul RO „adevărat” al EN-ului; în modul cu două fișiere raportul primește un avertisment `ATENȚIE: …`. Pe site: 17 fișiere RO (16 articole + o pagină de produs).

În plus, statisticile fiecărui fișier au linia „Cost mediu al perechilor RO-EN”. Un cost mediu peste `MEAN_SUSPECT = 0.6` înseamnă, de regulă, că EN-ul este alt text chiar dacă link-urile sunt corecte: pe site e cazul lui `supletea-deosebita-a-constructiei-de-montaj.html` (0.96; corpul EN este alt articol). Singurul fișier peste 0.6 care e totuși o traducere reală: `maturitatea-este-calea-de-iesire-din-amagirile-copilaresti.html` (0.60, RO completat cu 5 paragrafe noi).

## Rezultatul pe fișierele model

```
Tag-uri în RO: {'A': 2, 'B': 6, 'C': 9}
Tag-uri în EN: {'A': 2, 'B': 4, 'C': 8}
Diferența pentru tag-uri de tip A: 0
Diferența pentru tag-uri de tip B: 2
Diferența pentru tag-uri de tip C: 1
Cost mediu al perechilor RO-EN: 0.13 (14 perechi; peste 0.6 înseamnă, de regulă, alt text)

În RO există în plus față de EN următoarele: 2 taguri de tipul (B) și 1 tag de tipul (C)

Tag-uri care nu au corespondent în EN (WRONG TAGS):

5.C  <p class="text_obisnuit">GASCA ESTE ACASA</p>
11.B <p class="text_obisnuit2">BABA OARBA Produsul pe care îl promovezi ...</p>
17.B <p class="text_obisnuit2">COCO CHANNEL Locaţia unui produs poate influenţa ...</p>
```

Exact cele trei taguri cerute, inclusiv cazul greu „BABA OARBA” vs „Leadership: Produsul…”, unde ambele taguri RO au aceiași identificatori (B, γ) și vechiul cod îl alegea pe cel greșit.

## De ce nu mergea înainte

Toate variantele vechi comparau **secvențial**: tagul RO curent cu tagul EN curent, și la prima nepotrivire eliminau tagul RO. Când două taguri RO vecine au aceiași identificatori (același tip, același interval de cuvinte), comparația secvențială îl „consumă” pe primul (BABA OARBA ↔ Leadership EN) și apoi îl declară greșit pe al doilea (Leadership RO), deși tocmai primul era cel în plus. Nicio regulă locală („uită-te la 4 taguri înainte și după”) nu rezolvă asta, pentru că ambele alegeri lasă contextul la fel.

## Cum rezolvă acest cod (matematic, fără cuvinte-cheie)

1. **Identificatorii din specificații** se calculează pentru fiecare tag: numărul, litera A/B/C (după structura HTML) și identificatorul grecesc α/β/γ (după numărul de cuvinte).

2. **Aliniere globală prin programare dinamică** (algoritmul Needleman–Wunsch, același principiu ca Gale–Church pentru alinierea traducerilor). În loc să decidă tag cu tag, algoritmul caută, dintre *toate* alinierile posibile RO ↔ EN care păstrează ordinea, pe cea cu **cost total minim**. Asta este exact „procesul cartezian” din instrucțiuni (se ține cont de toate tagurile dinainte și după), dar făcut riguros pe întreaga listă, nu pe o fereastră de 4 taguri.

3. **Costul unei perechi RO–EN** (mic = probabil traducere):
   - literă diferită → perechea este interzisă (regula din specificații: tipul trebuie să coincidă);
   - raportul de lungime: `|ln(cuvinte_RO / (r · cuvinte_EN))|`, unde `r` este raportul mediu RO/EN al documentului, calculat automat (mediana perechilor din prima trecere); astfel identificatorul grecesc devine o măsură continuă, nu doar 3 praguri, și „β vs α” pentru 7 vs 6 cuvinte nu mai e o problemă;
   - semnătura de punctuație: diferențe la numărul de `?`, `!`, `:`, `;`, ghilimele, paranteze și propoziții (se păstrează în traducere);
   - numerele care apar doar într-o parte (ex. „10 luni” vs „4-5 months”);
   - cuvintele scrise cu MAJUSCULE (acronime, nume) — diferența la numărul lor;
   - bonus pentru cuvinte identice în ambele texte (nume proprii, „Leadership”, „etc.”, „internet”).
   Un tag lăsat fără pereche costă `GAP = 1.0`.

4. Tagurile RO rămase fără pereche sunt **WRONG TAGS**; tagurile EN fără pereche se raportează separat.

În cazul „BABA OARBA”: perechea *BABA OARBA ↔ Leadership EN* costă ≈ 0.43 (lungime) + 0.25 (lipsește `:`) + 0.8 (7 cuvinte cu majuscule), iar perechea *Leadership RO ↔ Leadership EN* costă ≈ 0.04. Alinierea globală alege a doua variantă și lasă BABA OARBA fără pereche, oricare ar fi poziția lui în fișier.

## Limite

- Dacă un tag RO și traducerea lui EN au **tipuri diferite** (de ex. în RO e `text_obisnuit2`, în EN e `text_obisnuit`), în modul strict ambele vor fi raportate ca fără corespondent. Este comportamentul cerut în specificații; `--tip-flexibil` le împerechează.
- Dacă traducerea EN este drastic mai scurtă/lungă decât originalul (de ex. 40 de cuvinte traduse în 8), costul de lungime poate depăși `GAP` și tagul va fi raportat ca lipsă. Pragurile (`GAP`, `W_*`) sunt la începutul scriptului și se pot ajusta.
- Metoda compară lungime și structură, nu sens: două paragrafe fără legătură, dar de lungime apropiată, pot fi împerechete (pe site: 2 cazuri din 43 de perechi suspecte, care ascundeau câte un paragraf netradus). Într-o listă de citate numerotate și ordonate diferit în RO și EN (`citate-celebre-despre-leadership.html`), numerele identice din text împing alinierea pe poziție și raportul nu e de încredere.
- Un paragraf RO despărțit în două în EN (sau două aforisme RO într-un singur `<p>`, ca în `cartea-de-nisip.html`) apare ca pereche suspectă plus un WRONG / „doar în EN” fals.
