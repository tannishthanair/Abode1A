# Abode1A
This project implements the Round 1 challenge to extract a structured outline (Title, H1, H2, H3) from PDF documents and output them in a specified JSON format.

## Approach

Our solution employs a heuristic-based approach combined with advanced layout analysis and rule-based Natural Language Processing (NLP) techniques to identify document titles and hierarchical headings from raw PDF content. We explicitly avoid large, pre-trained machine learning models to comply with the size and offline execution constraints.

The core logic resides in `outline_extractor.py`, supported by `pdf_parser.py` for efficient data extraction:

1.  **Robust PDF Parsing (`pdf_parser.py`):**
    * Leverages `PyMuPDF` (Fitz) to extract text line-by-line, along with critical metadata such as font size, font name, and bounding box coordinates (`bbox`).
    * **Performance Optimization:** Key properties like `is_bold` (based on font name heuristics) and `font_name_lower` are pre-computed during parsing and injected into each line's data dictionary. This significantly reduces redundant string operations in downstream processing.

2.  **Advanced Layout Analysis (`outline_extractor.py - _analyze_font_properties`):**
    * Performs a single-pass analysis of all text lines to understand the document's overall font landscape.
    * Identifies the most prominent font styles (combinations of font name, size, and bold status) that are strong candidates for headings (H1, H2, H3) and determines typical font sizes and horizontal alignment (x0 position) for each level.
    * Calculates the average body text font size to dynamically set relative thresholds for headings.
    * **Document Type Inference:** Attempts to determine if the document is an "academic paper" (e.g., presence of numbered sections, "Abstract", "References") or a "general document/flyer." This flag (`has_academic_patterns`) guides subsequent filtering logic.

3.  **Robust Title Extraction (`outline_extractor.py - _find_document_title`):**
    * Specifically targets Page 1 to find the most prominent text that qualifies as a title.
    * Scores potential title lines based on font size, boldness, and vertical position.
    * Applies a set of general filters to exclude common non-title elements like page numbers, watermarks, metadata (DOI, PII), author names, and common flyer labels (e.g., "FOR:").
    * Includes logic to concatenate multi-line titles that are visually and stylistically cohesive.
    * The `title` defaults to an empty string (`""`) if no definitive title is found, as per some expected outputs.

4.  **Hierarchical Heading Detection (`outline_extractor.py - _is_heading`):**
    * This is the core heuristic engine for classification. It combines multiple cues in a prioritized manner:
        * **Aggressive Initial Filtering:** Removes watermarks ("Journal Pre-proof"), page numbers, and other non-heading content very early based on precise regex patterns and content.
        * **Vertical Spacing Analysis:** Calculates the vertical gap between lines. Headings are often preceded by significant white space, acting as a strong indicator.
        * **Prioritized Numbered Headings (Rule-Based NLP):** Uses highly reliable regular expressions (e.g., `1.0 Introduction`, `2.1 Sub-section`) to identify and classify H1, H2, H3 based on the numbering depth and a lenient check on font size/boldness/alignment.
        * **Strong Named Headings (Rule-Based NLP):** Identifies common academic section titles (e.g., "Abstract", "Introduction", "References") and assigns them H1, H2, or H3 based on common conventions and visual cues (boldness, alignment, font size).
        * **General Visual Headings (Fallback):** For less structured documents (like flyers), a fallback rule catches very large, bold, short phrases with significant vertical spacing, classifying them as H1. This handles prominent visual elements that aren't formal headings (e.g., "HOPE TO SEE YOU THERE!").
        * **Dynamic Filtering:** Filters (e.g., for math expressions, author affiliations, citations) are applied conditionally based on the `has_academic_patterns` flag, preventing over-filtering for non-academic documents.
    * **Cleaning:** Extracted heading text is cleaned to remove numerical prefixes or extraneous content.

## Models or Libraries Used

* **PyMuPDF (Fitz):** Used for efficient PDF parsing and extraction of text content along with detailed layout information (font size, font name, bounding box coordinates).
* **Python's `re` module:** Extensively used for regular expression matching to identify structural patterns (numbered headings, specific keywords) and filter out unwanted content.
* **Python's `collections.Counter`:** Used for frequency analysis of font sizes to infer body text and overall prominent font sizes.

**No external machine learning models (e.g., pre-trained NLP models like transformers, spaCy models) are used, ensuring compliance with the ≤ 200MB model size and offline execution constraints.** The solution relies purely on rule-based heuristics and statistical analysis of document layout properties.

**Project Structure:**

adobe-hackathon/
├── Dockerfile
├── app/
│   ├── main.py
│   ├── pdf\_parser.py
│   ├── outline\_extractor.py
│   └── requirements.txt
├── input/         \<-- Place your input PDF files here
├── output/        \<-- Output JSON files will be generated here
└── README.md

````

**Steps:**

1.  **Navigate to your Project Root:**
    Open your terminal (e.g., MINGW64) and navigate to the `adobe-hackathon/` directory. This directory should contain your `Dockerfile`, `app/`, `input/`, and `output/` folders.

2.  **Ensure `input` and `output` Directories Exist:**
    If they don't already exist, create empty `input` and `output` directories in your project root:
    ```bash
    mkdir -p input
    mkdir -p output
    ```

3.  **Place Input PDFs:**
    Copy your test PDF files into the `adobe-hackathon/input/` directory.

4.  **Build the Docker Image:**
    This command will build your solution's Docker image and tag it. This step compiles your application code into a Docker image.

    ```bash
    docker build --platform linux/amd64 -t mysolutionname:somerandomidentifier .
    ```
    * `--platform linux/amd64`: Specifies the target architecture (as required by the hackathon).
    * `-t mysolutionname:somerandomidentifier`: Tags the image with a name and identifier. **You must use this exact tag in the next step.**

5.  **Run the Docker Container:**
    This command will run your solution inside a Docker container, mounting your local `input` and `output` folders so the container can read and write files. It also disables network access to comply with the "offline" constraint.

    ```bash
    docker run --rm -v "$(pwd)/input:/app/input" -v "$(pwd)/output:/app/output" --network none mysolutionname:somerandomidentifier
    ```
    * `--rm`: Automatically removes the container after execution for cleanup.
    * `-v "$(pwd)/input:/app/input"`: Mounts your host's `input` directory to `/app/input` inside the container.
    * `-v "$(pwd)/output:/app/output"`: Mounts your host's `output` directory to `/app/output` inside the container.
    * `--network none`: Ensures no external network calls are made.
    * `mysolutionname:somerandomidentifier`: The exact name and tag of the image you built in the previous step.

**Expected Output:**

Upon successful execution, the console will display messages indicating the processing of each PDF. You will find corresponding `.json` files in your `adobe-hackathon/output/` directory, each containing the extracted document title and hierarchical outline.
````
