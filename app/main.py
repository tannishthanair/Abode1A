import os
import json
from pdf_parser import PDFParser
from outline_extractor import OutlineExtractor

INPUT_DIR = "/app/input"
OUTPUT_DIR = "/app/output"

def process_pdf(pdf_path, output_json_path):
    print(f"Processing {pdf_path}...")
    parser = PDFParser(pdf_path)
    if not parser.open_pdf():
        print(f"Failed to open PDF: {pdf_path}. Skipping.")
        return

    # text_blocks now contains line-level data with metadata
    text_blocks = parser.extract_blocks_with_metadata() 
    parser.close_pdf()

    extractor = OutlineExtractor()
    title, outline = extractor.extract_outline(text_blocks)

    output_data = {
        "title": title,
        "outline": outline
    }

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    print(f"Successfully processed {pdf_path} and saved outline to {output_json_path}")


if __name__ == "__main__":
    if not os.path.exists(INPUT_DIR):
        print(f"Input directory {INPUT_DIR} not found. Exiting.")
        exit(1)
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    pdf_files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith('.pdf')]

    if not pdf_files:
        print(f"No PDF files found in {INPUT_DIR}.")
    else:
        for pdf_file in pdf_files:
            pdf_path = os.path.join(INPUT_DIR, pdf_file)
            json_filename = os.path.splitext(pdf_file)[0] + '.json'
            output_json_path = os.path.join(OUTPUT_DIR, json_filename)
            process_pdf(pdf_path, output_json_path)