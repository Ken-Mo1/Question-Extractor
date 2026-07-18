import re
import time
import traceback

import fitz

from modules.pdf_converter import PDFConverter
from modules.question_extractor import QuestionExtractor
from modules.database import Database
from modules.pdf_text_extractor import PDFTextExtractor
from modules.metadata_extractor import MetadataExtractor
from modules.chapter_mapper import ChapterMapper
from modules.duplicate_detector import DuplicateDetector
from modules.text_normalizer import TextNormalizer
from modules.image_extractor import ImageExtractor


class PDFProcessor:

    def __init__(self, ocr_engine, pipeline_version=None):

        # Stamped onto every row this instance inserts - lets the app
        # detect when the on-screen table / export is secretly a mix of
        # this run and an older, incompatible extraction logic (see
        # Database.get_stale_pipeline_summary()).
        self.pipeline_version = pipeline_version

        self.converter = PDFConverter()

        self.text_extractor = PDFTextExtractor()

        self.extractor = QuestionExtractor()

        self.metadata = MetadataExtractor()

        self.chapter_mapper = ChapterMapper()

        self.duplicate = DuplicateDetector()

        self.normalizer = TextNormalizer()

        self.image_extractor = ImageExtractor()

        self.db = Database()

        self.ocr = ocr_engine

        self._current_default_marks = None

        self._current_default_type = None

        self._current_last_question_number = None

        self._current_known_ranges = None

    # -------------------------------------------------------
    # Strip page-footer noise from OCR output
    # -------------------------------------------------------

    def _is_footer_line(self, text):
        """
        True for lines that are page-footer furniture rather than
        question content: the QP code repeated on every page (e.g.
        "32/6/2"), "P.T.O.", or a lone page number. These need to be
        filtered out of OCR results before question-matching, or they
        get appended to whichever question happens to be last on the
        page - confirmed pushing a real trailing marks tag out of reach
        of the end-anchored patterns in extract_marks().
        """

        stripped = text.strip()

        if not stripped:
            return True

        if re.fullmatch(r'\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{1,2}', stripped):
            return True

        if re.search(r'P\.?\s*T\.?\s*O\.?', stripped, re.I) and len(stripped) < 40:
            return True

        if re.fullmatch(r'\d{1,3}', stripped):
            return True

        # QP code + page number + P.T.O. often OCR onto one combined
        # line (e.g. "32/6/2 3 i P.T.O.") - catch that combined form
        # too, not just each piece in isolation.
        if re.search(r'\d{1,2}\s*/\s*\d{1,2}\s*/\s*\d{1,2}', stripped) and \
                re.search(r'P\.?\s*T\.?\s*O', stripped, re.I):
            return True

        return False

    # -------------------------------------------------------
    # Determine whether embedded PDF text is good enough
    # -------------------------------------------------------

    def should_use_ocr(self, text):

        if not text:
            return True

        text = text.strip()

        if len(text) < 150:
            return True

        english = len(re.findall(r"[A-Za-z]", text))

        digits = len(re.findall(r"\d", text))

        total = len(text)

        if total == 0:
            return True

        english_ratio = english / total

        if english_ratio < 0.12 and digits < 30:
            return True

        return False

    # -------------------------------------------------------
    # Reject pages that are clearly Hindi-only
    # -------------------------------------------------------

    def is_english_page(self, text):

        if not text:

            return False

        english = len(re.findall(r"[A-Za-z]", text))

        hindi = len(re.findall(r"[\u0900-\u097F]", text))

        private_use = sum(

            1

            for ch in text

            if 0xE000 <= ord(ch) <= 0xF8FF

        )

        total = len(text)

        if total < 25:
            return False

        if private_use > total * 0.10:
            return False

        if english >= hindi:

            return True

        if english > 100:

            return True

        return False

    # -------------------------------------------------------
    # Process one page
    # -------------------------------------------------------

    def process_page(
        self,
        doc,
        pdf_name,
        page_number,
        metadata,
        rows
    ):
        # Legacy (non-Unicode) Hindi fonts extract as Latin-looking
        # gibberish, not Devanagari, so a plain character check can
        # mistake them for English. Catch this by font name FIRST,
        # before any text-based check runs.
        if self.text_extractor.uses_legacy_hindi_font(doc, page_number):
            return 0, "legacy_hindi_font", {"needs_ocr": False, "render_s": 0.0, "ocr_s": 0.0}

        lines = self.text_extractor.extract_lines(doc, page_number)

        flat_text = "\n".join(text for text, _ in lines).strip()

        hidden_vector_text = self.text_extractor.has_hidden_vector_text(
            doc, page_number
        )

        # NOTE: there used to be a "confidently non-English, skip OCR
        # entirely" shortcut here. It assumed any page with vector-
        # outlined text was always the Hindi half of a bilingual page.
        # That assumption broke on a real paper where the ENTIRE
        # document (English included) is vector-outlined with no real
        # text layer at all - every single page tripped the shortcut,
        # OCR never ran once, and the result was 0 questions from 0 of
        # 24 pages. Removed: a page with hidden vector text now always
        # goes through OCR (see `needs_ocr` below); is_english_page(),
        # which runs AFTER OCR on the real OCR'd text, is what decides
        # whether to keep or discard it. Slower on true Hindi-only
        # pages, but correct on every paper regardless of how it was
        # generated - which matters more than the speed here.

        # "native": bboxes are in PDF points, straight from the PDF.
        # "ocr": bboxes are in pixel coordinates of the rendered page
        # PNG (this page had no usable embedded text, e.g. a scanned
        # page or - as seen on some real CBSE PDFs - one where every
        # character is drawn as its own vector outline rather than
        # actual text).
        source = "native"
        rendered_image_path = None

        needs_ocr = self.should_use_ocr(flat_text) or hidden_vector_text

        timing = {"needs_ocr": needs_ocr, "render_s": 0.0, "ocr_s": 0.0}

        if needs_ocr:

            t_render = time.perf_counter()

            rendered_image_path = self.converter.render_page(
                doc, pdf_name, page_number
            )

            timing["render_s"] = time.perf_counter() - t_render

            ocr_lines, ocr_elapsed, ocr_is_english, ocr_script_conf = (
                self.ocr.read_lines_with_boxes(rendered_image_path)
            )

            timing["ocr_s"] = ocr_elapsed
            timing["ocr_is_english"] = ocr_is_english
            timing["ocr_script_confidence"] = ocr_script_conf

            # BUG FIX: the page footer (QP code like "32/6/2", a lone
            # page number, "P.T.O.") was getting OCR'd as ordinary text
            # lines and tacked onto whatever question happened to be
            # LAST on that page - since that question's block runs to
            # the end of the page's text with nothing to bound it.
            # Confirmed: this pushed a real trailing marks tag ("...the
            # country. 3") out from the end of the block, past a chunk
            # of footer noise, so the end-anchored marks patterns could
            # no longer find it. Native-text extraction already strips
            # these (see PDFTextExtractor); OCR output needs the same
            # treatment before it reaches question-matching.
            ocr_lines = [
                (t, b) for t, b in ocr_lines
                if not self._is_footer_line(t)
            ]

            ocr_text = "\n".join(text for text, _ in ocr_lines)

            # should_use_ocr() already decided the native text wasn't
            # good enough - trust that decision and use the OCR result,
            # rather than re-comparing raw character counts. A blank
            # (missing font/cmap) page still contains whitespace and
            # stray surviving labels/digits, which can make it LONGER
            # than a correctly-OCR'd short result and win a naive
            # length comparison, even though the OCR text is the real
            # content and the native text is near-garbage. Only keep
            # native text if OCR came back essentially empty.
            if len(ocr_text.strip()) >= 20:
                lines = ocr_lines
                flat_text = ocr_text
                source = "ocr"
            # else: OCR produced almost nothing useful - keep the
            # native `lines` from above as a last resort.

        if not flat_text:
            return 0, "no_text_after_extraction", timing

        # The OCR engine runs English-only (see ocr_engine.py) - it
        # never outputs real Devanagari text for a Hindi page, just
        # low-quality Latin noise, so counting Devanagari Unicode
        # characters (is_english_page's old signal) can't distinguish
        # a Hindi page from an English one here. Use OCR confidence
        # instead when this page came from OCR: measured ~44 avg on a
        # real Hindi page vs ~91 on a real English page - a wide,
        # reliable gap. Native-text pages (no OCR involved) keep the
        # original character-ratio check.
        if source == "ocr":
            if not timing.get("ocr_is_english", False):
                return 0, "not_english", timing
        elif not self.is_english_page(flat_text):
            return 0, "not_english", timing

        (
            questions,
            self._current_default_marks,
            self._current_default_type,
            self._current_last_question_number,
            self._current_known_ranges,
        ) = self.extractor.extract_questions_with_layout(
            lines,
            self._current_default_marks,
            self._current_default_type,
            self._current_last_question_number,
            self._current_known_ranges,
        )

        if not questions:
            return 0, "no_questions_matched", timing

        extracted = 0

        for q in questions:

            question = q["question"].strip()

            if len(question) < 10:
                continue

            # Text is only used internally now (chapter classification,
            # dedup hashing, in-app search) - the deliverable is the
            # screenshot below. Still worth a light cleanup since a
            # cleaner string makes chapter keyword-matching more
            # reliable.
            question = self.normalizer.normalize(question)

            bbox = q.get("bbox")

            # Every question gets screenshotted directly from the page -
            # this is the point of the screenshot-based approach: no
            # more guessing whether a question "needs" an image, since
            # the image IS the question as far as the reader is
            # concerned.
            if bbox:

                if source == "native":

                    image_path = self.image_extractor.crop_region(
                        doc, pdf_name, page_number,
                        bbox[1], bbox[3], q["question_no"]
                    )

                else:

                    image_path = self.image_extractor.crop_region_from_image(
                        rendered_image_path, pdf_name, page_number,
                        bbox[1], bbox[3], q["question_no"]
                    )

            else:
                # No position data at all (shouldn't normally happen -
                # every path above provides bboxed lines - but fail
                # safe rather than crash).
                image_path = None

            chapter = self.chapter_mapper.predict(
                question,
                metadata["subject"]
            )

            question_hash = self.duplicate.hash(
                question
            )

            rows.append(
                (
                    metadata["year"],
                    metadata["subject"],
                    metadata["paper_set"],
                    metadata["paper_code"],
                    metadata["language"],
                    pdf_name,
                    page_number + 1,
                    q["question_no"],
                    q["marks"],
                    q.get("type"),
                    chapter,
                    question_hash,
                    question,
                    str(image_path) if image_path else None,
                    self.pipeline_version
                )
            )

            extracted += 1

        if extracted == 0:
            # Every candidate question on this page failed the
            # length/validity check inside the loop above.
            return 0, "questions_matched_but_all_invalid", timing

        return extracted, "ok", timing

    # -------------------------------------------------------
    # Process complete PDF
    # -------------------------------------------------------

    def process_pdf(self, pdf, override_year=None, on_page_done=None):
        """
        `on_page_done`, if given, is called after EVERY page (success,
        skip, or crash) as on_page_done(page_number_1_indexed,
        total_pages, count, reason, timing). This exists so the caller
        (app.py) can show a live progress bar / status line that
        updates after each page, instead of the UI appearing frozen for
        the whole run - especially important now that a page needing
        OCR can take real, visible time on a CPU-only machine.
        """

        metadata = self.metadata.extract(pdf, override_year=override_year)

        # Reset per-PDF state: these carried-forward defaults must not
        # leak from one paper into the next.
        self._current_default_marks = None
        self._current_default_type = None
        self._current_last_question_number = None
        self._current_known_ranges = None

        # Open the PDF ONCE and share it across every page - text
        # extraction, font inspection, and (if needed) rendering.
        # The previous version opened a fresh fitz.Document for every
        # single page via PDFTextExtractor, which was a major slowdown
        # on multi-page PDFs and multi-PDF ZIP batches.
        doc = fitz.open(pdf)

        rows = []

        total_questions = 0

        total_pages = len(doc)

        processed_pages = 0

        skipped_pages = 0

        # Counts of WHY a page contributed 0 questions, e.g.
        # {"not_english": 20, "no_questions_matched": 3}. An "error:..."
        # key means the page raised an exception - see `errors` below
        # for the full traceback. Kept separate from ordinary skip
        # reasons on purpose: a page correctly identified as Hindi and a
        # page that crashed both used to show up as one indistinguishable
        # "skipped" number, which is exactly what made a 24-for-24
        # failure look identical to a normal bilingual-paper run.
        skip_reasons = {}

        # Full detail for any page that raised an exception - page
        # number, the exception message, and the full traceback. Shown
        # in the app (see app.py), not just printed to a console the
        # person running this may never look at.
        errors = []

        # Aggregated timing, so a slow run can be diagnosed with real
        # numbers instead of another guess - see WHAT_CHANGED.md's
        # explicit warning against guessing further. Answers "is this
        # slow because of OCR itself, or something else?" directly.
        pages_ocrd = 0
        total_ocr_s = 0.0
        total_render_s = 0.0
        total_pdf_s = 0.0

        # Every question number actually captured, across every page of
        # this PDF - used below to report GAPS (e.g. "6, 7, and 9 were
        # never found") instead of letting a page with a diagram-heavy
        # MCQ or a stubborn OCR misread just silently produce fewer
        # questions with no visible signal that anything is missing.
        found_question_numbers = set()

        try:

            for page_number in range(total_pages):

                t_page = time.perf_counter()

                try:

                    rows_before = len(rows)

                    count, reason, timing = self.process_page(
                        doc,
                        pdf.name,
                        page_number,
                        metadata,
                        rows
                    )

                    for row in rows[rows_before:]:
                        found_question_numbers.add(row[7])

                    if timing.get("needs_ocr"):
                        pages_ocrd += 1
                        total_ocr_s += timing.get("ocr_s", 0.0)
                        total_render_s += timing.get("render_s", 0.0)

                    if count > 0:

                        processed_pages += 1

                        total_questions += count

                    else:

                        skipped_pages += 1

                        skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

                except Exception as e:

                    tb = traceback.format_exc()

                    print(
                        f"[WARNING] Failed to process page "
                        f"{page_number + 1} of {pdf.name}: {e}\n{tb}"
                    )

                    skipped_pages += 1

                    reason = f"error: {e}"

                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1

                    errors.append(
                        {
                            "page": page_number + 1,
                            "error": str(e),
                            "traceback": tb,
                        }
                    )

                    count = 0

                page_elapsed = time.perf_counter() - t_page

                total_pdf_s += page_elapsed

                if on_page_done:
                    on_page_done(
                        page_number + 1,
                        total_pages,
                        count,
                        reason,
                        page_elapsed
                    )

        finally:

            doc.close()

        # -----------------------------------------------
        # Bulk insert into database
        # -----------------------------------------------

        if rows:

            self.db.insert_questions(rows)

        # -----------------------------------------------
        # Final statistics
        # -----------------------------------------------

        inserted_questions = self.db.total_questions()

        # Report GAPS in the question-number sequence, e.g. this PDF's
        # highest found number is 38 but 1, 5, and 22 never appeared
        # anywhere - almost certainly a real question that got missed
        # (OCR near a diagram, a misread digit, etc), not one that was
        # never in the paper. Best-effort only: numeric question
        # numbers (skips "22(A)"-style labels), and only meaningful
        # once at least a few questions were found.
        missing_question_numbers = []

        numeric_found = set()

        for q in found_question_numbers:
            try:
                numeric_found.add(int(str(q).strip()))
            except (TypeError, ValueError):
                continue

        if numeric_found:

            highest = max(numeric_found)

            missing_question_numbers = [
                n for n in range(1, highest + 1) if n not in numeric_found
            ]

        return {

            "pages": total_pages,

            "processed_pages": processed_pages,

            "skipped_pages": skipped_pages,

            "questions": total_questions,

            "database_total": inserted_questions,

            "skip_reasons": skip_reasons,

            "errors": errors,

            "total_seconds": total_pdf_s,

            "pages_ocrd": pages_ocrd,

            "total_ocr_seconds": total_ocr_s,

            "total_render_seconds": total_render_s,

            "missing_question_numbers": missing_question_numbers,

        }
