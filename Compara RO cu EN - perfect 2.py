from bs4 import BeautifulSoup
import re

def get_word_count(text):
    """Count words in text after removing HTML tags."""
    clean_text = re.sub(r'<[^>]+>', '', text)
    words = len(clean_text.split())
    return words

def get_greek_identifier(word_count):
    if word_count < 7:
        return 'α'
    elif word_count <= 14:
        return 'β'
    else:
        return 'γ'

def get_tag_type(tag):
    if tag.find('span', class_='text_obisnuit2'):
        return 'A'
    elif tag.get('class') and 'text_obisnuit2' in tag['class']:
        return 'B'
    elif tag.get('class') and 'text_obisnuit' in tag['class']:
        return 'C'
    return 'C'

def extract_article_tags(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file.read(), 'html.parser')

    article_start = soup.find(string=lambda text: text and "ARTICOL START" in text)
    article_end = soup.find(string=lambda text: text and "ARTICOL FINAL" in text)

    if not (article_start and article_end):
        return []

    tags = []
    current_element = article_start.next_element

    while current_element and current_element != article_end:
        if current_element.name == 'p':
            content = str(current_element)
            word_count = get_word_count(content)
            tag_type = get_tag_type(current_element)
            greek_id = get_greek_identifier(word_count)

            tags.append({
                'content': content,
                'tag_type': tag_type,
                'greek_id': greek_id
            })
        current_element = current_element.next_element

    return tags

def compare_tags(ro_file, en_file):
    ro_tags = extract_article_tags(ro_file)
    en_tags = extract_article_tags(en_file)

    wrong_tags = []
    matched_tags = []
    en_index = 0

    # Continuăm până procesăm toate tag-urile RO sau EN
    while ro_tags and en_index < len(en_tags):
        ro_tag = ro_tags[0]
        ro_tag['line_number'] = len(matched_tags) + len(wrong_tags) + 1
        en_tag = en_tags[en_index]

        if ro_tag['tag_type'] == en_tag['tag_type'] and ro_tag['greek_id'] == en_tag['greek_id']:
            # Avem match
            matched_tags.append((ro_tag, en_tag))
            ro_tags.pop(0)
            en_index += 1
        else:
            # Nu avem match - punem în wrong și reluăm de la început
            wrong_tags.append(ro_tag)
            ro_tags.pop(0)
            # Nu incrementăm en_index - următorul tag RO va fi comparat cu același tag EN

    # Adăugăm tag-urile RO rămase la wrong_tags
    for tag in ro_tags:
        tag['line_number'] = len(matched_tags) + len(wrong_tags) + 1
        wrong_tags.append(tag)

    return matched_tags, wrong_tags

def print_results(matched_tags, wrong_tags):
    print("\nTag-uri care nu au corespondent în EN (WRONG TAGS):")
    for tag in sorted(wrong_tags, key=lambda x: x['line_number']):
        print(f"\nLinia {tag['line_number']}({tag['tag_type']})({tag['greek_id']})")
        print(f"Conținut: {tag['content'][:100]}...")

    ro_counts = {'A': 0, 'B': 0, 'C': 0}
    en_counts = {'A': 0, 'B': 0, 'C': 0}

    for ro_tag, en_tag in matched_tags:
        ro_counts[ro_tag['tag_type']] += 1
        en_counts[en_tag['tag_type']] += 1

    for tag in wrong_tags:
        ro_counts[tag['tag_type']] += 1

    print("\nStatistici:")
    print("\nTag-uri în RO:", ro_counts)
    print("Tag-uri în EN:", en_counts)
    for tag_type in 'ABC':
        diff = ro_counts[tag_type] - en_counts[tag_type]
        print(f"Diferența pentru tag-uri de tip {tag_type}: {diff}")

if __name__ == "__main__":
    ro_file = 'd:/3/PROBEMA/atrageti-clientii-ca-un-magnet.html'
    en_file = 'd:/3/PROBEMA/do-you-attract-clients-like-a-magnet.html'

    matched_tags, wrong_tags = compare_tags(ro_file, en_file)
    print_results(matched_tags, wrong_tags)