import sqlite3
from pathlib import Path


# Shared ORDER BY clause - imported directly by exporter.py rather than
# copy-pasted, so the on-screen table, CSV/Word export (if re-added),
# and any future consumer can never drift out of sync again (this
# mismatch caused real bugs earlier in this project: the Word doc and
# the app table used to sort differently and never matched).
#
# Groups by subject, then chapter, then a natural CBSE section order
# for type (MCQ -> Assertion-Reason -> VSA -> SA -> LA -> Case Study)
# rather than alphabetical, since alphabetical would scatter them
# (e.g. "Case Study" would sort before "Long Answer").
QUESTION_ORDER_BY = """
    ORDER BY
        subject,
        chapter,
        CASE type
            WHEN 'MCQ' THEN 1
            WHEN 'Assertion-Reason' THEN 2
            WHEN 'Very Short Answer' THEN 3
            WHEN 'Short Answer' THEN 4
            WHEN 'Long Answer' THEN 5
            WHEN 'Case Study' THEN 6
            ELSE 7
        END,
        CAST(question_no AS INTEGER)
"""


class Database:

    def __init__(self):

        # --------------------------------------------------
        # Single database location for entire application
        # --------------------------------------------------

        db_folder = Path("data/database")
        db_folder.mkdir(parents=True, exist_ok=True)

        self.db_path = db_folder / "cbse_question_bank.db"

        self.conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False
        )

        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")

        self.create_tables()

    # ------------------------------------------------------

    def create_tables(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        CREATE TABLE IF NOT EXISTS questions(

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            year INTEGER,

            subject TEXT,

            paper_set TEXT,

            paper_code TEXT,

            language TEXT,

            pdf_name TEXT,

            page_number INTEGER,

            question_no TEXT,

            marks INTEGER,

            type TEXT,

            chapter TEXT,

            question_hash TEXT,

            question TEXT,

            image_path TEXT,

            pipeline_version TEXT

        )

        """)

        # --------------------------------------------------
        # Migration for databases created before image_path / type
        # existed. ALTER TABLE ADD COLUMN is safe to run on an
        # existing table - it does not touch existing rows.
        # --------------------------------------------------

        cursor.execute("PRAGMA table_info(questions)")

        existing_columns = {row[1] for row in cursor.fetchall()}

        if "image_path" not in existing_columns:

            cursor.execute(
                "ALTER TABLE questions ADD COLUMN image_path TEXT"
            )

        if "type" not in existing_columns:

            cursor.execute(
                "ALTER TABLE questions ADD COLUMN type TEXT"
            )

        if "pipeline_version" not in existing_columns:

            # Rows inserted before this column existed are stamped NULL
            # here (see get_stale_pipeline_summary() below) - NULL is
            # itself treated as "stale / unknown version", which is the
            # correct, safe interpretation: we genuinely don't know what
            # code produced them.
            cursor.execute(
                "ALTER TABLE questions ADD COLUMN pipeline_version TEXT"
            )

        # --------------------------------------------------
        # Future-proof indexes
        # --------------------------------------------------

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_subject
        ON questions(subject)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chapter
        ON questions(chapter)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_year
        ON questions(year)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_paper
        ON questions(paper_code)
        """)

        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_question_hash
        ON questions(question_hash)
        """)

        # --------------------------------------------------
        # Composite uniqueness
        #
        # Same question CAN exist in different years,
        # different papers and different subjects.
        #
        # We only prevent duplicate insertion within the
        # exact same paper.
        # --------------------------------------------------

        cursor.execute("""

        CREATE UNIQUE INDEX IF NOT EXISTS unique_question

        ON questions(

            subject,
            year,
            paper_code,
            question_no,
            question_hash

        )

        """)

        self.conn.commit()

    # ------------------------------------------------------

    def insert_questions(self, rows):

        cursor = self.conn.cursor()

        cursor.executemany("""

        INSERT OR IGNORE INTO questions(

            year,
            subject,
            paper_set,
            paper_code,
            language,
            pdf_name,
            page_number,
            question_no,
            marks,
            type,
            chapter,
            question_hash,
            question,
            image_path,
            pipeline_version

        )

        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)

        """, rows)

        self.conn.commit()

    # ------------------------------------------------------

    def get_all_questions(self):

        cursor = self.conn.cursor()

        cursor.execute("""

        SELECT

            id,
            year,
            subject,
            paper_set,
            paper_code,
            language,
            pdf_name,
            page_number,
            question_no,
            marks,
            type,
            chapter,
            question,
            image_path

        FROM questions

        """ + QUESTION_ORDER_BY)

        return cursor.fetchall()

    # ------------------------------------------------------

    def total_questions(self):

        cursor = self.conn.cursor()

        cursor.execute(

            "SELECT COUNT(*) FROM questions"

        )

        return cursor.fetchone()[0]

    # ------------------------------------------------------

    def get_stale_pipeline_summary(self, current_version):
        """
        Returns a list of (pipeline_version, row_count) for every row in
        the database that was NOT produced by `current_version` -
        including rows with pipeline_version = NULL (inserted before
        this column existed, or by any earlier build).

        This exists because of a real, already-observed failure mode:
        "Clear Database before re-processing" is a instruction in the
        sidebar, not something the app enforces, so a re-processed PDF
        can silently mix with rows from a completely different, older
        extraction logic. The exported Word doc and the on-screen table
        then look internally consistent (no crash, no error) while
        actually being a blend of two incompatible pipelines - e.g. only
        a handful of "screenshot" rows because most of the table is
        really old "only-if-overlaps-a-diagram" rows. Surfacing this
        directly, instead of relying on the user to remember, is the
        fix.
        """

        cursor = self.conn.cursor()

        cursor.execute(
            """
            SELECT
                COALESCE(pipeline_version, '(unknown / pre-tracking)'),
                COUNT(*)
            FROM questions
            WHERE pipeline_version IS NOT ?
            GROUP BY pipeline_version
            """,
            (current_version,)
        )

        return cursor.fetchall()

    # ------------------------------------------------------

    def clear_database(self):

        cursor = self.conn.cursor()

        cursor.execute(

            "DELETE FROM questions"

        )

        self.conn.commit()

    # ------------------------------------------------------

    def optimize(self):

        cursor = self.conn.cursor()

        cursor.execute("VACUUM")
        cursor.execute("ANALYZE")

        self.conn.commit()

    # ------------------------------------------------------

    def close(self):

        self.conn.close()