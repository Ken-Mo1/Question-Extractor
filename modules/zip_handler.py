from pathlib import Path
import zipfile
import shutil
import os
import stat
import time


class ZipHandler:

    def __init__(self):
        self.upload_folder = Path("data/uploads")
        self.extract_folder = Path("data/extracted")

    def save_uploaded_file(self, uploaded_file):

        self.upload_folder.mkdir(parents=True, exist_ok=True)

        file_path = self.upload_folder / uploaded_file.name

        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())

        return file_path

    def _remove_readonly(self, func, path, exc_info):
        """
        Removes read-only attribute from files/folders so Windows can delete them.
        """
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def clean_extract_folder(self):

        if self.extract_folder.exists():

            for attempt in range(3):

                try:
                    shutil.rmtree(
                        self.extract_folder,
                        onexc=self._remove_readonly
                    )
                    break

                except PermissionError:

                    if attempt == 2:
                        raise

                    time.sleep(1)

        self.extract_folder.mkdir(parents=True, exist_ok=True)

    def extract_zip(self, zip_path):

        self.clean_extract_folder()

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(self.extract_folder)

        return self.extract_folder

    def get_all_pdfs(self):

        return sorted(self.extract_folder.rglob("*.pdf"))