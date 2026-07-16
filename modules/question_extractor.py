import re


class QuestionExtractor:

    def __init__(self):

        # Accepts:
        # 1.
        # 1)
        # 1 :
        # 10.
        # 38)
        #
        # IMPORTANT: the separator must be followed by REAL whitespace
        # (\s+, not \s*). With \s* this pattern was also matching things
        # like "10.15" (a time, e.g. "10.15 a.m.") or "2:1" (a ratio) at
        # the start of a text-extraction line, because nothing requires
        # a space between the "." and what follows. Those false matches
        # were turning random fragments of the instructions/cover pages
        # into fake "questions". Requiring \s+ after the separator fixes
        # this while still matching every real "12. Some question text".
        self.question_pattern = re.compile(
            r'(?m)^\s*(\d{1,2})\s*[\.\):]\s+'
        )

        # CBSE marks formats.
        #
        # NOTE: three patterns that used to be here -
        #   \((\d)\)$   \[(\d)\]$   \s(\d)\s*$
        # - matched ANY trailing digit with no requirement that it mean
        # "marks" at all. On an MCQ block ending in "... (D) 8", that
        # matched the "8" from option (D) and reported it as the
        # question's marks value. Real marks are now only recognised
        # when the word "Marks" actually appears; everything else falls
        # back to the section-level default (see section_marks_pattern
        # below and _default_marks_for_position).
        self.marks_patterns = [

            re.compile(r'\[(\d)\s*Marks?\]', re.I),
            re.compile(r'\((\d)\s*Marks?\)', re.I),
            re.compile(r'(\d)\s*Marks?$', re.I),
            re.compile(r'Marks?\s*[:\-]?\s*(\d)', re.I),

        ]

        # Real CBSE papers usually do NOT tag every individual MCQ/short
        # question with "[1 Mark]" - instead a section header states it
        # once: "carrying 3 marks each", "of 1 mark each", etc. This
        # pattern catches those statements so we can use them as a
        # fallback default whenever a question has no per-question tag.
        self.section_marks_pattern = re.compile(
            r'(?:carrying|of)\s+(\d+)\s*marks?\s*each',
            re.I
        )

        # CBSE papers state each section's question TYPE in its own
        # words too ("Very Short Answer (VSA-I) type questions",
        # "Multiple Choice Questions (MCQs)", "Case study based
        # questions", etc). Matched in priority order - first match
        # wins - since some phrases are substrings of others.
        self.type_patterns = [

            (re.compile(r'assertion\s*[-\u2013\u2014]?\s*reason', re.I), "Assertion-Reason"),
            (re.compile(r'case[\s\-]*(study|based)', re.I), "Case Study"),
            (re.compile(r'source[\s\-]*based', re.I), "Case Study"),
            (re.compile(r'multiple\s+choice|\bmcqs?\b', re.I), "MCQ"),
            (re.compile(r'very\s+short\s+answer|\bvsa\b', re.I), "Very Short Answer"),
            (re.compile(r'short\s+answer|\bsa\b', re.I), "Short Answer"),
            (re.compile(r'long\s+answer|\bla\b', re.I), "Long Answer"),

        ]

        # Fallback when a page has no recognisable section-type wording
        # at all (e.g. the question is on a page by itself with no
        # visible section header). Matches standard CBSE marks-per-type
        # convention - not exact for every subject, but a reasonable
        # default for a label whose only job is grouping in the export.
        self.MARKS_TYPE_FALLBACK = {

            1: "MCQ",
            2: "Very Short Answer",
            3: "Short Answer",
            4: "Case Study",
            5: "Long Answer",

        }

    # ----------------------------------------------------

    def clean(self, text):

        if not text:
            return ""

        text = text.replace("\r", "\n")

        # Remove headers/footers only
        text = re.sub(r'Page\s+\d+.*', '', text, flags=re.I)
        text = re.sub(r'P\.?T\.?O\.?', '', text, flags=re.I)

        # Preserve line breaks
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)

        return text.strip()

    # ----------------------------------------------------

    def extract_marks(self, block):

        for pattern in self.marks_patterns:

            m = pattern.search(block)

            if m:

                marks = int(m.group(1))

                block = pattern.sub("", block).strip()

                return marks, block

        return None, block

    # ----------------------------------------------------

    def normalize(self, block):

        # Preserve OR, options, assertion reason etc.
        block = re.sub(r'[ \t]+', ' ', block)

        block = re.sub(r'\n +', '\n', block)

        return block.strip()

    # ----------------------------------------------------

    def is_valid_question(self, block):

        if len(block.strip()) < 8:
            return False

        # Don't reject maths/equation questions
        letters = len(re.findall(r'[A-Za-z]', block))

        digits = len(re.findall(r'\d', block))

        symbols = len(re.findall(r'[=+\-×÷/%√πΣ∆≤≥<>°()]', block))

        return (letters + digits + symbols) >= 8

    # ----------------------------------------------------

    def extract_questions(self, text, default_marks=None, default_type=None):
        """
        Backward-compatible entry point for callers with no position
        data (this is the OCR fallback path - OCR output has no bbox
        information to offer). Treats the whole text as ordinary lines
        with bbox=None, and strips the "bbox" key back out of the
        result so existing callers see exactly the same shape as
        before.
        """

        lines = [(line, None) for line in text.split("\n")]

        questions, updated_marks, updated_type = self._extract_from_lines(
            lines, default_marks, default_type, apply_clean=True
        )

        for q in questions:
            q.pop("bbox", None)

        return questions, updated_marks, updated_type

    # ----------------------------------------------------

    def extract_questions_with_layout(
        self, lines, default_marks=None, default_type=None
    ):
        """
        Layout-aware entry point. `lines` is a list of (text, bbox)
        tuples as produced by PDFTextExtractor.extract_lines() - real
        PDF text with header/footer lines already removed. Each
        returned question dict includes a "bbox" key: (x0, y0, x1, y1)
        spanning every line that question's text occupies, in PDF
        points - used to screenshot that question directly from the
        page, and a "type" key (MCQ / Very Short Answer / Short Answer
        / Long Answer / Case Study / Assertion-Reason).
        """

        return self._extract_from_lines(
            lines, default_marks, default_type, apply_clean=False
        )

    # ----------------------------------------------------

    def _extract_from_lines(self, lines, default_marks, default_type, apply_clean):

        # Join the lines into one string for regex matching, while
        # recording the exact (start, end, bbox) span of each line
        # within that exact string. Nothing between here and the
        # matching loop below is allowed to change the string's length,
        # or these offsets would drift out of sync with their bboxes.
        joined_parts = []
        line_spans = []

        pos = 0

        for line_text, bbox in lines:

            start = pos

            joined_parts.append(line_text)

            pos += len(line_text)

            line_spans.append((start, pos, bbox))

            pos += 1  # for the "\n" joiner below

        text = "\n".join(joined_parts)

        if apply_clean:
            # Only safe when there is no bbox info to preserve (the
            # OCR-fallback path) - clean() changes the string's length.
            text = self.clean(text)

        section_marks = [
            (m.start(), int(m.group(1)))
            for m in self.section_marks_pattern.finditer(text)
        ]

        # Same bug, same fix as section_types below: the General
        # Instructions page states EVERY section's marks value
        # ("...of 1 mark each... carrying 3 marks each... carrying 5
        # marks each...") in one block before Q1. Without filtering,
        # "the last marks statement before this question" picks up
        # whatever was mentioned last in that preview instead of the
        # value that actually applies to the question's own section.
        section_heading_positions = [
            m.start()
            for m in re.finditer(r'SECTION\s*[-\u2013\u2014]\s*[A-E]\b', text, re.I)
        ]

        if section_heading_positions:
            section_marks = [
                (pos, marks) for pos, marks in section_marks
                if any(pos > h for h in section_heading_positions)
            ]

        section_types = []

        for pattern, label in self.type_patterns:
            for m in pattern.finditer(text):
                section_types.append((m.start(), label))

        section_types.sort(key=lambda item: item[0])

        # BUG FIX: a real CBSE paper's General Instructions page lists
        # every section's type ("Multiple Choice Questions... 19 & 20
        # are Assertion-Reason... VSA... SA... LA... Case Study...")
        # all in one block, BEFORE the first actual question (Q1). The
        # old logic picked "the last type keyword seen before this
        # question" - and on that page, EVERY keyword precedes Q1, so
        # it always grabbed the LAST one mentioned in the instructions
        # (Case Study, since Section E is described last) regardless
        # of what Q1 actually was. That wrong type then carried forward
        # as the default through every MCQ until Section B's own real
        # heading finally overrode it - which is why every MCQ (Q1-18)
        # was coming out labeled "Case Study" instead of "MCQ".
        #
        # Fix: only trust a type keyword if it appears AFTER a real
        # "SECTION - <letter>" heading, not from the instructions
        # preview. Real section bodies always have this heading
        # immediately before their type description; the instructions
        # preamble does not.
        if section_heading_positions:
            section_types = [
                (pos, label) for pos, label in section_types
                if any(pos > h for h in section_heading_positions)
            ]

        matches = list(self.question_pattern.finditer(text))

        questions = []

        if not matches:
            updated_marks = (
                section_marks[-1][1] if section_marks else default_marks
            )
            updated_type = (
                section_types[-1][1] if section_types else default_type
            )
            return questions, updated_marks, updated_type

        for i, match in enumerate(matches):

            start = match.start()

            if i == len(matches) - 1:
                end = len(text)
            else:
                end = matches[i + 1].start()

            block = text[start:end].strip()

            number = match.group(1)

            # Remove question number
            block = re.sub(
                r'^\s*\d{1,2}\s*[\.\):]\s+',
                '',
                block,
                count=1
            )

            marks, block = self.extract_marks(block)

            if marks is None:
                marks = self._default_marks_for_position(
                    start, section_marks, default_marks
                )

            question_type = self._default_type_for_position(
                start, section_types, default_type
            )

            if question_type is None and marks in self.MARKS_TYPE_FALLBACK:
                question_type = self.MARKS_TYPE_FALLBACK[marks]

            block = self.normalize(block)

            if not self.is_valid_question(block):
                continue

            question_dict = {

                "question_no": number,

                "marks": marks,

                "type": question_type,

                "question": block,

                "bbox": self._bbox_for_span(start, end, line_spans)

            }

            questions.append(question_dict)

        updated_marks = (
            section_marks[-1][1] if section_marks else default_marks
        )

        updated_type = (
            section_types[-1][1] if section_types else default_type
        )

        return questions, updated_marks, updated_type

    # ----------------------------------------------------

    def _bbox_for_span(self, start, end, line_spans):
        """
        Returns the union bbox (x0, y0, x1, y1) of every line whose
        character span overlaps [start, end), or None if no line in
        this range has real position data (e.g. the OCR fallback path,
        or a page that genuinely has no positioned lines).
        """

        x0 = y0 = None
        x1 = y1 = None

        for line_start, line_end, bbox in line_spans:

            if bbox is None:
                continue

            if line_end <= start or line_start >= end:
                continue

            lx0, ly0, lx1, ly1 = bbox

            x0 = lx0 if x0 is None else min(x0, lx0)
            y0 = ly0 if y0 is None else min(y0, ly0)
            x1 = lx1 if x1 is None else max(x1, lx1)
            y1 = ly1 if y1 is None else max(y1, ly1)

        if x0 is None:
            return None

        return (x0, y0, x1, y1)

    # ----------------------------------------------------

    def _default_marks_for_position(self, position, section_marks, carried_default):
        """
        Returns the marks value from the most recent "carrying X marks
        each" statement that appears BEFORE this question's position on
        THIS page; falls back to the value carried forward from a
        previous page if this page has no such statement of its own.
        """

        applicable = [
            marks for pos, marks in section_marks if pos <= position
        ]

        if applicable:
            return applicable[-1]

        return carried_default

    # ----------------------------------------------------

    def _default_type_for_position(self, position, section_types, carried_default):
        """
        Same idea as _default_marks_for_position, for question type.
        """

        applicable = [
            label for pos, label in section_types if pos <= position
        ]

        if applicable:
            return applicable[-1]

        return carried_default