import re
import os
import glob
from bs4 import BeautifulSoup
import difflib

def extract_en_filename(content):
    # Codul dvs. existent
    flags_section = re.search(r'<!-- FLAGS[_\d]* -->(.*?)<!-- FLAGS -->', content, re.DOTALL)
    if not flags_section:
        return None
    match = re.search(r'href="https://neculaifantanaru\.com/en/([^"]+)"', flags_section.group(1))
    return match.group(1) if match else None

def find_corresponding_files(ro_dir, en_dir):
    # Codul dvs. existent
    file_pairs = []
    ro_files = glob.glob(os.path.join(ro_dir, '*.html'))
    print(f"Am găsit {len(ro_files)} fișiere RO")

    for ro_file in ro_files:
        with open(ro_file, 'r', encoding='utf-8') as f:
            content = f.read()
        en_filename = extract_en_filename(content)
        if en_filename:
            en_file = os.path.join(en_dir, en_filename)
            if os.path.exists(en_file):
                file_pairs.append((ro_file, en_file))
                print(f"Potrivire: {os.path.basename(ro_file)} -> {en_filename}")
    return file_pairs

def count_words(text):
    # Codul dvs. existent
    return len(text.strip().split())

def get_greek_identifier(word_count):
    # Codul dvs. existent cu intervalele extinse
    if word_count < 7:
        return 'α'
    elif word_count <= 14:
        return 'β'
    elif word_count <= 24:
        return 'γ'
    elif word_count <= 34:
        return 'δ'
    elif word_count <= 44:
        return 'ε'
    elif word_count <= 54:
        return 'ζ'
    elif word_count <= 64:
        return 'η'
    else:
        return 'θ'

def get_tag_type(tag):
    # Codul dvs. existent
    if tag.find('span'):
        return 'A'
    elif 'text_obisnuit2' in tag.get('class', []):
        return 'B'
    return 'C'

def get_tag_identifier(tag):
    """Creează un identificator unic pentru un tag bazat pe tip și identificatorul grecesc."""
    return f"{tag['type']}_{tag['greek']}"

def analyze_tags(content):
    """Analizează tagurile și returnează informații despre fiecare tag."""
    article_content = re.search(r'<!-- ARTICOL START -->(.*?)<!-- ARTICOL FINAL -->',
                                content, re.DOTALL)

    if not article_content:
        print("Avertisment: Nu s-a găsit conținutul articolului")
        return []

    content = article_content.group(1)
    soup = BeautifulSoup(content, 'html.parser')
    tags_info = []

    # Găsește paragrafele din <div align="justify">
    main_div = soup.find('div', attrs={'align': 'justify'})
    if not main_div:
        print("Avertisment: Nu s-a găsit div-ul principal")
        return []

    paragraphs = main_div.find_all('p', class_=['text_obisnuit', 'text_obisnuit2'])
    print(f"Am găsit {len(paragraphs)} paragrafe")

    for i, tag in enumerate(paragraphs):
        text_content = tag.get_text(strip=True)
        if text_content:  # Include doar tagurile cu text
            tag_type = get_tag_type(tag)
            word_count = count_words(text_content)
            greek_id = get_greek_identifier(word_count)
            tag_id = get_tag_identifier({'type': tag_type, 'greek': greek_id})

            tags_info.append({
                'number': i + 1,
                'type': tag_type,
                'greek': greek_id,
                'identifier': tag_id,
                'content': str(tag),
                'text': text_content
            })
            print(f"Tag găsit de tip {tag_type} cu identificator {tag_id}: {text_content[:50]}...")

    return tags_info

def compare_tags(ro_tags, en_tags):
    """Compară tagurile și găsește diferențele folosind alinierea secvențelor."""
    ro_ids = [get_tag_identifier(tag) for tag in ro_tags]
    en_ids = [get_tag_identifier(tag) for tag in en_tags]

    matcher = difflib.SequenceMatcher(None, ro_ids, en_ids)
    opcodes = matcher.get_opcodes()

    wrong_tags = []

    for tag, i1, i2, j1, j2 in opcodes:
        if tag == 'delete':
            # Taguri care sunt în RO, dar lipsesc în EN
            wrong_tags.extend(ro_tags[i1:i2])

    return wrong_tags

def format_results(wrong_tags):
    """Formatează rezultatele pentru afișare și salvare."""
    type_counts = {'A': 0, 'B': 0, 'C': 0}
    type_content = {'A': [], 'B': [], 'C': []}

    for tag in wrong_tags:
        type_counts[tag['type']] += 1
        type_content[tag['type']].append(tag['content'])

    result = []

    # Prima linie cu sumarul
    summary_parts = []
    for tag_type in ['A', 'B', 'C']:
        if type_counts[tag_type] > 0:
            summary_parts.append(f"{type_counts[tag_type]} taguri de tipul ({tag_type})")
    result.append("În RO există în plus față de EN următoarele: " + " și ".join(summary_parts))

    # Detaliile pentru fiecare tip de tag
    for tag_type in ['A', 'B', 'C']:
        if type_counts[tag_type] > 0:
            tag_word = "taguri" if type_counts[tag_type] > 1 else "tag"
            result.append(f"\n{type_counts[tag_type]}({tag_type}) adică aceste {tag_word}:")
            for content in type_content[tag_type]:
                result.append(content)
            result.append("")  # Linie goală pentru separare

    return "\n".join(result)

def process_all_files():
    ro_dir = r'd:/3/ro'
    en_dir = r'd:/3/en'
    output_dir = r'd:/3/Output'

    print("Începem compararea...")
    file_pairs = find_corresponding_files(ro_dir, en_dir)
    all_results = []

    for ro_file, en_file in file_pairs:
        print(f"\nProcesăm: {os.path.basename(ro_file)}")

        with open(ro_file, 'r', encoding='utf-8') as f:
            ro_content = f.read()
        with open(en_file, 'r', encoding='utf-8') as f:
            en_content = f.read()

        ro_tags = analyze_tags(ro_content)
        print(f"Taguri RO: {len(ro_tags)}")
        en_tags = analyze_tags(en_content)
        print(f"Taguri EN: {len(en_tags)}")
        wrong_tags = compare_tags(ro_tags, en_tags)

        if wrong_tags:
            results = format_results(wrong_tags)
            header = f"\n---------Fișier: {os.path.basename(ro_file)}\n"
            results_with_header = header + results
            all_results.append(results_with_header)
            print(results_with_header)

    if all_results:
        # Creează directorul de output dacă nu există
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, 'rezultate.txt')
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(''.join(all_results))
        print(f"\nRezultatele au fost salvate în: {output_path}")
    else:
        print("\nNu s-au găsit diferențe în niciun fișier")

if __name__ == "__main__":
    process_all_files()
