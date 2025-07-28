# Adobe India Hackathon - Connecting the Dots: Round 1

## Challenge Theme: Understand Your Document - Extracting Structured Outlines

This project implements the Round 1 challenge to extract a structured outline (Title, H1, H2, H3) from PDF documents and output them in a specified JSON format.

## Approach

Our solution leverages a heuristic-based approach combined with robust PDF parsing to identify document titles and headings.

1.  **PDF Parsing (using PyMuPDF):**
    * The `pdf_parser.py` module uses `PyMuPDF` (Fitz) to open PDF documents and extract text blocks along with rich metadata such as font size, font name, bounding box coordinates, and page numbers. [cite_start]This detailed information is crucial for accurately distinguishing headings from body text.
    * We specifically focus on `span` level details to get precise font information for each text segment.

2.  **Heading Detection (Heuristic-based):**
    * [cite_start]The `outline_extractor.py` module employs a set of heuristics to identify titles and headings without relying on external NLP models or internet access, adhering to the competition constraints[cite: 59, 60, 61, 62].
    * **Font Size Analysis:** We analyze the distribution of font sizes across the document to infer potential heading levels. Generally, larger font sizes indicate higher-level headings (e.g., Title > H1 > H2 > H3). [cite_start]While not the sole factor (as per contest tip ), it's a primary indicator.
    * **Positional and Contextual Clues:** We consider the position of text blocks (e.g., text at the top of a page is more likely a title or H1).
    * **Text Patterns:** Regular expressions are used to identify common heading patterns like numbered sections (e.g., "1. Introduction", "2.1 Sub-section").
    * **Content Filtering:** Short strings (e.g., page numbers, common headers/footers) and purely numeric text are filtered out to reduce false positives.
    * **Cleaning:** Extracted heading text is cleaned to remove numbering or leading symbols.
    * **Hierarchical Inference:** The algorithm attempts to infer the hierarchical level (H1, H2, H3) based on the derived font size thresholds and the order of appearance.

3.  **Output Generation:**
    * The `main.py` script orchestrates the process. [cite_start]It reads PDF files from `/app/input`, processes them, and writes the extracted outline to a corresponding JSON file in `/app/output`, following the specified format[cite: 43].

## Models or Libraries Used

* **PyMuPDF (Fitz):** For efficient PDF parsing and text/metadata extraction. No external ML models are used. The solution relies entirely on rule-based heuristics.

## How to Build and Run Your Solution

This section is for documentation purposes. [cite_start]The evaluation will use the commands specified in the "Expected Execution" section of the challenge document[cite: 61, 62, 63, 64, 65, 66, 67].

### Building the Docker Image

Navigate to the root directory of this project (`adobe/`) and execute the following command:

```bash
docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .