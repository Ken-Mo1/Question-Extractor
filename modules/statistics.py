import sqlite3


class Statistics:

    def __init__(self, db):

        self.db = db

    def total_questions(self):

        cur = self.db.conn.cursor()

        cur.execute("SELECT COUNT(*) FROM questions")

        return cur.fetchone()[0]

    def total_papers(self):

        cur = self.db.conn.cursor()

        cur.execute("SELECT COUNT(DISTINCT pdf_name) FROM questions")

        return cur.fetchone()[0]

    def marks_distribution(self):

        cur = self.db.conn.cursor()

        cur.execute("""

        SELECT

            marks,

            COUNT(*)

        FROM questions

        GROUP BY marks

        ORDER BY marks

        """)

        return cur.fetchall()

    def subject_distribution(self):

        cur = self.db.conn.cursor()

        cur.execute("""

        SELECT

            subject,

            COUNT(*)

        FROM questions

        GROUP BY subject

        """)

        return cur.fetchall()

    def year_distribution(self):

        cur = self.db.conn.cursor()

        cur.execute("""

        SELECT

            year,

            COUNT(*)

        FROM questions

        GROUP BY year

        ORDER BY year

        """)

        return cur.fetchall()