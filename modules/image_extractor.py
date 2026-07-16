import fitz
from pathlib import Path
from PIL import Image


class ImageExtractor:
    """
    Screenshots each question directly from the rendered page, instead
    of reconstructing its text. This is the core of the "screenshot per
    question" approach: rather than chasing every way a PDF's fonts,
    symbols, or layout can defeat text extraction, we just crop the
    actual pixels of the region a question occupies. Whatever is
    visually there - equations, diagrams, tables, degree symbols,
    scrambled-looking MCQ grids - comes through correctly because it's
    a picture, not reconstructed text.

    Works for two kinds of pages:
      - Native-text PDF pages (bboxes come from PyMuPDF, in PDF points)
      - Scanned/vector-outlined pages that fall back to OCR (bboxes come
        from EasyOCR, in pixel coordinates of the already-rendered page)
    """

    def __init__(self, dpi=300):
        self.image_root = Path("data/question_images")
        self.dpi = dpi

    # ------------------------------------------------------

    def crop_region(
        self,
        doc,
        pdf_name,
        page_number,
        y0,
        y1,
        question_no,
        margin=8
    ):
        """
        NATIVE-TEXT PATH: renders the given vertical band of the page
        (PDF points, with a small margin) to a PNG and returns its path.
        """

        page = doc.load_page(page_number)

        page_height = page.rect.height
        page_width = page.rect.width

        clip = fitz.Rect(
            0,
            max(y0 - margin, 0),
            page_width,
            min(y1 + margin, page_height)
        )

        zoom = self.dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=matrix, clip=clip)

        image_path = self._output_path(pdf_name, page_number, question_no)

        pix.save(image_path)

        return image_path

    # ------------------------------------------------------

    def crop_region_from_image(
        self,
        source_image_path,
        pdf_name,
        page_number,
        y0,
        y1,
        question_no,
        margin=15
    ):
        """
        OCR / SCANNED-PAGE PATH: crops a vertical band (pixel
        coordinates, matching whatever EasyOCR returned) directly out of
        the already-rendered page PNG - no second render needed, since
        OCR already required rendering this page once.
        """

        with Image.open(source_image_path) as img:

            width, height = img.size

            top = max(int(y0 - margin), 0)
            bottom = min(int(y1 + margin), height)

            cropped = img.crop((0, top, width, bottom))

            image_path = self._output_path(
                pdf_name, page_number, question_no
            )

            cropped.save(image_path)

        return image_path

    # ------------------------------------------------------

    def _output_path(self, pdf_name, page_number, question_no):

        folder = self.image_root / pdf_name
        folder.mkdir(parents=True, exist_ok=True)

        safe_question_no = str(question_no).replace("/", "-")

        return folder / f"page{page_number + 1:03}_q{safe_question_no}.png"
