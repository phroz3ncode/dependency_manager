import itertools
import json
import multiprocessing
import os
import shutil
import sys
import time
import zipfile
from collections import defaultdict
from json import JSONDecodeError
from os import path
from typing import Optional

from orjson import orjson

from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import get_file_stat
from depmanager.common.var_services.entities.var_object import VarObject
from depmanager.common.var_services.enums import IMAGE_LIB_DIR
from depmanager.common.var_services.enums import REPAIR_LIB_DIR
from depmanager.common.var_services.enums import TEMP_VAR_NAME
from depmanager.common.var_services.enums import Ext


class VarDatabaseBase:
    INCLUDE_LIST = ["var"]
    EXCLUDE_LIST = ["disabled"]
    APPEARANCE_LIST = ["json", "vap"]

    def __init__(self, root: str = None, disable_save: bool = False, quick_scan: bool = False):
        # Database is always assumed to be dirty on initialization
        self._database_is_dirty = True

        self.rootpath = root
        self.root_db = "remote_db.json"
        self.vars = {}
        self.disable_save = disable_save
        self.quick_scan = quick_scan
        self.scanned = False

        self.load()

    def __len__(self):
        return len(self.vars)

    def __getitem__(self, item):
        return self.vars.get(item)

    def __setitem__(self, key, value):
        self.vars[key] = value

    def _clear_attributes(self, attributes):
        for attrib in attributes:
            try:
                delattr(self, attrib)
            except AttributeError:
                continue

    def _clear_cache(self):
        self._clear_attributes(
            [
                "directory_files",
                "vars_directory_files",
                "vars_versions",
            ]
        )
        self._database_is_dirty = False

    def refresh(self) -> None:
        # Cache must be cleared to perform a clean scan
        self._clear_cache()
        self.remove_files()
        self.add_files()
        # If the scan updated any variables the cache may now be "dirty"
        if self._database_is_dirty:
            self._clear_cache()

    @property
    def keys(self):
        return set(self.vars.keys())

    @property
    def directory_count(self):
        return len(self.directory_files)

    @property
    def root_db_path(self):
        return path.join(self.rootpath, self.root_db)

    @property
    def directory_listing(self) -> dict[str, list]:
        dir_listing = {}
        for (dirpath, _, filenames) in os.walk(self.rootpath):
            if self.ignore_directory(dirpath) or len(filenames) == 0:
                continue
            vars_in_filenames = [f for f in filenames if len(f) > 4 and f[-4:] == Ext.VAR]
            if len(vars_in_filenames) > 0:
                dir_listing[dirpath] = vars_in_filenames
        return dir_listing

    @cached_property
    def directory_files(self) -> list[tuple[str, float, float]]:
        print("Parallel scanning directories...")
        self.scanned = True
        files = [
            os.path.join(f[1], f[0])
            for f in list(
                itertools.chain.from_iterable(
                    itertools.product(files, [key]) for key, files in self.directory_listing.items()
                )
            )
        ]

        try:
            with multiprocessing.Pool() as m_pool:
                # Pycharm debugger has issues sometimes
                if sys.gettrace():
                    time.sleep(2)
                files_with_stats = list(m_pool.map(get_file_stat, files))
        except BufferError:
            print("Failed to secure buffer...")
            files_with_stats = list(get_file_stat(file) for file in files)
        return files_with_stats

    @cached_property
    def vars_directory_files(self) -> set[str]:
        return set(v.file_path for _, v in self.vars.items())

    @cached_property
    def vars_versions(self) -> defaultdict[str, set]:
        versions = defaultdict(set)
        for _, var in self.vars.items():
            versions[var.duplicate_id].add(var.version)
        return versions

    def to_json(self) -> str:
        return orjson.dumps(
            {"rootpath": self.rootpath, "vars": [v.to_dict() for _, v in self.vars.items()]}, option=orjson.OPT_INDENT_2
        ).decode("UTF-8")

    def save(self) -> None:
        print(f"Saving database {self.root_db_path}")
        with open(self.root_db_path, "w", encoding="UTF-8") as write_db_file:
            write_db_file.write(self.to_json())

    def load(self) -> None:
        if not path.exists(self.root_db_path):
            self.refresh()
        else:
            try:
                print(f"Loading default database {self.root_db_path}")
                with open(self.root_db_path, "r", encoding="UTF-8") as read_db_file:
                    data = json.load(read_db_file)
                    for item in data["vars"]:
                        var = VarObject.from_dict(data=item, root_path=self.rootpath)
                        self[var.var_id] = var
            except JSONDecodeError:
                self.refresh()

    def ignore_directory(self, dirpath: str) -> bool:
        return IMAGE_LIB_DIR in dirpath or REPAIR_LIB_DIR in dirpath or "_ignore" in dirpath

    def get_var_from_filepath(self, file_path: str, is_image: bool = False) -> Optional[VarObject]:
        filename = path.basename(file_path)
        filename_ext = path.splitext(filename)[-1]
        if (filename_ext != Ext.VAR and not is_image) or (filename_ext != Ext.JPG and is_image):
            return None
        # If we find a temp var, we should destroy it
        if filename == TEMP_VAR_NAME:
            print(f"Removing temp var: {file_path}")
            os.remove(file_path)
            return None
        if filename_ext == Ext.VAR and len(filename.split(".")) == 4 and "_" in filename.split(".")[2]:
            print(f"Incorrect formatted var: {file_path}")

        return self.vars.get(filename.replace(Ext.VAR if not is_image else Ext.JPG, Ext.EMPTY))

    @staticmethod
    def get_var_name_as_latest(var_id):
        return f"{'.'.join(var_id.split('.')[:-1])}.latest"

    def get_var_name(self, var_id, always=False) -> Optional[str]:
        try:
            author, name, version = var_id.split(".")
        except ValueError:
            if always:
                return var_id
            return None
        if version == "latest":
            # noinspection PyTypeChecker
            versions = self.vars_versions[f"{author}.{name}"]
            if len(versions) == 0:
                if always:
                    return var_id
                return None
            var_id = f"{author}.{name}.{max(versions)}"
        if var_id not in self.vars:
            if always:
                return var_id
            return None
        return var_id

    def update_var(self, file_path):
        try:
            var = VarObject(root_path=self.rootpath, file_path=file_path, quick_scan=self.quick_scan)
            self[var.var_id] = var
        except (ValueError, KeyError, PermissionError, zipfile.BadZipfile) as err:
            print(f"ERROR :: Could not read {file_path} >> {err}")

    def add_file(self, file_path: str, filemod=None, filesize=None) -> bool:
        if "temp.temp.1.var" in file_path:
            return False

        var = self.get_var_from_filepath(file_path)
        if var is not None:
            if var.file_path != file_path:
                print(f"Warning: {file_path} is a duplicate var")
                return False
            if (filemod != var.modified and filesize != var.size) or (
                (filemod is None or filesize is None) and var.updated
            ):
                print(f"Updating: {var.var_id}")
                self.update_var(file_path)
                self._database_is_dirty = True
                return True
            return False

        self.update_var(file_path)
        self._database_is_dirty = True
        return True

    def add_files(self) -> None:
        progress = ProgressBar(self.directory_count, description="Scanning vars")
        for filepath, filemod, filesize in self.directory_files:
            progress.inc()
            file_added = self.add_file(filepath, filemod, filesize)
            if file_added:
                self._database_is_dirty = True
        if not self.disable_save and self._database_is_dirty:
            self.save()

    def remove_files(self) -> None:
        files = self.directory_files
        present_files = set(f[0] for f in files)
        current_var_files = self.vars_directory_files
        removed_files = current_var_files - present_files
        if len(removed_files) > 0:
            self._database_is_dirty = True

        for var_path in sorted(removed_files):
            var = self.get_var_from_filepath(var_path).var_id
            print(f"Removing: {var}")
            self.vars.pop(var)

    def manipulate_file(self, var_id, dest_dir, move=False, symlink=False) -> None:
        os.makedirs(dest_dir, exist_ok=True)

        var = self[var_id]
        src_path = var.file_path
        dest_path = path.join(dest_dir, var.filename)

        if not path.isfile(src_path):
            print(f"Var not found on disk: {var_id} [Please refresh remote or local database]")
        if move:
            os.rename(src_path, dest_path)
            self[var.var_id] = self[var.var_id].from_new_path(self.rootpath, dest_path)
        elif symlink and var.prefer_symlink:
            if not path.isfile(dest_path):
                try:
                    os.symlink(src_path, dest_path)
                except WindowsError:
                    shutil.copy2(src_path, dest_path)
        else:
            if not path.isfile(dest_path):
                shutil.copy2(src_path, dest_path)

    def manipulate_file_list(self, var_id_list, sub_directory, append=False, remove=False, suffix=False) -> None:
        if len(var_id_list) == 0:
            return

        progress = ProgressBar(len(var_id_list), "Moving/Copying vars")
        for var_id in var_id_list:
            progress.inc()
            var = self[var_id]

            var_sub_directory = None
            # Use preferred sub_directory
            if sub_directory == "AUTO":
                if var.incorrect_subdirectory:
                    var_sub_directory = var.preferred_subdirectory
            # Add sub_directory to the current sub_directory if not present
            elif append:
                if sub_directory not in var.sub_directory:
                    var_sub_directory = f"{sub_directory}{var.sub_directory}"
            elif suffix:
                if sub_directory not in var.sub_directory:
                    var_sub_directory = f"{var.sub_directory}_{sub_directory}"
            # Remove sub_directory from the current sub_directory if present
            elif remove:
                if sub_directory in var.sub_directory:
                    var_sub_directory = var.sub_directory.replace(sub_directory, Ext.EMPTY)
            # Move to a specific sub_directory
            else:
                if sub_directory != var.sub_directory:
                    var_sub_directory = sub_directory

            if var_sub_directory is not None:
                self.manipulate_file(
                    var.var_id,
                    path.join(var.root_path, var_sub_directory),
                    move=True,
                )

        if not self.disable_save:
            self.save()

    def dedupe_dependency_list(self, dependencies: set[str]) -> set[str]:
        # If an exact version is needed, we only need the exact reference, it will double as latest
        duplicates = set()
        for dependency in dependencies:
            if ".latest" not in dependency:
                if self.get_var_name_as_latest(dependency) in dependencies:
                    duplicates.add(self.get_var_name_as_latest(dependency))
        return dependencies - duplicates
