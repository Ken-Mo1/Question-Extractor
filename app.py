import time

import streamlit as st
import pandas as pd
from pathlib import Path

from modules.pdf_processor import PDFProcessor
from modules.database import Database
from modules.ocr_engine import OCREngine
from modules.exporter import Exporter
from modules.analytics import Analytics
from modules.search_engine import SearchEngine

st.set_page_config(
    page_title="CBSE AI Question Bank",
    layout="wide"
)

st.title("📚 CBSE AI Question Bank")

PIPELINE_VERSION = "2026-07-15 - fast OCR, MCQ line-grouping, auto-clear"

# -----------------------
# Initialize (cached)
#
# Streamlit reruns this whole script top-to-bottom on EVERY interaction
# - clicking a button, typing a search keyword, moving the year
# stepper. Without caching, that meant EasyOCR's ~500MB model was being
# re-loaded from disk on every single rerun, not just once per
# processing run - wasted seconds (sometimes much more) on every click,
# on top of the real OCR time. @st.cache_resource makes each of these
# a true singleton, built once per server process.
# -----------------------


@st.cache_resource
def get_database():
    return Database()


@st.cache_resource
def get_ocr_engine():
    return OCREngine()


@st.cache_resource
def get_processor(_ocr, _db, pipeline_version):
    processor = PDFProcessor(_ocr, pipeline_version=pipeline_version)
    processor.db = _db
    return processor


db = get_database()
ocr = get_ocr_engine()
processor = get_processor(ocr, db, PIPELINE_VERSION)
exporter = Exporter()

