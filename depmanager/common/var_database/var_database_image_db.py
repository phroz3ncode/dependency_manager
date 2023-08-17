import os
import zipfile
from datetime import datetime
from os import path

import filedate

from depmanager.common.enums.ext import Ext
from depmanager.common.enums.paths import IMAGE_LIB_DIR
from depmanager.common.shared.tools import remove_empty_directories
from depmanager.common.var_database.var_database_base import VarDatabaseBase


class VarDatabaseImageDB(VarDatabaseBase):
    def __init__(self, root: str = None, image_root: str = None, quick_scan: bool = False):
        super().__init__(root, quick_scan)
        self._images_added_or_removed = False

        self.image_root = image_root
        self.image_root_db = "image_lib.zip"

    @property
    def image_db_enabled(self) -> bool:
        return self.image_root is not None

    @property
    def image_db_path(self):
        return path.join(self.rootpath, self.image_root_db)

    @property
    def image_db_local_path(self):
        return path.join(self.image_root, IMAGE_LIB_DIR)

    @property
    def image_db_local_dep_path(self):
        return path.join(self.image_root, f"{IMAGE_LIB_DIR}{Ext.DEP}")

    @property
    def image_files(self) -> list[str]:
        dir_listing = []
        for (dirpath, _, filenames) in os.walk(self.image_db_local_path):
            if IMAGE_LIB_DIR not in dirpath:
                continue
            dir_listing.extend([os.path.join(dirpath, f) for f in filenames if len(f) > 4 and f[-4:] == Ext.JPG])
        return dir_listing

    @property
    def image_file_subdirs(self):
        print("Scanning subdirectories")
        os.makedirs(self.image_db_local_path, exist_ok=True)

        dep = {}
        for (dir_path, _, files) in os.walk(self.image_db_local_path):
            for file in files:
                dep[file.replace(Ext.JPG, Ext.EMPTY)] = path.relpath(dir_path, self.image_db_local_path)
        return dep

    def save_image_db(self) -> None:
        if self._images_added_or_removed:
            print(f"Saving image database {self.image_db_path}")
            if os.path.exists(self.image_db_path):
                os.remove(self.image_db_path)
            with zipfile.ZipFile(self.image_db_path, "w", zipfile.ZIP_STORED) as zip_file:
                for item in self.image_files:
                    zip_file.write(
                        item, os.path.relpath(item, self.image_db_local_path), compress_type=zipfile.ZIP_STORED
                    )
            self._images_added_or_removed = False

    def save_image_db_as_dep(self):
        print("Saving image database as .dep")
        os.makedirs(self.image_db_local_path, exist_ok=True)

        dep = []
        for (_, _, files) in os.walk(self.image_db_local_path):
            for file in files:
                dep.append(file.replace(Ext.JPG, Ext.EMPTY))
        with open(self.image_db_local_dep_path, "w", encoding="UTF-8") as write_dep_file:
            for line in dep:
                write_dep_file.write(f"{line}\n")

    def load_image_db(self) -> None:
        files = self.directory_files
        image_files = self.image_files
        if len(files) != len(image_files):
            if path.exists(self.image_db_path):
                with zipfile.ZipFile(self.image_db_path) as zip_file:
                    zip_file.extractall(self.image_db_local_path)
            else:
                os.makedirs(self.image_db_local_path, exist_ok=True)

    def update_var_image(self, file_path: str) -> None:
        var = self.get_var_from_filepath(file_path, is_image=True)
        if var is not None:
            local_image_name = path.join(self.image_db_local_path, var.sub_directory, f"{var.clean_name}{Ext.JPG}")
            if path.exists(local_image_name):
                return

            image_data = var.extract_identity_image_data()
            if image_data is not None:
                os.makedirs(path.join(self.image_db_local_path, var.sub_directory), exist_ok=True)
                image_data.save(local_image_name, format="JPEG")

                # Set the date of the images to the dates of the vars
                image_filedate = filedate.File(local_image_name)
                image_filedate.set(
                    created=str(datetime.fromtimestamp(var.info["created"])),
                    modified=str(datetime.fromtimestamp(var.info["modified"])),
                )

    def refresh_image_db(self) -> None:
        print("Updating image lib... [Progress bar TBD]")
        self.load_image_db()
        required_image_files = set(path.join(v.sub_directory, f"{v.clean_name}{Ext.JPG}") for _, v in self.vars.items())
        current_image_files = set(os.path.relpath(f, self.image_db_local_path) for f in self.image_files)
        removed_files = current_image_files - required_image_files
        added_files = required_image_files - current_image_files

        for image_path in sorted(removed_files):
            os.remove(os.path.join(self.image_db_local_path, image_path))

        for image_path in sorted(added_files):
            self.update_var_image(image_path)

        if len(removed_files) > 0 or len(added_files) > 0 or not os.path.exists(self.image_db_path):
            remove_empty_directories(self.image_db_local_path)
            self._images_added_or_removed = True
