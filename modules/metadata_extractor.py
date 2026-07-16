import re
from pathlib import Path


class MetadataExtractor:

    def __init__(self):

        # Subject keywords in filename

        self.subjects = {

            "science": "Science",

            "mathematics": "Mathematics",
            "math": "Mathematics",
            "maths": "Mathematics",

            "social science": "Social Science",
            "social_science": "Social Science",
            "socialscience": "Social Science",
            "sst": "Social Science",

            "english": "English",

            "hindi": "Hindi",

            "artificial intelligence": "Artificial Intelligence",
            "artificial_intelligence": "Artificial Intelligence",
            "ai": "Artificial Intelligence",

            "information technology": "Information Technology",
            "it": "Information Technology",

            "computer applications": "Computer Applications",
            "computer": "Computer Applications"

        }

    # -----------------------------------------------------

    def detect_subject(self, filename):

        lower = filename.lower()

        # Longer keywords first

        for keyword in sorted(self.subjects.keys(), key=len, reverse=True):

            if keyword in lower:

                return self.subjects[keyword]

        return "Unknown"

    # -----------------------------------------------------

    def detect_language(self, filename):

        lower = filename.lower()

        if "hindi" in lower:

            return "Hindi"

        return "English"

    # -----------------------------------------------------

    def detect_year(self, filename):

        m = re.search(r"(20\d{2})", filename)

        if m:

            return int(m.group(1))

        return None

    # -----------------------------------------------------

    def detect_paper_code(self, filename):

        # Example:
        #
        # 30/2/2
        # 31/5/1
        # 086
        #

        m = re.search(r'(\d{2}/\d+/\d+)', filename)

        if m:

            return m.group(1)

        m = re.search(r'\b\d{3}\b', filename)

        if m:

            return m.group(0)

        return filename

    # -----------------------------------------------------

    def detect_paper_set(self, filename):

        lower = filename.lower()

        m = re.search(r'set[\s_-]*([a-z0-9]+)', lower)

        if m:

            return m.group(1).upper()

        m = re.search(r'\b([abcd])\b', lower)

        if m:

            return m.group(1).upper()

        return "Unknown"

    # -----------------------------------------------------

    def extract(self, pdf_path, override_year=None):
        """
        override_year lets the caller (PDFProcessor / the Streamlit
        upload form) supply a year when the filename itself has none.
        Real CBSE filenames (e.g. "30-1-2_Mathematics Standard.pdf")
        very often don't encode an exam year at all - there's no
        reliable way to recover it from the filename or page content
        in that case, so it has to come from the user.
        """

        filename = Path(pdf_path).stem

        year = self.detect_year(filename)

        if year is None:
            year = override_year

        metadata = {

            "year": year,

            "subject": self.detect_subject(filename),

            "paper_code": self.detect_paper_code(filename),

            "paper_set": self.detect_paper_set(filename),

            "language": self.detect_language(filename)

        }

        return metadata