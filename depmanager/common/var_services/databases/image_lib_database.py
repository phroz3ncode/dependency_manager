import os
from datetime import datetime
from os import path

import filedate

from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.var_services.databases.file_database import FileDatabase
from depmanager.common.var_services.databases.var_database import VarDatabase
from depmanager.common.var_services.enums import IMAGE_LIB_DIR
from depmanager.common.var_services.enums import Ext


class ImageLibDatabase(FileDatabase):
    def __init__(self, var_database: VarDatabase, local_path: str):
        super().__init__(var_database=var_database, local_path=local_path)

    @property
    def db_subdir(self) -> str:
        return IMAGE_LIB_DIR

    @property
    def db_name(self) -> str:
        return "image_lib"

    @property
    def db_ext(self) -> str:
        return Ext.JPG

    def _update(self):
        updated_files = False
        missing_vars = []
        progress = ProgressBar(len(self.var_database), description=f"Refreshing {self.db_name}")
        for var_id, var in self.var_database.vars.items():
            progress.inc()
            local_image_name = path.join(self.local_db_path, var.sub_directory, f"{var.clean_name}{Ext.JPG}")
            if path.exists(local_image_name):
                continue

            image_data = var.extract_identity_image_data()
            if image_data is not None:
                updated_files = True
                os.makedirs(path.join(self.local_db_path, var.sub_directory), exist_ok=True)
                image_data.save(local_image_name, format="JPEG")

                # Set the date of the images to the dates of the vars
                image_filedate = filedate.File(local_image_name)
                image_filedate.set(
                    created=str(datetime.fromtimestamp(var.info["created"])),
                    modified=str(datetime.fromtimestamp(var.info["modified"])),
                )
            else:
                missing_vars.append(var_id)
        return updated_files, missing_vars