UPLOAD_FOLDER = Path("data/uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# -----------------------
# Sidebar
# -----------------------

st.sidebar.title("Controls")

st.sidebar.caption(f"Build: {PIPELINE_VERSION}")

manual_clear = st.sidebar.button("🔄 Clear Database Now")

export = st.sidebar.button("📄 Export Word Question Bank")

if manual_clear:

    db.clear_database()

    st.sidebar.success("Database cleared.")

st.sidebar.markdown("---")

year_override = st.sidebar.number_input(
    "Exam Year (used only if the filename has no year, e.g. '30-1-2_...pdf')",
    min_value=2000,
    max_value=2100,
    value=2025,
    step=1
)

# -----------------------
# Direct PDF upload - no ZIP step.
# -----------------------

uploaded_files = st.file_uploader(
    "Upload CBSE Question Paper PDF(s)",
    type=["pdf"],
    accept_multiple_files=True
)

if uploaded_files:

    saved_paths = []

    for uploaded_file in uploaded_files:

        file_path = UPLOAD_FOLDER / uploaded_file.name

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        saved_paths.append(file_path)

    st.success(f"Ready to process {len(saved_paths)} PDF(s)")

    # Most people process one paper/batch at a time. By design the
    # database accumulates across uploads (so a school can build one
    # bank across many papers over time) - but nothing enforced
    # clearing it first, so a missed click silently blended an old
    # extraction run with a new one into one "fudged" result. Default
    # ON gets the common case right automatically; uncheck only to
    # deliberately combine multiple uploads into one bank.
    clear_first = st.checkbox(
        "Clear database before processing this batch",
        value=True,
        help=(
            "ON (recommended): this batch replaces whatever is in the "
            "database. OFF: this batch is added on top of what's "
            "already there - only do this if you're deliberately "
            "building one bank across several separate uploads."
        )
    )

    if st.button("🚀 Process PDF(s)"):

        if clear_first:
            db.clear_database()
            st.info("Database cleared before this batch.")

        overall_progress = st.progress(0)

        total = len(saved_paths)

        for i, pdf_path in enumerate(saved_paths):

            st.write(f"**Processing {pdf_path.name} ...**")

            # Live per-page status - a 24-page run doing real OCR work
            # can take real minutes. Without this, that looked
            # identical to a frozen app. Now it visibly moves one page
            # at a time, and if one specific page hangs, you'll see
            # exactly which one and how long it's been stuck.
            page_status = st.empty()
            page_progress = st.progress(0)

            run_start = time.perf_counter()

            def on_page_done(page_num, total_pages, count, reason, elapsed):
                page_progress.progress(page_num / total_pages)
                so_far = time.perf_counter() - run_start
                page_status.write(
                    f"&nbsp;&nbsp;&nbsp;&nbsp;Page {page_num}/{total_pages} "
                    f"— this page: {elapsed:.1f}s "
                    f"({'ok, ' + str(count) + ' question(s)' if count else reason}) "
                    f"— {so_far:.0f}s elapsed"
                )

            stats = processor.process_pdf(
                pdf_path,
                override_year=year_override,
                on_page_done=on_page_done
            )

            errors = stats.get("errors", [])

            skip_reasons = stats.get("skip_reasons", {})

            st.write(
                f"&nbsp;&nbsp;&nbsp;&nbsp;→ {stats['questions']} questions "
                f"extracted from {stats['processed_pages']} of "
                f"{stats['pages']} pages "
                f"({stats['skipped_pages']} pages skipped) in "
                f"{stats['total_seconds']:.0f}s"
            )

            # Where the time actually went, in numbers - so the next
            # speed question is answered with data, not another guess.
            if stats.get("pages_ocrd"):

                avg_ocr = stats["total_ocr_seconds"] / stats["pages_ocrd"]

                st.caption(
                    f"⏱️ {stats['pages_ocrd']} of {stats['pages']} page(s) "
                    f"needed OCR — {stats['total_ocr_seconds']:.0f}s total "
                    f"OCR time ({avg_ocr:.1f}s/page avg), "
                    f"{stats['total_render_seconds']:.0f}s total page-render "
                    f"time. Everything else (native text, chapter matching, "
                    f"database writes) took "
                    f"{stats['total_seconds'] - stats['total_ocr_seconds'] - stats['total_render_seconds']:.0f}s."
                )

            if stats.get("missing_question_numbers"):

                missing_list = ", ".join(
                    str(n) for n in stats["missing_question_numbers"]
                )

                st.warning(
                    f"⚠️ Question number(s) **{missing_list}** never "
                    f"appeared anywhere in {pdf_path.name}, despite "
                    f"higher-numbered questions being found - almost "
                    f"always a real question that got missed (commonly "
                    f"an MCQ whose text sits right against a diagram, or "
                    f"a misread question number), not one that was never "
                    f"in the paper. Worth a manual look at those specific "
                    f"questions in the source PDF."
                )

            if errors:

                st.error(
                    f"⚠️ {len(errors)} page(s) in {pdf_path.name} failed "
                    f"with an actual error, not a normal skip. Expand for "
                    f"details."
                )

                with st.expander(
                    f"Errors for {pdf_path.name} ({len(errors)})"
                ):
                    for err in errors:
                        st.markdown(f"**Page {err['page']}:** {err['error']}")
                        st.code(err["traceback"], language="text")

            if skip_reasons:

                with st.expander(
                    f"Why pages were skipped - {pdf_path.name}"
                ):
                    for reason, count in sorted(
                        skip_reasons.items(),
                        key=lambda item: -item[1]
                    ):
                        st.write(f"- **{count}** page(s): {reason}")

            overall_progress.progress((i + 1) / total)

        st.success("Processing complete")

# -----------------------
# Database
# -----------------------

stale_versions = db.get_stale_pipeline_summary(PIPELINE_VERSION)

if stale_versions:

    stale_total = sum(count for _, count in stale_versions)

    breakdown = ", ".join(
        f"{count} from '{version}'" for version, count in stale_versions
    )

    st.warning(
        f"⚠️ {stale_total} question(s) in the database were extracted by "
        f"a DIFFERENT build of this app than the one currently running "
        f"({breakdown}). The table below and any export will be a mix of "
        f"old and new extraction logic. Click **Clear Database Now** in "
        f"the sidebar and re-process to get a clean, consistent result."
    )

rows = db.get_all_questions()

columns = [
    "id",
    "year",
    "subject",
    "paper_set",
    "paper_code",
    "language",
    "pdf",
    "page",
    "question_no",
    "marks",
    "type",
    "chapter",
    "question",
    "image_path"
]

df = pd.DataFrame(rows, columns=columns)

DISPLAY_COLUMNS = [
    "id",
    "subject",
    "chapter",
    "type",
    "marks",
    "question_no",
    "question",
    "image_path"
]

# -----------------------
# Dashboard
# -----------------------

if not df.empty:

    analytics = Analytics(df)

    summary = analytics.summary()

    c1, c2, c3, c4, c5 = st.columns(5)

    c1.metric("Questions", summary["Questions"])
    c2.metric("Subjects", summary["Subjects"])
    c3.metric("Chapters", summary["Chapters"])
    c4.metric("Types", summary["Types"])

    missing_screenshots = df["image_path"].isna().sum()

    c5.metric(
        "Missing Screenshots",
        int(missing_screenshots),
        help=(
            "Should be 0 (or very close to it) - every extracted "
            "question is supposed to get a screenshot. A high number "
            "here usually means stale data from before this was added: "
            "click Clear Database and re-process."
        )
    )

# -----------------------
# Search
# -----------------------

st.divider()

st.header("Search")

col_a, col_b = st.columns(2)

keyword = col_a.text_input("Keyword")

chapter_filter = "All"

if not df.empty:

    chapter_options = ["All"] + sorted(
        c for c in df["chapter"].dropna().unique() if c
    )

    chapter_filter = col_b.selectbox("Chapter", chapter_options)

if not df.empty:

    search = SearchEngine(df)

    results = df

    if keyword:
        results = search.keyword(keyword)

    if chapter_filter != "All":
        results = results[results["chapter"] == chapter_filter]

    st.write(f"Results : {len(results)}")

    st.dataframe(
        results[DISPLAY_COLUMNS],
        use_container_width=True,
        height=500
    )

# -----------------------
# Export
# -----------------------

if export and not df.empty:

    word_file = exporter.export()

    st.success(f"Exported Word question bank to {word_file}")
