from pathlib import Path

# ------------------------
# Folders
# ------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

UPLOAD_DIR = DATA_DIR / "uploads"

EXTRACT_DIR = DATA_DIR / "extracted"

DATABASE_DIR = DATA_DIR / "database"

EXPORT_DIR = DATA_DIR / "exports"

TEMP_DIR = DATA_DIR / "temp"

# ------------------------
# Database
# ------------------------

DATABASE_NAME = "cbse_question_bank.db"

# ------------------------
# OCR
# ------------------------

MIN_TEXT_LENGTH = 200

OCR_LANG = ["en"]

# ------------------------
# Supported Subjects
# ------------------------

SUPPORTED_SUBJECTS = [

    "Science",
    "Mathematics",
    "English",
    "Hindi",
    "Social Science"

]

# ------------------------
# Export
# ------------------------

WORD_FILE = "QuestionBank.docx"

# ------------------------
# Create folders automatically
# ------------------------

for folder in [

    DATA_DIR,
    UPLOAD_DIR,
    EXTRACT_DIR,
    DATABASE_DIR,
    EXPORT_DIR,
    TEMP_DIR

]:

    folder.mkdir(parents=True, exist_ok=True)