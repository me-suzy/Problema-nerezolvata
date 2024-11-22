from bs4 import BeautifulSoup

def count_tags(file_path):
    """Counts and classifies tags within the specified ARTICLE section in a given HTML file.

    Args:
        file_path (str): Path to the HTML file.

    Returns:
        dict: A dictionary containing the counts of each tag type.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        soup = BeautifulSoup(file.read(), 'html.parser')

    # Find the section between <!-- ARTICOL START --> and <!-- ARTICOL FINAL -->
    article_start = soup.find(string=lambda text: text and "ARTICOL START" in text)
    article_end = soup.find(string=lambda text: text and "ARTICOL FINAL" in text)

    if article_start and article_end:
        # Extract content between these two comments
        article_content = []
        for sibling in article_start.find_next_siblings():
            if sibling == article_end:
                break
            article_content.append(sibling)

        article_soup = BeautifulSoup(''.join(str(tag) for tag in article_content), 'html.parser')
    else:
        print("Nu am găsit secțiunea delimitată de comentarii în fișier.")
        return {'A': 0, 'B': 0, 'C': 0}

    # Count the tags within the article section
    tag_counts = {'A': 0, 'B': 0, 'C': 0}
    for i, tag in enumerate(article_soup.find_all('p')):
        if tag.span:
            tag_counts['A'] += 1
        elif tag.get('class') and 'text_obisnuit2' in tag['class']:
            tag_counts['B'] += 1
        else:
            tag_counts['C'] += 1
        print(f"Linia {i+1}: Tag {tag.get('class', 'Fără clasă')}")  # Optional: Print details for each tag
    return tag_counts

# Paths to the files
ro_file = 'd:/3/ro/atrageti-clientii-ca-un-magnet.html'
en_file = 'd:/3/en/do-you-attract-clients-like-a-magnet.html'

# Count tags in both files
ro_counts = count_tags(ro_file)
en_counts = count_tags(en_file)

# Compare and print results
print("\nNumăr total de tag-uri în Română:")
print(ro_counts)
print("\nNumăr total de tag-uri în Engleză:")
print(en_counts)

# Calculate differences
for tag_type in 'ABC':
    diff = ro_counts[tag_type] - en_counts[tag_type]
    print(f"Diferența de tag-uri de tip {tag_type}: {diff}")
