import os
import shutil
from os import path

from depmanager.common.shared.tools import remove_empty_directories
from depmanager.common.var_services.databases.var_database import VarDatabase
from depmanager.common.var_services.enums import Ext


class FileDatabase:
    def __init__(self, var_database: VarDatabase, local_path: str):
        self.var_database = var_database
        self.local_path = local_path

    @property
    def db_subdir(self) -> str:
        raise NotImplementedError("should be implemented by descendents")

    @property
    def db_name(self) -> str:
        raise NotImplementedError("should be implemented by descendents")

    @property
    def db_ext(self) -> str:
        raise NotImplementedError("should be implemented by descendents")

    @property
    def var_db_rootpath(self):
        return self.var_database.rootpath

    @property
    def local_db_path(self):
        return path.join(self.local_path, self.db_subdir)

    @property
    def local_dep_path(self):
        return path.join(self.local_path, f"{self.db_name}{Ext.DEP}")

    @property
    def exists(self):
        return path.exists(self.local_db_path)

    def save(self):
        print(f"Saving {self.db_name} to remote")
        local_image_db = path.join(self.local_path, self.db_subdir)
        if not path.exists(local_image_db):
            print(f"Skipping... no local {self.db_name} found")
            return

        remote_image_db = path.join(self.var_db_rootpath, self.db_subdir)
        shutil.make_archive(remote_image_db, "zip", local_image_db)

    def load(self):
        print(f"Loading {self.db_name} from remote")
        remote_image_db = path.join(self.var_db_rootpath, f"{self.db_subdir}{Ext.ZIP}")
        local_image_db = path.join(self.local_path, self.db_subdir)
        if path.exists(remote_image_db):
            shutil.unpack_archive(remote_image_db, local_image_db, "zip")
        else:
            os.makedirs(local_image_db, exist_ok=True)

    def remove_missing(self):
        """Remove files in the databse that are no longer in the VarDatabase"""
        print("Scanning for files present from removed vars")
        files_removed = False
        for (root, _, files) in os.walk(self.local_db_path):
            for file in files:
                sub_directory = path.relpath(root, self.local_db_path)
                var_id = file.replace(self.db_ext, Ext.EMPTY)
                var = self.var_database.vars.get(var_id)

                if var is not None and (var.sub_directory == sub_directory):
                    continue
                files_removed = True
                os.remove(path.join(root, file))
        return files_removed

    def _update(self) -> tuple[bool, list[str]]:
        raise NotImplementedError("should be implemented by descendents")

    def update(self, save_after_update=True):
        if not self.exists:
            self.load()
        files_removed = self.remove_missing()
        remove_empty_directories(self.local_db_path)
        files_updated, response = self._update()
        if save_after_update and (files_removed or files_updated):
            self.save()
        return response

    def get_sub_directories_from_database(self):
        print(f"Scanning subdirectories from {self.db_name}")
        os.makedirs(self.local_db_path, exist_ok=True)

        dep = {}
        for (dir_path, _, files) in os.walk(self.local_db_path):
            for file in files:
                dep[file.replace(self.db_ext, Ext.EMPTY)] = path.relpath(dir_path, self.local_db_path)
        return dep

    def build_dep_from_database(self):
        print(f"Constructing .dep from {self.db_name}")
        os.makedirs(self.local_db_path, exist_ok=True)

        dep = []
        for (_, _, files) in os.walk(self.local_db_path):
            for file in files:
                dep.append(file.replace(self.db_ext, Ext.EMPTY))
        with open(self.local_dep_path, "w", encoding="UTF-8") as write_dep_file:
            for line in dep:
                write_dep_file.write(f"{line}\n")
