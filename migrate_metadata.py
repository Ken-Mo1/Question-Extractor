import sqlite3
import re
from pathlib import Path

DB = Path("data/database/cbse_question_bank.db")

conn = sqlite3.connect(DB)
cur = conn.cursor()

cur.execute("""
SELECT id, pdf_name
FROM questions
""")

rows = cur.fetchall()

updated = 0

for row_id, pdf_name in rows:

    filename = Path(pdf_name).stem
    lower = filename.lower()

    # -------------------
    # Defaults
    # -------------------

    year = 2022              # Your current ZIP is 2022
    subject = "Science"
    language = "English"

    # Make every paper unique
    paper_set = filename

    # Paper code
    paper_code = filename

    m = re.search(r"(\d{4})", filename)

    if m:
        paper_code = m.group(1)

    if "hindi" in lower:
        language = "Hindi"

    if "english" in lower:
        subject = "English"

    elif "math" in lower:
        subject = "Mathematics"

    elif "science" in lower:
        subject = "Science"

    cur.execute(
        """
        UPDATE questions
        SET
            year=?,
            subject=?,
            paper_set=?,
            paper_code=?,
            language=?
        WHERE id=?
        """,
        (
            year,
            subject,
            paper_set,
            paper_code,
            language,
            row_id
        )
    )

    updated += 1

conn.commit()

print("=" * 50)
print("Migration Complete")
print(f"Rows Updated : {updated}")
print("=" * 50)

conn.close()