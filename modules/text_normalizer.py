import re


class TextNormalizer:

    def __init__(self):
        pass

    # Legacy-font / OCR mojibake -> correct math symbol.
    # These are private-use-area code points that commonly appear when a
    # PDF's embedded Symbol-style font (used for the glyphs √, ×, ÷, ≤,
    # ≥, Δ, Ω, →) gets pulled out as plain text instead of being mapped
    # through its symbol encoding. The previous version of this file had
    # lines like text.replace("Ã—", "Ã—") where the "before" and "after"
    # strings were identical (corrupted during an earlier edit), so the
    # fix was silently doing nothing. This table maps the private-use
    # code points to the correct symbol.
    #
    # NOTE: the exact PUA code points that show up depend on the specific
    # font used in your PDFs. If you still see stray boxes/garbage
    # characters where a symbol should be after this fix, send a sample
    # and the mapping below can be extended.
    SYMBOL_FIXES = {
        "\uf0ae": "→",
        "\uf044": "Δ",
        "\uf057": "Ω",
        "\uf0b3": "≥",
        "\uf0a3": "≤",
        "\uf0d6": "√",
        "\uf0b4": "×",
        "\uf0b8": "÷",
    }

    # The combined Hindi+English OCR reader occasionally reads a Latin
    # digit using the Devanagari digit glyph instead (e.g. a question
    # numbered "29" coming out as "Q2९" - the "9" rendered as the
    # Devanagari numeral). Map Devanagari digits 0-9 to their ASCII
    # equivalents so this never surfaces in the output regardless of
    # which digit or how many appear in a run.
    DEVANAGARI_DIGITS = str.maketrans(
        "०१२३४५६७८९",
        "0123456789"
    )

    def normalize(self, text):

        if not text:
            return ""

        text = text.translate(self.DEVANAGARI_DIGITS)

        text = text.replace("\r", "\n")

        patterns = [
            r'Page\s+\d+',
            r'P\.?T\.?O\.?',
            r'CBSE.*?202\d',
            r'www\.cbse.*',
            r'Copyright.*',
            r'Turn Over',
            r'Contd\.*',
            r'Code No\..*',
            r'Set\s+\d+.*',
            r'\d+/\d+/\d+\s*#\s*\d*\s*\|\s*P\s*a\s*g\s*e',
            r'\d*\s*\|\s*P\s*a\s*g\s*e',
        ]

        for p in patterns:
            text = re.sub(
                p,
                '',
                text,
                flags=re.I
            )

        # Strip page-number footers like "1 / 23" ONLY when they occupy
        # an entire line by themselves. The old pattern (r'\d+\s*/\s*\d+')
        # matched ANY digit/digit anywhere in the text, which was quietly
        # deleting real maths fractions such as "3/4" inside questions -
        # a direct cause of mangled maths content.
        text = re.sub(
            r'(?m)^\s*\d{1,4}\s*/\s*\d{1,4}\s*$',
            '',
            text
        )

        # NOTE: a rule used to sit here that stripped any line containing
        # only digits, meant to catch stray page-number footers that
        # slipped past the more specific patterns above. It was removed:
        # MCQ option VALUES (e.g. the "25" in "(A) 25") very often sit
        # alone on their own text line in these PDFs, and that rule was
        # deleting them, leaving "(A)" with no value at all. Genuine
        # footer page numbers are already caught by the specific
        # patterns above, and (for native-text pages) filtered even
        # earlier in pdf_text_extractor.extract_lines().

        text = re.sub(
            r'(\w)-\n(\w)',
            r'\1\2',
            text
        )

        for bad, good in self.SYMBOL_FIXES.items():
            text = text.replace(bad, good)

        lines = []

        previous_blank = False

        for line in text.split("\n"):

            line = line.strip()

            if not line:

                if not previous_blank:
                    lines.append("")

                previous_blank = True

                continue

            previous_blank = False

            lines.append(line)

        text = "\n".join(lines)

        text = re.sub(
            r'[ \t]+',
            ' ',
            text
        )

        text = re.sub(
            r'\n{3,}',
            '\n\n',
            text
        )

        return text.strip()
