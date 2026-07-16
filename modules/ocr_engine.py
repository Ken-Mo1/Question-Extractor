import os
import time

import cv2
import pytesseract

# Windows doesn't put Tesseract on PATH automatically the way Linux/Mac
# package managers do, so pytesseract can't find the tesseract.exe
# binary unless told exactly where it is. Point it at the standard
# Windows install location if that's where it actually is; on
# Linux/Mac (where `tesseract` is normally already on PATH after
# `apt install tesseract-ocr` / `brew install tesseract`), leave
# pytesseract's default alone.
_WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

if os.name == "nt" and os.path.exists(_WINDOWS_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = _WINDOWS_TESSERACT_PATH


class OCREngine:
    """
    Tesseract-based OCR engine. Replaces the previous EasyOCR engine,
    which measured at ~93 SECONDS PER PAGE on CPU on a real 24-page
    paper (2231s total) - EasyOCR's deep-learning-per-word design is
    built for GPU throughput and is punishing on CPU-only hardware,
    and no amount of image downscaling or denoising-removal closes
    that gap; it's the recognition engine itself that's slow.

    Tesseract was measured on the SAME real 24-page paper at ~1-3
    SECONDS PER PAGE (44-84s total depending on settings) - a ~30-50x
    speedup - with comparable text quality on the pages that were
    actually English.

    KEY DESIGN CHOICE: run English-only ('eng'), not a combined
    Hindi+English model. Two concrete, measured reasons:

    1. Speed: combined-language models are slower per page than a
       single language.
    2. Accuracy: a combined hi+en model was measured corrupting digits
       in ENGLISH text it should have read cleanly - e.g. "18" -> a
       Devanagari-look-alike glyph, "35" -> "85" - because it was
       spending recognition probability mass considering Devanagari
       shapes for every character, including ones that were plainly
       Latin digits. Forcing 'eng' only removes that ambiguity for the
       English pages we actually care about.

    This means we get NO real Hindi text back for Hindi pages - eng-
    only OCR run against Devanagari script just produces low-quality
    Latin noise. That's fine and intentional: this pipeline only ever
    keeps English pages, so Hindi text was always being discarded
    anyway. What we DO need is a reliable way to tell "this page is
    Hindi, skip it" apart from "this page is English, keep it" -
    that's what `confidence` is for (see read_lines_with_boxes below):
    measured avg confidence on a real Hindi page was ~44, vs ~91 on a
    real English page from the same document - a wide, reliable gap.
    PDFProcessor uses this instead of counting Devanagari Unicode
    characters (which would always be near-zero here, since eng-only
    OCR doesn't output real Devanagari text).
    """

    # Below this average per-word confidence (0-100, as reported by
    # Tesseract), a page is treated as non-English and skipped rather
    # than fed through question-matching. Measured gap: ~44 on a real
    # Hindi page vs ~91 on a real English page from the same paper -
    # this threshold sits well clear of both.
    ENGLISH_CONFIDENCE_THRESHOLD = 65

    # DPI-equivalent target for the image handed to Tesseract. Kept
    # high (unlike the old engine's downscaling) because Tesseract's
    # classical (non-neural) recognizer is fast regardless, and higher
    # resolution meaningfully helps it read small math symbols and
    # option labels correctly - there's no speed reason to shrink it.
    MAX_OCR_WIDTH = 2600

    def __init__(self):
        # Nothing to load - unlike EasyOCR, Tesseract has no model
        # weights to read into memory, so there's no startup cost to
        # cache/avoid either.
        pass

    def _load_for_ocr(self, image_path):

        img = cv2.imread(str(image_path))

        if img is None:
            raise ValueError(f"Could not read image at {image_path}")

        h, w = img.shape[:2]

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        gray = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            15
        )

        scale = 1.0

        if w > self.MAX_OCR_WIDTH:

            scale = self.MAX_OCR_WIDTH / w

            new_size = (self.MAX_OCR_WIDTH, max(1, int(round(h * scale))))

            gray = cv2.resize(gray, new_size, interpolation=cv2.INTER_AREA)

        return gray, scale

    def read_lines_with_boxes(self, image_path):
        """
        Returns (lines, elapsed_seconds, avg_confidence).

        `lines` = list of (text, bbox) in PIXEL coordinates of the
        ORIGINAL image at `image_path` (scaled back up if internal
        downscaling happened). `avg_confidence` = mean Tesseract word
        confidence (0-100) across every recognized word on the page -
        see the class docstring for why this replaces Devanagari
        character-counting as the English/Hindi page signal.

        Groups Tesseract's word-level boxes into visual lines by
        vertical position (same approach as before) rather than
        trusting Tesseract's own paragraph grouping, so tightly-packed
        MCQ lines stay separate instead of merging.
        """

        t0 = time.perf_counter()

        image, scale = self._load_for_ocr(image_path)

        data = pytesseract.image_to_data(
            image,
            lang="eng",
            config="--psm 6",
            output_type=pytesseract.Output.DICT
        )

        words = []
        confidences = []

        n = len(data["text"])

        for i in range(n):

            text = data["text"][i]

            if not text or not text.strip():
                continue

            conf = int(data["conf"][i]) if data["conf"][i] not in ("-1", -1) else -1

            if conf < 0:
                continue

            confidences.append(conf)

            x0 = data["left"][i]
            y0 = data["top"][i]
            x1 = x0 + data["width"][i]
            y1 = y0 + data["height"][i]

            words.append({
                "text": text,
                "x0": x0, "y0": y0,
                "x1": x1, "y1": y1,
            })

        avg_confidence = (
            sum(confidences) / len(confidences) if confidences else 0.0
        )

        lines = self._group_words_into_lines(words)

        if scale != 1.0:

            inv = 1.0 / scale

            lines = [
                (text, (x0 * inv, y0 * inv, x1 * inv, y1 * inv))
                for text, (x0, y0, x1, y1) in lines
            ]

        elapsed = time.perf_counter() - t0

        return lines, elapsed, avg_confidence

    def _group_words_into_lines(self, words):

        if not words:
            return []

        heights = [w["y1"] - w["y0"] for w in words]

        heights.sort()

        median_h = heights[len(heights) // 2] or 10

        tolerance = median_h * 0.6

        words_sorted = sorted(words, key=lambda w: (w["y0"] + w["y1"]) / 2)

        rows = []

        for w in words_sorted:

            cy = (w["y0"] + w["y1"]) / 2

            placed = False

            for row in rows:

                if abs(cy - row["cy"]) <= tolerance:

                    row["words"].append(w)
                    row["cy"] = (row["cy"] * row["n"] + cy) / (row["n"] + 1)
                    row["n"] += 1
                    placed = True
                    break

            if not placed:
                rows.append({"cy": cy, "n": 1, "words": [w]})

        rows.sort(key=lambda r: r["cy"])

        lines = []

        for row in rows:

            row_words = sorted(row["words"], key=lambda w: w["x0"])

            text = " ".join(w["text"] for w in row_words)

            x0 = min(w["x0"] for w in row_words)
            y0 = min(w["y0"] for w in row_words)
            x1 = max(w["x1"] for w in row_words)
            y1 = max(w["y1"] for w in row_words)

            lines.append((text, (x0, y0, x1, y1)))

        return lines
