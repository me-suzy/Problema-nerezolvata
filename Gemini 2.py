import re

# File paths
file_ro_path = r"e:\Carte\BB\17 - Site Leadership\Principal\ro\hello-charlie.html"
file_en_path = r"e:\Carte\BB\17 - Site Leadership\Principal\en\hello-charlie.html"

# Regex pentru taguri
pattern_tags = re.compile(
    r'<p class="text_obisnuit2">(.*?)</p>|'
    r'<p class="text_obisnuit"><span class="text_obisnuit2">(.*?)</span>(.*?)</p>|'
    r'<p class="text_obisnuit">(.*?)</p>',
    re.DOTALL | re.IGNORECASE
)

def extract_tags(content):
    """Return a list of tags extracted from HTML content."""
    matches = pattern_tags.findall(content)
    tags = []
    for m in matches:
        if m[0]:  # text_obisnuit2
            tags.append("text_obisnuit2")
        elif m[1] and m[2]:  # text_obisnuit-span
            tags.append("text_obisnuit-span")
        elif m[3]:  # text_obisnuit simplu
            tags.append("text_obisnuit")
    return tags

def main():
    with open(file_ro_path, "r", encoding="utf-8") as f_ro:
        ro_content = f_ro.read()
    with open(file_en_path, "r", encoding="utf-8") as f_en:
        en_content = f_en.read()

    # Extragem doar tipurile de taguri
    ro_tags = extract_tags(ro_content)
    en_tags = extract_tags(en_content)

    print(f"Romanian tags count: {len(ro_tags)}")
    print(f"English tags count: {len(en_tags)}\n")

    # Verificăm diferențele
    if len(ro_tags) > len(en_tags):
        print(f"{len(ro_tags) - len(en_tags)} extra instances in Romanian file.")
    else:
        print("No extra instances in Romanian file.")

    if len(en_tags) > len(ro_tags):
        print(f"{len(en_tags) - len(ro_tags)} extra instances in English file.")
    else:
        print("No extra instances in English file.")

if __name__ == "__main__":
    main()
