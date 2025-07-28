# import fitz  # PyMuPDF

# class PDFParser:
#     def __init__(self, pdf_path):
#         self.pdf_path = pdf_path
#         self.doc = None

#     def open_pdf(self):
#         try:
#             self.doc = fitz.open(self.pdf_path)
#         except Exception as e:
#             print(f"Error opening PDF {self.pdf_path}: {e}")
#             self.doc = None
#         return self.doc is not None

#     def close_pdf(self):
#         if self.doc:
#             self.doc.close()

#     def extract_blocks_with_metadata(self):
#         """
#         Extracts text lines with their font size, font name, and bounding box.
#         Aggregates spans into lines to better capture logical text units.
#         """
#         if not self.doc:
#             return []

#         all_lines_data = []
#         for page_num in range(self.doc.page_count):
#             page = self.doc.load_page(page_num)
#             text_dict = page.get_text("dict")
#             blocks = text_dict["blocks"]

#             for b in blocks:
#                 if b['type'] == 0:  # Text block
#                     for line in b['lines']:
#                         full_line_text = " ".join([span['text'] for span in line['spans']]).strip()
#                         if not full_line_text: # Skip empty lines
#                             continue

#                         # Get consistent font properties for the line from the first span
#                         # This assumes consistent styling within a line, which is usually true for headings.
#                         line_font_size = line['spans'][0]['size'] if line['spans'] else 0
#                         line_font_name = line['spans'][0]['font'] if line['spans'] else ''
                        
#                         all_lines_data.append({
#                             'text': full_line_text,
#                             'font_size': line_font_size,
#                             'font_name': line_font_name,
#                             'bbox': line['bbox'], # Bounding box of the entire line
#                             'page': page_num + 1 # Page numbers are 1-based
#                         })
#         return all_lines_data


import fitz  # PyMuPDF

class PDFParser:
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.doc = None

    def open_pdf(self):
        try:
            self.doc = fitz.open(self.pdf_path)
        except Exception as e:
            print(f"Error opening PDF {self.pdf_path}: {e}")
            self.doc = None
        return self.doc is not None

    def close_pdf(self):
        if self.doc:
            self.doc.close()

    def extract_blocks_with_metadata(self):
        """
        Extracts text lines with their font size, font name, and bounding box.
        Aggregates spans into lines and pre-computes 'is_bold' and 'font_name_lower' for efficiency.
        """
        if not self.doc:
            return []

        all_lines_data = []
        for page_num in range(self.doc.page_count):
            page = self.doc.load_page(page_num)
            text_dict = page.get_text("dict")
            blocks = text_dict["blocks"]

            for b in blocks:
                if b['type'] == 0:  # Text block
                    for line in b['lines']:
                        full_line_text = " ".join([span['text'] for span in line['spans']]).strip()
                        if not full_line_text:
                            continue

                        line_font_size = line['spans'][0]['size'] if line['spans'] else 0
                        line_font_name = line['spans'][0]['font'] if line['spans'] else ''
                        
                        # Pre-compute is_bold and font_name_lower ONCE here
                        font_name_lower = line_font_name.lower()
                        # Extended bold check
                        is_bold = 'bold' in font_name_lower or 'black' in font_name_lower or 'demi' in font_name_lower or 'heavy' in font_name_lower or 'condensed' in font_name_lower or 'extrabold' in font_name_lower or 'roman' not in font_name_lower # Add roman check here too [cite: 7]

                        all_lines_data.append({
                            'text': full_line_text,
                            'font_size': line_font_size,
                            'font_name': line_font_name, # Keep original font name
                            'font_name_lower': font_name_lower, # New: Lowercased font name
                            'is_bold': is_bold, # New: Pre-computed boolean
                            'bbox': line['bbox'],
                            'page': page_num + 1
                        })
        return all_lines_data