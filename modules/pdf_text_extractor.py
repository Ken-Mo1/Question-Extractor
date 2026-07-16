import re
import fitz


# Known legacy (pre-Unicode) Hindi fonts commonly used in CBSE question
# papers. Text typed in these fonts is stored in the PDF using ordinary
# Latin/ASCII code points - each Devanagari glyph is mapped onto a Latin
# letter for display purposes. That means when this text is extracted
# "as text" it does NOT come out as Devanagari Unicode (\u0900-\u097F);
# it comes out as meaningless Latin-looking gibberish that easily gets
# mistaken for English by character-based checks. The font name is the
# only reliable signal that a page like this is actually Hindi.
LEGACY_HINDI_FONT_MARKERS = (
    "kruti",
    "devlys",
    "chanakya",
    "shusha",
    "walkman",
    "agra",
    "amar",
    "dvb",
)

# Lines matching any of these are running headers/footers (page numbers,
# "P.T.O.", the QP-code footer, "SET~n" banners, etc). They are dropped
# at line-assembly time - BEFORE any offset is assigned to a line - so
# they can never end up glued onto a question, and so nothing downstream
# has to re-clean the text in a way that would shift character offsets
# out of sync with each line's page position.
_FOOTER_LINE_PATTERNS = [
    re.compile(r'^\s*p\.?\s*t\.?\s*o\.?\s*$', re.I),
    re.compile(r'^\s*page\s+\d+', re.I),
    re.compile(r'^\s*\d+\s*\|\s*p\s*a\s*g\s*e\s*$', re.I),
    re.compile(r'^\s*\d+/\d+/\d+\s*#?\s*$'),
    re.compile(r'^\s*set\s*[~\-]?\s*\d+\s*$', re.I),
    re.compile(r'^\s*series\b', re.I),
]


def _is_footer_line(text):
    stripped = text.strip()

    if not stripped:
        return False

    for pattern in _FOOTER_LINE_PATTERNS:
        if pattern.search(stripped):
            return True

    return False


class PDFTextExtractor:
    """
    Extracts embedded text from PDF pages.

    `doc` is a fitz.Document that the caller (PDFProcessor) opens ONCE
    per PDF and passes in for every page, instead of the old behaviour
    of calling fitz.open() again for every single page (a major
    performance bottleneck on multi-page / multi-PDF batches).
    """

    def extract_text(self, doc, page_number):

        lines = self.extract_lines(doc, page_number)

        return "\n".join(text for text, _ in lines).strip()

    def extract_lines(self, doc, page_number):
        """
        Returns a list of (line_text, bbox) tuples for this page, in
        top-to-bottom / left-to-right reading order, with running
        header/footer lines already removed. `bbox` is (x0, y0, x1, y1)
        in PDF points - this is what lets ImageExtractor know which
        pixel band on the page a given question occupies.
        """

        page = doc.load_page(page_number)

        raw = page.get_text("dict", sort=True)

        lines = []

        for block in raw.get("blocks", []):

            if block.get("type") != 0:
                # type 1 = image block, not text - skip
                continue

            for line in block.get("lines", []):

                spans = line.get("spans", [])

                if not spans:
                    continue

                text = "".join(span.get("text", "") for span in spans)

                if not text.strip():
                    continue

                if _is_footer_line(text):
                    continue

                x0 = min(span["bbox"][0] for span in spans)
                y0 = min(span["bbox"][1] for span in spans)
                x1 = max(span["bbox"][2] for span in spans)
                y1 = max(span["bbox"][3] for span in spans)

                lines.append((text, (x0, y0, x1, y1)))

        return lines

    def has_hidden_vector_text(self, doc, page_number):
        """
        Detects a specific failure mode found on real CBSE PDFs: content
        (usually the Hindi half of a bilingual page) rendered as vector
        line-art instead of real text, while other content on the SAME
        page (digits, option labels, stray Latin characters) is real,
        extractable text.

        should_use_ocr() judges "is the text I already have good
        enough?" - but on a page like this, what little text DOES
        survive (numbers, "(A)(B)(C)(D)", odd Latin labels) can look
        perfectly sufficient on its own, even though the actual
        sentence-level content is completely missing. This check looks
        for the tell-tale sign instead: a large number of tiny,
        character-sized vector paths (the outlined glyphs) that don't
        correspond to nearly as much real extracted text as they should.
        """

        page = doc.load_page(page_number)

        try:
            drawings = page.get_drawings()
        except Exception:
            return False

        glyph_like = sum(
            1
            for d in drawings
            if d.get("rect")
            and d["rect"].width < 20
            and d["rect"].height < 20
        )

        # Calibrated against real samples: pages with genuine embedded
        # text (even lots of it) show single digits to low tens of these
        # (decorative lines, a diagram's construction lines); pages with
        # vector-outlined Hindi paragraphs show hundreds.
        return glyph_like > 100

    def uses_legacy_hindi_font(self, doc, page_number):
        """
        Returns True if this page's text is set in a known legacy
        (non-Unicode) Hindi font. Pages like this should be treated as
        Hindi and skipped immediately, even though their raw extracted
        text looks like English/Latin gibberish rather than Devanagari.
        """

        try:
            fonts = doc.get_page_fonts(page_number)
        except Exception:
            return False

        for font in fonts:
            font_info = " ".join(str(part) for part in font).lower()

            for marker in LEGACY_HINDI_FONT_MARKERS:
                if marker in font_info:
                    return True

        return False
