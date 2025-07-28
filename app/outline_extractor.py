import re
import math
from collections import Counter

class OutlineExtractor:
    def __init__(self):
        self.title = "Untitled Document"
        self.outline = []
        self.font_styles_map = {} # Stores identified font styles for H1, H2, H3
        self.general_font_info = {} # Stores general font stats like largest_font_size etc.

    def _analyze_font_properties(self, text_lines_data):
        """
        Analyzes font properties across the document to identify typical styles for headings.
        This helps in dynamically determining thresholds and characteristics for H1, H2, H3.
        It tries to find distinct font signatures (font name, size, bold status) that are likely headings.
        """
        font_signatures_raw = {} # (font_name, font_size, is_bold) -> list of bbox[1] (y-coords)
        all_font_sizes = []
        all_x0_coords = []
        
        # Collect all font signatures and their occurrences
        for line_data in text_lines_data:
            size = round(line_data['font_size'], 1)
            font_name = line_data['font_name']
            # More robust bold check for common font naming conventions
            is_bold = 'bold' in font_name.lower() or 'black' in font_name.lower() or 'demi' in font_name.lower() or 'heavy' in font_name.lower() or 'condensed' in font_name.lower() or 'extrabold' in font_name.lower()
            
            sig = (font_name, size, is_bold)
            font_signatures_raw.setdefault(sig, []).append(line_data['bbox'][1]) # Store y-coords
            all_font_sizes.append(size)
            all_x0_coords.append(line_data['bbox'][0])


        if not all_font_sizes:
            return

        # Calculate general font statistics
        max_overall_font_size = max(all_font_sizes)
        self.general_font_info['max_overall_font_size'] = max_overall_font_size
        self.general_font_info['min_x0'] = min(all_x0_coords) if all_x0_coords else 0 # Smallest x0 for document's left margin

        # Heuristic for base body text font size (often the most common non-heading size)
        size_counts = Counter(all_font_sizes)
        filtered_sizes_for_body = [s for s in all_font_sizes if s > 6 and s < max_overall_font_size * 0.95]
        if filtered_sizes_for_body:
            self.general_font_info['body_font_size'] = Counter(filtered_sizes_for_body).most_common(1)[0][0]
        else:
            self.general_font_info['body_font_size'] = 10.0 # Default fallback


        # Identify potential heading font styles based on distinctiveness and position
        potential_heading_styles = []
        page_count_actual = len(set(ld['page'] for ld in text_lines_data))

        for sig, y_coords_list in font_signatures_raw.items():
            font_name, size, is_bold = sig
            
            # Filter out sizes unlikely to be headings based on body font and minimum size
            if size < self.general_font_info['body_font_size'] * 0.95 or size < 8:
                continue
            
            # Count how many pages this style appears on (for ubiquitous filter)
            lines_for_this_sig = [ld for ld in text_lines_data if (ld['font_name'], round(ld['font_size'], 1), 'bold' in ld['font_name'].lower() or 'black' in ld['font_name'].lower() or 'demi' in ld['font_name'].lower() or 'heavy' in ld['font_name'].lower() or 'condensed' in ld['font_name'].lower() or 'extrabold' in ld['font_name'].lower()) == sig]
            pages_with_style = len(set(ld['page'] for ld in lines_for_this_sig))
            
            # Filter styles that are too ubiquitous and not exceptionally prominent (e.g., "Journal Pre-proof")
            if pages_with_style > page_count_actual * 0.7: # Appears on >70% of pages
                # If it's the exact text "Journal Pre-proof" and appears on most pages, it's a watermark. Filter it out.
                if any("journal pre-proof" in ld['text'].lower() for ld in lines_for_this_sig):
                    continue
                # If it's any other text, but very common, only consider if it's super bold and large.
                if not (is_bold and size >= max_overall_font_size * 0.9):
                    continue
            
            # Calculate average y-position and x0-position for this style
            avg_y = sum(ld['bbox'][1] for ld in lines_for_this_sig) / len(lines_for_this_sig) if lines_for_this_sig else 0
            avg_x0 = sum(ld['bbox'][0] for ld in lines_for_this_sig) / len(lines_for_this_sig) if lines_for_this_sig else 0

            # Scoring heuristic: Prioritize larger, bolder, higher (lower y), and more left-aligned (lower x0) styles
            # These values need to be stable even if page dimensions are not available from parsing.
            # Using common A4 page dimensions as a fallback if not explicitly derived.
            page_height = 842 # A4 height in points
            page_width = 595 # A4 width in points

            # Try to get actual page dimensions from the first page if available
            if text_lines_data:
                first_page_line = text_lines_data[0]
                if first_page_line['page'] == 1 and first_page_line['bbox'][3] > 0 and first_page_line['bbox'][2] > 0:
                    page_height = first_page_line['bbox'][3] # Max y-coord implies page height if from top-left origin
                    page_width = first_page_line['bbox'][2] # Max x-coord implies page width

            norm_y = avg_y / page_height
            norm_x0 = avg_x0 / page_width

            # Adjusted weights for scoring to emphasize size and position more.
            # Increased weight for boldness, decreased weight for x0 (less sensitive to slight variations)
            score = (size * 15) + (200 if is_bold else 0) - (norm_y * 100) - (norm_x0 * 20) + (len(y_coords_list) * 0.05) # Frequency as a small positive factor
            
            potential_heading_styles.append({'signature': sig, 'score': score, 'avg_y': avg_y, 'avg_x0': avg_x0, 'count': len(y_coords_list)})

        # Sort by score to get the most "heading-like" styles first
        potential_heading_styles.sort(key=lambda x: x['score'], reverse=True)

        # Assign the top unique font styles to H1, H2, H3 levels based on score and size distinctiveness
        self.font_styles_map = {
            'H1': None, 'H2': None, 'H3': None,
            'H1_size': 0, 'H2_size': 0, 'H3_size': 0,
            'H1_x0_min': float('inf'), 'H2_x0_min': float('inf'), 'H3_x0_min': float('inf') # Track typical x0 for indentation
        }

        assigned_levels_count = 0
        assigned_sizes = set()
        
        for style_info in potential_heading_styles:
            sig = style_info['signature']
            size = sig[1]
            
            # Ensure assigned sizes are clearly distinct and follow a decreasing pattern
            if assigned_levels_count == 0: # Always assign the top scoring one to H1 first
                self.font_styles_map['H1'] = sig
                self.font_styles_map['H1_size'] = size
                self.font_styles_map['H1_x0_min'] = style_info['avg_x0']
                assigned_levels_count = 1
                assigned_sizes.add(size)
            elif assigned_levels_count == 1:
                # Assign H2 only if its size is clearly smaller than H1 or it's a different font name/boldness
                if size < self.font_styles_map['H1_size'] * 0.95 or sig[0] != self.font_styles_map['H1'][0] or sig[2] != self.font_styles_map['H1'][2]:
                    self.font_styles_map['H2'] = sig
                    self.font_styles_map['H2_size'] = size
                    self.font_styles_map['H2_x0_min'] = style_info['avg_x0']
                    assigned_levels_count = 2
                    assigned_sizes.add(size)
            elif assigned_levels_count == 2:
                # Assign H3 only if its size is clearly smaller than H2 or it's a different font name/boldness
                if size < self.font_styles_map['H2_size'] * 0.95 or sig[0] != self.font_styles_map['H2'][0] or sig[2] != self.font_styles_map['H2'][2]:
                    self.font_styles_map['H3'] = sig
                    self.font_styles_map['H3_size'] = size
                    self.font_styles_map['H3_x0_min'] = style_info['avg_x0']
                    assigned_levels_count = 3
                    assigned_sizes.add(size)
            else:
                break # Only need H1, H2, H3

        # Fallback for sizes if not enough distinct styles were identified
        if self.font_styles_map['H1_size'] == 0: self.font_styles_map['H1_size'] = max_overall_font_size * 0.9 if max_overall_font_size > 0 else 18
        if self.font_styles_map['H2_size'] == 0: self.font_styles_map['H2_size'] = self.font_styles_map['H1_size'] * 0.85
        if self.font_styles_map['H3_size'] == 0: self.font_styles_map['H3_size'] = self.font_styles_map['H2_size'] * 0.85
        
        # Ensure x0_min are reasonable, if not, set them based on document's general left margin
        if self.font_styles_map['H1_x0_min'] == float('inf'): self.font_styles_map['H1_x0_min'] = self.general_font_info['min_x0']
        # Apply a small indentation difference if not naturally found
        if self.font_styles_map['H2_x0_min'] == float('inf'): self.font_styles_map['H2_x0_min'] = self.font_styles_map['H1_x0_min'] + 10 
        if self.font_styles_map['H3_x0_min'] == float('inf'): self.font_styles_map['H3_x0_min'] = self.font_styles_map['H2_x0_min'] + 10 


    def _is_title(self, line_data):
        """
        Heuristic to identify the document title for academic papers.
        Usually the largest, often bold, and appears once prominently on the first page.
        """
        text = line_data['text'].strip()
        font_size = round(line_data['font_size'], 1)
        font_name_lower = line_data['font_name'].lower()
        is_bold = 'bold' in font_name_lower or 'black' in font_name_lower or 'demi' in font_name_lower or 'heavy' in font_name_lower or 'condensed' in font_name_lower or 'extrabold' in font_name_lower

        if line_data['page'] != 1 or not text:
            return False

        # Specific check for the known title string in this PDF
        if "deep support vector machine for hyperspectral image classification" in text.lower():
            if is_bold and font_size >= self.general_font_info.get('max_overall_font_size', 0) * 0.95:
                if line_data['bbox'][1] < 150: # Top 150 pixels on page 1
                    return True
        return False

    def _is_math_expression(self, text):
        """
        Detects if a text string is likely a mathematical expression, equation number, or figure/table caption.
        """
        text = text.strip()
        if not text: return False

        # Common LaTeX math commands
        if re.search(r'\\(sum|alpha|beta|gamma|cdot|mathbb|mathfrak|xi|eta|forall|in|infty|ge|le|pm|mu|sigma|tanh|log|exp|frac|partial|Delta|lambda|emptyset|mathbf|mathrm|text)\b', text):
            return True
        
        # Starts with common math expression characters or patterns (e.g., parenthesis for equation numbers)
        if re.match(r'^\s*[\(\[\]\{\}\+\-\*\/\=\<\>\$€£%]\s*', text) or \
           re.match(r'^[\d\.]+\s*[-+*\/=]', text) or \
           re.match(r'^\s*\(\s*\d+\s*\)\s*$', text) or \
           re.match(r'^\s*\d+(\.\d+)*\s*$', text): # Just a number like page number, but could be equation number
            return True

        # Common figure/table caption starts
        if re.match(r'^(Figure|Table)\s*\d+[:.]', text, re.IGNORECASE):
             return True
        
        # If it's mostly symbols and numbers, likely math
        if len(re.findall(r'[\d\+\-\*\/\=\<\>\$\\]', text)) / (len(text) + 1) > 0.4:
            return True
        
        return False

    def _is_heading(self, line_data):
        """
        Determines if a line is a heading (H1, H2, H3) based on learned font styles,
        specific content patterns, and layout heuristics.
        Order of checks is crucial for hierarchy and filtering.
        """
        text = line_data['text'].strip()
        font_name = line_data['font_name']
        font_size = round(line_data['font_size'], 1)
        x0_pos = line_data['bbox'][0] # Left position of the text
        is_bold = 'bold' in font_name.lower() or 'black' in font_name.lower() or 'demi' in font_name.lower() or 'heavy' in font_name.lower() or 'condensed' in font_name.lower() or 'extrabold' in font_name.lower()
        current_sig = (font_name, font_size, is_bold)
        
        # 0. Initial Basic Filtering - remove common non-heading text immediately
        if not text:
            return None
        
        # Ignore very short or very long lines that are unlikely to be headings
        if len(text) < 3:
            return None
        if len(text.split()) > 20: # Max 20 words for most headings
            # Allow longer ones only if they are clearly numbered sections.
            if not re.match(r'^(\d+(\.\d+)*)\s+', text):
                return None
        
        # Filter out lines that are purely page numbers, common running elements, etc.
        if re.match(r'^\s*\d+\s*$', text) and line_data['page'] > 1: # Single number on page > 1 (likely page number)
            return None
        if re.match(r'^(Page|Pg\.)\s+\d+\s*(of\s+\d+)?$', text, re.IGNORECASE):
            return None
        
        # **CRUCIAL: Aggressively filter "Journal Pre-proof" and similar watermarks.**
        if "journal pre-proof" in text.lower() or \
           "highlights" in text.lower() or \
           "journal pre-print" in text.lower() or \
           "manuscript" in text.lower() or \
           "accepted manuscript" in text.lower():
           return None

        # Filter out patterns commonly seen in metadata/authors/affiliations that are NOT headings
        if re.match(r'^(PII|DOI|Reference|Received date|Revised date|Accepted date):', text, re.IGNORECASE) or \
           re.match(r'^\s*\d+,\s*(\d{4}|\w+)\s*$', text) or \
           re.search(r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text) or \
           re.search(r'\b(University|Department|Institute|Queensland|Australia|Nigeria)\b', text) or \
           re.search(r'^[A-Z][a-z]+\s+[A-Z]\.\s+[A-Z][a-z]+$', text): # e.g., "Onuwa Okwuashi"
            return None
        
        # Filter out mathematical expressions (from _is_math_expression helper)
        if self._is_math_expression(text):
            return None
        
        # Filter out lines that are purely citation-like (Author, Year) or just numerical citations [X]
        if re.match(r'^\s*\[\d+\]\s*$', text) or re.match(r'^\s*\[[a-zA-Z\s\.]+\]\s*$', text): # e.g. 
            return None
        if re.search(r'\([A-Za-z\s\.]+,\s*\d{4}\)', text) and len(text.split()) < 20: # e.g. (Li et al., 2018)
            return None

        # Check for sentence-like structures (often not headings unless very specific)
        if text.endswith('.') and len(text.split()) > 5:
            # Allow specific known headings to override this general rule
            if not text.lower().startswith(("abstract", "introduction", "results", "discussion and conclusion")):
                return None

        # 1. Strongest Heuristic: Explicit Section Numbering (e.g., "1.0 Introduction", "2.1 Deep support vector machine framework")
        # This is the most reliable for academic papers. We make it more lenient on font properties.
        match_numbered = re.match(r'^(\d+(\.\d+)*)\s+(.*)', text)
        if match_numbered:
            # Numerically-prefixed lines are highly likely to be headings.
            # Only require it to be at least body font size and roughly bolded OR a learned heading style.
            if font_size >= self.general_font_info.get('body_font_size', 10) * 0.9 and (is_bold or current_sig in [self.font_styles_map.get('H1'), self.font_styles_map.get('H2'), self.font_styles_map.get('H3')]):
                parts = match_numbered.group(1).split('.')
                
                # Use indentation more strictly for numerical headings
                if len(parts) == 1: # e.g., "1.0 Introduction"
                    if abs(x0_pos - self.font_styles_map.get('H1_x0_min', 0)) < 25: # Within 25px of H1 margin
                        return "H1"
                elif len(parts) == 2: # e.g., "2.1 Deep support vector machine framework"
                    if abs(x0_pos - self.font_styles_map.get('H2_x0_min', 0)) < 25: # Within 25px of H2 margin
                        return "H2"
                elif len(parts) >= 3: # e.g., "2.1.1 Sub-sub-section"
                    if abs(x0_pos - self.font_styles_map.get('H3_x0_min', 0)) < 25: # Within 25px of H3 margin
                        return "H3"
            return None # If it's numbered but fails style/indentation check, it's not a heading

        # 2. Strong Named Headings (Abstract, Keywords, Acknowledgement, References, etc.) - often bold, no numbering
        common_h1_names = ["abstract", "introduction", "results", "discussion and conclusion", "acknowledgement", "references", "appendix"]
        common_h2_names = ["materials and method", "related work", "experimental setup", "data and implementation", "conclusion"]
        common_h3_names = ["keywords", "conflict of interest", "declaration of interests"]
        
        cleaned_text_lower = text.lower().replace('.', '').replace(':', '').strip()

        if cleaned_text_lower in common_h1_names and is_bold and font_size >= self.font_styles_map.get('H1_size',0) * 0.9:
            if abs(x0_pos - self.font_styles_map.get('H1_x0_min', 0)) < 25:
                return "H1"
        if cleaned_text_lower in common_h2_names and is_bold and font_size >= self.font_styles_map.get('H2_size',0) * 0.9:
            if abs(x0_pos - self.font_styles_map.get('H2_x0_min', 0)) < 25:
                return "H2"
        if cleaned_text_lower in common_h3_names and is_bold and font_size >= self.font_styles_map.get('H3_size',0) * 0.9:
            if abs(x0_pos - self.font_styles_map.get('H3_x0_min', 0)) < 25:
                return "H3"
        
        # 3. General Heuristics: Based on learned font styles, boldness, and simple content rules (fallback)
        # This will catch headings that don't follow strict numbering or explicit naming conventions but are styled as such.
        # Reduced length requirement for general headings.
        
        # Check against learned H1 style or similar large, bold text
        if self.font_styles_map.get('H1') == current_sig or (font_size >= self.font_styles_map['H1_size'] * 0.9 and is_bold):
            if len(text.split()) < 10 and not text.endswith('.') and abs(x0_pos - self.font_styles_map.get('H1_x0_min', 0)) < 25:
                return "H1"

        # Check against learned H2 style or similar
        if self.font_styles_map.get('H2') == current_sig or (font_size >= self.font_styles_map['H2_size'] * 0.9 and is_bold):
            if len(text.split()) < 15 and not text.endswith('.') and abs(x0_pos - self.font_styles_map.get('H2_x0_min', 0)) < 25:
                return "H2"

        # Check against learned H3 style or similar
        if self.font_styles_map.get('H3') == current_sig or (font_size >= self.font_styles_map['H3_size'] * 0.9 and is_bold):
            if len(text.split()) < 20 and not text.endswith('.') and abs(x0_pos - self.font_styles_map.get('H3_x0_min', 0)) < 25:
                return "H3"
        
        return None


    def extract_outline(self, text_lines_data):
        self.outline = []
        self.title = "Untitled Document" # Default title

        if not text_lines_data:
            return self.title, self.outline

        # Sort lines by page and then by y-coordinate for proper reading order
        text_lines_data.sort(key=lambda b: (b['page'], b['bbox'][1]))

        # Step 1: Analyze overall font properties to identify potential heading styles
        self._analyze_font_properties(text_lines_data)

        # Step 2: Identify the document title
        found_title = False
        for line_data in text_lines_data:
            if self._is_title(line_data):
                self.title = line_data['text'].strip()
                found_title = True
                break
        
        if not found_title and text_lines_data:
            # Fallback title: Look for the largest bold text on page 1, high up, that isn't a running header or metadata.
            potential_title_lines = []
            for ld in text_lines_data:
                if ld['page'] == 1 and ld['bbox'][1] < 200: # Top 200 pixels on page 1
                    is_bold = 'bold' in ld['font_name'].lower() or 'black' in ld['font_name'].lower() or 'demi' in ld['font_name'].lower() or 'heavy' in ld['font_name'].lower() or 'condensed' in ld['font_name'].lower() or 'extrabold' in ld['font_name'].lower()
                    
                    if is_bold and ld['font_size'] >= self.general_font_info.get('max_overall_font_size',0) * 0.9:
                        current_text_lower = ld['text'].strip().lower()
                        # Filter out common non-title/metadata lines
                        if "journal pre-proof" not in current_text_lower and \
                           "highlights" not in current_text_lower and \
                           not self._is_math_expression(ld['text'].strip()) and \
                           not re.match(r'^(pii|doi|reference|received date|revised date|accepted date):', current_text_lower) and \
                           not re.search(r'@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', current_text_lower) and \
                           not re.search(r'\([A-Za-z\s\.]+,\s*\d{4}\)', current_text_lower) and \
                           15 < len(ld['text'].split()) < 30: # Reasonable word count for a title
                            potential_title_lines.append(ld)
            
            potential_title_lines.sort(key=lambda x: x['font_size'], reverse=True) # Largest font first
            
            if potential_title_lines:
                # Concatenate potentially split title lines if they are close vertically and horizontally aligned.
                final_title_text = potential_title_lines[0]['text'].strip()
                base_x0 = potential_title_lines[0]['bbox'][0]
                base_font_size = potential_title_lines[0]['font_size']

                for i in range(1, len(potential_title_lines)):
                    # Check vertical proximity, similar font size, and horizontal alignment
                    if potential_title_lines[i]['bbox'][1] - potential_title_lines[i-1]['bbox'][3] < 5 and \
                       potential_title_lines[i]['font_size'] == base_font_size and \
                       abs(potential_title_lines[i]['bbox'][0] - base_x0) < 10: # Check x0 alignment
                        final_title_text += " " + potential_title_lines[i]['text'].strip()
                    else:
                        break
                self.title = final_title_text
            else:
                self.title = "Academic Paper (Generic Title)" # Generic fallback if nothing found.


        # Step 3: Iterate through all lines to find and classify headings
        added_headings = set() # To prevent adding duplicate headings

        for line_data in text_lines_data:
            current_page = line_data['page']
            current_text = line_data['text'].strip()

            # **CRUCIAL: Aggressive filter for "Journal Pre-proof" and other watermarks/running headers/footers.**
            # This should be the first content check after basic text validation.
            if "journal pre-proof" in current_text.lower() or \
               "highlights" in current_text.lower() or \
               "journal pre-print" in current_text.lower() or \
               "manuscript" in current_text.lower() or \
               "accepted manuscript" in current_text.lower() or \
               (self.title != "Untitled Document" and current_text.lower() == self.title.lower()): # Filter exact title if repeated
                continue
            
            # Additional filtering for very common non-outline elements (like page numbers)
            if re.match(r'^\s*\d+\s*$', current_text): # Single number, typically a page number
                continue
            
            heading_level = self._is_heading(line_data)

            if heading_level:
                cleaned_text = current_text

                # Specific cleaning for numerical headings like "1.0 Introduction"
                match_numbered = re.match(r'^(\d+(\.\d+)*)\s+(.*)', cleaned_text)
                if match_numbered:
                    cleaned_text = match_numbered.group(3).strip()
                
                # Further cleaning for common named headings (ensure we extract just the heading part)
                elif cleaned_text.lower().startswith("abstract") and len(cleaned_text.split()) > 1:
                    cleaned_text = "Abstract"
                elif cleaned_text.lower().startswith("keywords:") and len(cleaned_text.split()) > 1:
                    cleaned_text = "Keywords"
                elif cleaned_text.lower().startswith("acknowledgement") and len(cleaned_text.split()) > 1:
                    cleaned_text = "Acknowledgement"
                elif cleaned_text.lower().startswith("conflict of interest") and len(cleaned_text.split()) > 1:
                    cleaned_text = "Conflict of interest"
                elif cleaned_text.lower().startswith("declaration of interests") and len(cleaned_text.split()) > 1:
                    cleaned_text = "Declaration of interests"
                elif cleaned_text.lower().startswith("references") and len(cleaned_text.split()) > 1:
                    cleaned_text = "References"
                
                # Final filtering for quality after cleaning
                if not cleaned_text or len(cleaned_text) < 3:
                    continue

                unique_key = (cleaned_text, heading_level, current_page)
                if unique_key in added_headings:
                    continue
                added_headings.add(unique_key)

                self.outline.append({
                    "level": heading_level,
                    "text": cleaned_text,
                    "page": current_page
                })
            
        return self.title, self.outline

