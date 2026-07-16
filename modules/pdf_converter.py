import fitz
from pathlib import Path


class PDFConverter:
    """
    Renders PDF pages to images ON DEMAND.

    The previous version converted and saved EVERY page of EVERY PDF at
    400 DPI, even when the embedded PDF text was already good enough and
    OCR was never going to be used on that page. On large ZIP batches
    this wasted a lot of time and disk space.

    This version only renders a page when PDFProcessor decides OCR is
    actually needed for it (see PDFProcessor.extract_page_text). It also
    shares one already-open fitz.Document across all pages of a PDF,
    instead of re-opening the file for every page.
    """

    def __init__(self, dpi=300):
        # 300 DPI is enough for OCR accuracy and is noticeably faster
        # than 400 DPI. Raise this back to 400 only if you see OCR
        # accuracy problems on small/faint text.
        self.image_root = Path("data/images")
        self.dpi = dpi

    def render_page(self, doc, pdf_name, page_number):
        """
        Render a single page of an already-open fitz.Document to a PNG
        and return its path.

        `doc` must be a fitz.Document opened once by the caller
        (PDFProcessor.process_pdf) and reused across all pages of that
        PDF - do not call fitz.open() again in here.
        """

        output_folder = self.image_root / pdf_name
        output_folder.mkdir(parents=True, exist_ok=True)

        page = doc.load_page(page_number)

        zoom = self.dpi / 72
        matrix = fitz.Matrix(zoom, zoom)

        pix = page.get_pixmap(matrix=matrix)

        image_path = output_folder / f"page_{page_number + 1:03}.png"

        pix.save(image_path)

        return image_path
