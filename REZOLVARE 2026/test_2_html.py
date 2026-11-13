# -*- coding: utf-8 -*-
r"""
Compara direct cele doua fisiere model (RO si EN) din folderul PROBLEMA si afiseaza
tagurile RO care nu au corespondent in EN.

    python test_2_html.py

Rezultatul asteptat (din specificatii):
    Tag-uri in RO: {'A': 2, 'B': 6, 'C': 9}
    Tag-uri in EN: {'A': 2, 'B': 4, 'C': 8}
    WRONG TAGS: 5.C GASCA ESTE ACASA, 11.B BABA OARBA ..., 17.B COCO CHANNEL ...

Raportul se scrie si in "Rezultate test_2_html\rezultate.txt", alinierea completa in
"Rezultate test_2_html\aliniere.txt", iar fisierul EN cu paragrafele RO lipsa inserate la locul lor in
"Rezultate test_2_html\do-you-attract-clients-like-a-magnet.html".
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import compara_taguri as ct  # noqa: E402

RO_FILE = os.path.join(HERE, 'atrageti-clientii-ca-un-magnet.html')
EN_FILE = os.path.join(HERE, 'do-you-attract-clients-like-a-magnet.html')
OUT_DIR = os.path.join(HERE, 'Rezultate test_2_html')

ASTEPTAT = [5, 11, 17]   # numerele tagurilor RO fara corespondent in EN


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    for path in (RO_FILE, EN_FILE):
        if not os.path.exists(path):
            print(f"Lipseste fisierul: {path}")
            return 1

    # verbose=True afiseaza si identificatorii Numar(Litera)(Grecesc) ai fiecarui tag
    rezultat = ct.compare_files(RO_FILE, EN_FILE, out_dir=OUT_DIR, merge=True, verbose=True)
    if rezultat is None:
        return 1

    gasit = [t.number for t in rezultat['wrong']]
    print(f"Taguri RO fara corespondent in EN: {gasit}   (asteptat: {ASTEPTAT})")
    print("REZULTAT CORECT" if gasit == ASTEPTAT else "REZULTAT DIFERIT DE CEL ASTEPTAT")
    print(f"Fisierele de iesire sunt in: {OUT_DIR}")
    return 0 if gasit == ASTEPTAT else 2


if __name__ == '__main__':
    sys.exit(main())
