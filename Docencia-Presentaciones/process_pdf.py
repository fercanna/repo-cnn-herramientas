import sys
from pypdf import PdfReader
import re

def find_chapter_start(reader, chapter_pattern):
    """Finds the page number where a chapter starts."""
    for i in range(len(reader.pages)):
        page = reader.pages[i]
        text = page.extract_text()
        if re.search(chapter_pattern, text, re.IGNORECASE):
            return i
    return -1

def extract_chapter_text(reader, start_page, end_pattern):
    """Extracts text from the start page until the end pattern is found."""
    full_text = ""
    for i in range(start_page, len(reader.pages)):
        page = reader.pages[i]
        text = page.extract_text()
        if i > start_page and re.search(end_pattern, text, re.IGNORECASE):
            # If we find the next chapter's title, stop.
            break
        full_text += f"--- Page {i+1} ---\n"
        full_text += text
        full_text += "\n\n"
    return full_text

def main():
    pdf_path = "Gestion por procesos y riesgo operacional_2020_AENOR.PDF"
    try:
        reader = PdfReader(pdf_path)
    except FileNotFoundError:
        print(f"Error: El archivo '{pdf_path}' no fue encontrado.", file=sys.stderr)
        sys.exit(1)

    # Patterns to identify the start of Chapter 10 and Chapter 11
    # This assumes the title is clear in the text.
    chapter_10_pattern = r"10\.\s+Gesti(ó|o)n del riesgo operacional"
    chapter_11_pattern = r"11\.\s+Gesti(ó|o)n del desempe(ñ|n)o"

    print(f"Buscando el inicio del capítulo 10 en '{pdf_path}'...")
    start_page = find_chapter_start(reader, chapter_10_pattern)

    if start_page == -1:
        print("Error: No se pudo encontrar el inicio del capítulo 10.", file=sys.stderr)
        print("Revisando el índice (si existe)...", file=sys.stderr)
        # Fallback: try to find it in the outline
        try:
            for dest in reader.outline:
                if isinstance(dest, list): # Check if it's a nested outline
                    for sub_dest in dest:
                         if "10" in sub_dest.title:
                            print(f"Found reference in outline: '{sub_dest.title}', page: {reader.get_destination_page_number(sub_dest)}")

                elif "10" in dest.title:
                    print(f"Found reference in outline: '{dest.title}', page: {reader.get_destination_page_number(dest)}")

        except Exception as e:
            print(f"No se pudo leer el índice: {e}", file=sys.stderr)

        sys.exit(1)

    print(f"Capítulo 10 encontrado en la página {start_page + 1}.")
    print("Extrayendo texto hasta el inicio del capítulo 11...")

    chapter_text = extract_chapter_text(reader, start_page, chapter_11_pattern)

    print("\n--- INICIO DEL TEXTO EXTRAÍDO DEL CAPÍTULO 10 ---")
    print(chapter_text)
    print("--- FIN DEL TEXTO EXTRAÍDO ---")


if __name__ == "__main__":
    main()
