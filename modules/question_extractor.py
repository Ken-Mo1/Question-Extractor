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

            # BUG FIX: real CBSE papers very often DON'T print the word
            # "Marks" at all next to a question - just a bare number in
            # the margin, or a "1 x 3 = 3" style tag (question count x
            # marks-each = total). None of the patterns above match
            # either, so a confirmed real question like "...Explain
            # with example. 1x3=3" or "...Explain. 3" was coming back
            # with marks=None - which then fell through to the
            # instructions-page range lookup instead of using the far
            # more reliable number sitting right there on the question
            # itself. "1x3=3" / "1×3=3": take the total (third number).
            re.compile(r'\d+\s*[x\u00d7]\s*\d+\s*=\s*(\d+)\s*$', re.I),
            # A bare 1-2 digit number immediately after the question's
            # own closing punctuation (". 3", "? 2", etc) - anchored to
            # sentence-ending punctuation specifically so this can't
            # misfire on a number that's part of the question's actual
            # content (a date, a coordinate, an equation's answer).
            re.compile(r'(?<=[.?!])\s+(\d{1,2})\s*$'),

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
            (re.compile(r'very[\s\-]*short[\s\-]*answer|\bvsa\b', re.I), "Very Short Answer"),
            (re.compile(r'short[\s\-]*answer|\bsa\b', re.I), "Short Answer"),
            (re.compile(r'long\s+answer|\bla\b', re.I), "Long Answer"),
            (re.compile(r'map[\s\-]*based', re.I), "Map Based"),

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

        # Explicit "Question nos. X to Y are <type>, carrying N marks
        # each" statements, as CBSE instructions always state. Found by
        # testing against a real Social Science paper: unlike the Math
        # paper (which restates "consists of N questions of M marks
        # each" again on each section's own page, right after its
        # "SECTION - X" heading), this paper's marks/type wording
        # appears ONLY ONCE, on the instructions page - and since that
        # page has no "SECTION - X" heading of its own to anchor the
        # existing proximity filter, every question ended up defaulting
        # to whichever type/marks was mentioned LAST in the instructions
        # (the same contamination bug fixed for the Math paper, just
        # triggered a different way here).
        #
        # This is a more robust fix than another proximity filter: CBSE
        # instructions always spell out the exact question-number range
        # per section, so parse that directly and look up a question's
        # marks/type by its actual number - no guessing based on what
        # text happens to be nearby.
        self.question_range_pattern = re.compile(
            r'question\s*(?:numbers?|nos?\.?)\s*'
            r'(?:from\s+)?(\d+)\s*'
            r'(?:to|[-\u2013\u2014]|&|and)?\s*'
            r'(\d+)?',
            re.I
        )

    # ----------------------------------------------------

    def _parse_question_ranges(self, text):
        """
        Finds every "Question nos./number(s) X (to/and) Y ..." statement
        in `text` and returns a dict mapping each individual question
        number in that range to (marks, type) - whichever of those two
        it could find in the text immediately following the range (up
        to the next such statement, or ~300 characters, whichever comes
        first). Either value can be None if not found nearby; callers
        should treat a None as "no override, use the existing fallback
        logic" rather than as marks=None/type=None.
        """

        range_matches = list(self.question_range_pattern.finditer(text))

        ranges = {}

        for i, m in enumerate(range_matches):

            try:
                start_num = int(m.group(1))
            except (TypeError, ValueError):
                continue

            end_num = start_num

            if m.group(2):
                try:
                    end_num = int(m.group(2))
                except ValueError:
                    end_num = start_num

            if end_num < start_num or end_num - start_num > 40:
                # Sanity check: a real CBSE section never spans more
                # than ~40 questions. Guards against misreading two
                # unrelated numbers as a range.
                continue

            window_end = (
                range_matches[i + 1].start()
                if i + 1 < len(range_matches)
                else min(len(text), m.end() + 300)
            )

            window = text[m.end():window_end]

            marks = None

            marks_match = re.search(r'(\d+)\s*marks?\b', window, re.I)

            if marks_match:
                try:
                    marks = int(marks_match.group(1))
                except ValueError:
                    marks = None

            q_type = None

            for pattern, label in self.type_patterns:
                if pattern.search(window):
                    q_type = label
                    break

            for n in range(start_num, end_num + 1):
                ranges[n] = (marks, q_type)

        return ranges

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

        questions, updated_marks, updated_type, _, _ = self._extract_from_lines(
            lines, default_marks, default_type, apply_clean=True
        )

        for q in questions:
            q.pop("bbox", None)

        return questions, updated_marks, updated_type

    # ----------------------------------------------------

    def extract_questions_with_layout(
        self, lines, default_marks=None, default_type=None,
        default_last_number=None, known_ranges=None
    ):
        """
        Layout-aware entry point. `lines` is a list of (text, bbox)
        tuples as produced by PDFTextExtractor.extract_lines() - real
        PDF text with header/footer lines already removed. Each
        returned question dict includes a "bbox" key: (x0, y0, x1, y1)
        spanning every line that question's text occupies, in PDF
        points - used to screenshot that question directly from the
        page, and a "type" key (MCQ / Very Short Answer / Short Answer
        / Long Answer / Case Study / Assertion-Reason / Map Based).

        `default_last_number`, like default_marks/default_type, carries
        across pages: it's the last real question number accepted on
        the PREVIOUS page, used to catch the same wrapped-line false
        match (see _extract_from_lines) when it happens to be the
        FIRST match on a new page, where there's no prior match on
        that page alone to compare against.

        `known_ranges`, also carried across pages, is a dict of
        question_number -> (marks, type) parsed from explicit "Question
        nos. X to Y ... N marks each" statements (see
        _parse_question_ranges) - typically found once on the
        instructions page and reused for the rest of the PDF. Takes
        priority over the position-based nearest-mention heuristic when
        both are available for a given question.
        """

        return self._extract_from_lines(
            lines, default_marks, default_type, apply_clean=False,
            default_last_number=default_last_number,
            known_ranges=known_ranges
        )

    # ----------------------------------------------------

    def _extract_from_lines(
        self, lines, default_marks, default_type, apply_clean,
        default_last_number=None, known_ranges=None
    ):

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

        # Explicit "Question nos. X to Y are <type>, N marks each"
        # ranges, usually only stated once (on the instructions page)
        # but carried forward for the rest of this PDF - see
        # _parse_question_ranges for why this is more reliable than
        # the position-based heuristic below for papers that never
        # restate marks/type wording near the actual questions.
        known_ranges = dict(known_ranges or {})
        known_ranges.update(self._parse_question_ranges(text))

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

        raw_matches = list(self.question_pattern.finditer(text))

        # BUG FIX: a question that wraps onto a second line before any
        # option markers appear (common on "(A) ... OR (B) ..." style
        # questions) can end that first line with a number, e.g.
        # "...its first term is 15." - and since "15." then starts the
        # NEXT physical line, question_pattern (which matches at the
        # start of a line) mistook it for the start of a brand new
        # "Question 15", cutting the real question off right there.
        # This is exactly the confirmed truncation bug: Q29 lost its
        # second line and its marks label because of a stray "15." at
        # the start of line 2.
        #
        # Fix: real question numbers only increase down a page. Any
        # match whose number ISN'T greater than the previous accepted
        # question's number is almost certainly a stray number at the
        # start of a wrapped line, not a real question boundary -
        # reject it, and its text stays part of the question already
        # in progress instead of getting cut short.
        matches = []
        last_accepted_number = default_last_number

        for i, m in enumerate(raw_matches):

            try:
                n = int(m.group(1))
            except ValueError:
                continue

            if last_accepted_number is not None and n <= last_accepted_number:
                continue

            # BUG FIX: confirmed real case - a decorative bullet/border
            # symbol on a cover page got OCR'd as "6)", immediately
            # followed by a perfectly coherent English sentence (an
            # instruction bullet, not a question) - so the content-
            # quality check below can't catch it; it looks exactly like
            # real text. But every real CBSE paper's first actual
            # question is Q1, with no exceptions - so if this would be
            # the very first accepted match for the WHOLE PDF and it
            # isn't 1, it's not a real question boundary. Skip it and
            # keep looking rather than letting it permanently block the
            # real Q1-5 that come later (they'd all be <= this fake
            # number and rejected by the check above).
            if last_accepted_number is None and n != 1:
                continue

            # BUG FIX: a decorative bullet/border symbol on a cover
            # page (no real questions on it at all) got OCR'd as "6)"
            # and was accepted as a genuine "Question 6" - which then
            # permanently blocked every real Q1-5 later in the same
            # PDF, since they're all <= 6 and the check above rejects
            # anything that doesn't increase. The number-only check
            # can't tell a real question start from a stray OCR'd
            # symbol; peeking at what text actually follows the match
            # can. Real questions have real sentences after them -
            # this page's fake "6)" was followed by page-border noise.
            peek_end = (
                raw_matches[i + 1].start()
                if i + 1 < len(raw_matches)
                else min(len(text), m.end() + 200)
            )
            peek_text = text[m.end():peek_end]

            if not self.is_valid_question(peek_text):
                continue

            matches.append(m)
            last_accepted_number = n

        questions = []

        if not matches:
            updated_marks = (
                section_marks[-1][1] if section_marks else default_marks
            )
            updated_type = (
                section_types[-1][1] if section_types else default_type
            )
            return (
                questions, updated_marks, updated_type,
                last_accepted_number, known_ranges
            )

        for i, match in enumerate(matches):

            start = match.start()

            if i == len(matches) - 1:
                end = len(text)
            else:
                end = matches[i + 1].start()

            # BUG FIX: confirmed real case - Q29's block used to run
            # all the way to Q30's match, which meant it also absorbed
            # the "SECTION - D / (Long Answer Type Questions)..."
            # heading sitting between them. That pushed Q29's own real
            # trailing marks number ("...examples. 3") away from the
            # end of the block, so the end-anchored marks patterns
            # could no longer find it - the block's new end was the
            # section heading's "(4 x 5 = 20)" instead. A question's
            # content never legitimately continues past the next
            # section heading, so cap the block there too.
            heading_within = [
                h for h in section_heading_positions if start < h < end
            ]

            if heading_within:
                end = min(heading_within)

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

            range_marks, range_type = known_ranges.get(
                int(number) if number.isdigit() else -1, (None, None)
            )

            if marks is None:
                # Explicit "Question nos. X to Y ... N marks each"
                # ranges (see _parse_question_ranges) are the most
                # reliable source when available - they come straight
                # from the paper's own instructions, keyed by the
                # question's real number, rather than guessed from
                # whatever text happens to sit nearest it on the page.
                marks = (
                    range_marks
                    if range_marks is not None
                    else self._default_marks_for_position(
                        start, section_marks, default_marks
                    )
                )

            question_type = (
                range_type
                if range_type is not None
                else self._default_type_for_position(
                    start, section_types, default_type
                )
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

        return (
            questions, updated_marks, updated_type,
            last_accepted_number, known_ranges
        )

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