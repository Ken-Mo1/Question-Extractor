from pathlib import Path

folders = [
    "data/uploads",
    "data/extracted",
    "data/images",
    "data/output",
    "data/database",
    "modules",
    "logs",
    "chapter_maps",
    "templates",
    "assets"
]

files = {
    "app.py": "",
    "config.py": "",
    "requirements.txt": "",
    "README.md": "# CBSE AI Question Bank Generator",
    "modules/__init__.py": "",
}

for folder in folders:
    Path(folder).mkdir(parents=True, exist_ok=True)

for file, content in files.items():
    path = Path(file)
    if not path.exists():
        path.write_text(content, encoding="utf-8")

print("\nProject created successfully.\n")