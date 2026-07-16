from pathlib import Path
import time


class ZipProcessor:

    def __init__(self, pdf_processor):
        self.pdf_processor = pdf_processor

    def process(self, pdf_files):

        summary = {
            "pdfs": 0,
            "questions": 0,
            "pages": 0,
            "failed": 0,
            "files": [],
            "time": 0
        }

        start = time.time()

        for pdf in pdf_files:

            try:

                result = self.pdf_processor.process_pdf(pdf)

                if result is None:
                    result = {}

                summary["pdfs"] += 1
                summary["questions"] += result.get("questions", 0)
                summary["pages"] += result.get("pages", 0)

                summary["files"].append({
                    "file": pdf.name,
                    "pages": result.get("pages", 0),
                    "questions": result.get("questions", 0),
                    "status": "Success"
                })

            except Exception as e:

                summary["failed"] += 1

                summary["files"].append({
                    "file": pdf.name,
                    "pages": 0,
                    "questions": 0,
                    "status": str(e)
                })

        summary["time"] = round(time.time() - start, 2)

        return summary
