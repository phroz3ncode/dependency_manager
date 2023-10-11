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
from typing import Dict
from typing import List
from typing import Optional

from orjson import orjson

from depmanager.common.enums.ext import Ext
from depmanager.common.enums.paths import IMAGE_LIB_DIR
from depmanager.common.enums.paths import REPAIR_LIB_DIR
from depmanager.common.enums.variables import TEMP_VAR_NAME
from depmanager.common.shared.cached_object import CachedObject
from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import get_file_stat
from depmanager.common.var_object.var_object import VarObject


class VarDatabaseBase(CachedObject):
    INCLUDE_LIST = ["var"]
    EXCLUDE_LIST = ["disabled"]
    APPEARANCE_LIST = ["json", "vap"]

    rootpath: str
    root_db: str
    vars: Dict[str, VarObject]
    quick_scan: bool
    scanned: bool

    def __init__(self, root: str = None, quick_scan: bool = False, favorites: List[str] = None):
        self._files_added_or_removed = False

        self.rootpath = root
        self.root_db = "remote_db.json"
        self.vars = {}
        self.quick_scan = quick_scan
        self.favorites = favorites if favorites else []

        self.load()

    def __len__(self):
        return len(self.vars)

    def __getitem__(self, item):
        return self.vars.get(item)

    def __setitem__(self, key, value):
        self.vars[key] = value

    @property
    def _attributes(self):
        return [
            "directory_files",
            "vars_directory_files",
            "vars_versions",
        ]

    def refresh(self) -> None:
        # Cache must be cleared to perform a clean scan
        self.clear()
        self.remove_files()
        self.add_files()

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
        except (BrokenPipeError, BufferError):
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
        # Removing pretty-printing to improve performance
        return orjson.dumps(
            {"rootpath": self.rootpath, "vars": [v.to_dict() for _, v in self.vars.items()]}, option=orjson.OPT_INDENT_2
        ).decode("UTF-8")

    def save(self) -> None:
        if self._files_added_or_removed:
            print(f"Saving database {self.root_db_path}")
            with open(self.root_db_path, "w", encoding="UTF-8") as write_db_file:
                write_db_file.write(self.to_json())
            self._files_added_or_removed = False
            attributes = [a for a in self._attributes if a != "directory_files"]
            self.clear(attributes)

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
                        var.tag_as_favorite(self.favorites)
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
            var.tag_as_favorite(self.favorites)
            self[var.var_id] = var
            self._files_added_or_removed = True
        except (ValueError, KeyError, PermissionError, zipfile.BadZipfile) as err:
            print(f"ERROR :: Could not read {file_path} >> {err}")

    def add_file(self, file_path: str, filemod=None, filesize=None):
        if "temp.temp.1.var" in file_path:
            return

        var = self.get_var_from_filepath(file_path)
        if var is not None:
            if var.file_path != file_path:
                print(f"Warning: {file_path} is a duplicate var")
                return
            if (filemod != var.modified and filesize != var.size) or (
                (filemod is None or filesize is None) and var.updated
            ):
                print(f"Updating: {var.var_id}")
                self.update_var(file_path)
            return

        self.update_var(file_path)

    def add_files(self) -> None:
        progress = ProgressBar(self.directory_count, description="Scanning vars")
        for filepath, filemod, filesize in self.directory_files:
            progress.inc()
            self.add_file(filepath, filemod, filesize)

    def remove_files(self) -> None:
        files = self.directory_files
        present_files = set(f[0] for f in files)
        current_var_files = self.vars_directory_files
        removed_files = current_var_files - present_files
        if len(removed_files) > 0:
            self._files_added_or_removed = True

        for var_path in sorted(removed_files):
            var = self.get_var_from_filepath(var_path).var_id
            print(f"Removing: {var}")
            self.vars.pop(var)

    def manipulate_file(self, var_id, dest_dir, move=False, symlink=False, track_move=True) -> None:
        os.makedirs(dest_dir, exist_ok=True)

        var = self[var_id]
        src_path = var.file_path
        dest_path = path.join(dest_dir, var.filename)

        if not path.isfile(src_path):
            print(f"Var not found on disk: {var_id} [Please refresh remote or local database]")
        if move:
            self._files_added_or_removed = track_move
            os.rename(src_path, dest_path)
            self[var.var_id] = self[var.var_id].from_new_path(self.rootpath, dest_path)
        elif symlink and var.prefer_symlink:
            if not path.isfile(dest_path):
                self._files_added_or_removed = track_move
                try:
                    os.symlink(src_path, dest_path)
                except WindowsError:
                    shutil.copy2(src_path, dest_path)
        else:
            if not path.isfile(dest_path):
                self._files_added_or_removed = track_move
                shutil.copy2(src_path, dest_path)

    def manipulate_file_list(
        self, var_id_list, sub_directory, append=False, remove=False, suffix=False, desc=None
    ) -> None:
        if len(var_id_list) == 0:
            return

        if desc is None:
            desc = "Moving/Copying vars"

        progress = ProgressBar(len(var_id_list), desc)
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
                    var_sub_directory = f"{sub_directory}_{var.sub_directory}"
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

    def dedupe_dependency_list(self, dependencies: set[str]) -> set[str]:
        # If an exact version is needed, we only need the exact reference, it will double as latest
        removals = set()
        additions = set()
        for dependency in dependencies:
            # If the current dependency is hardcoded but there is also a "latest" version in dependencies
            if ".latest" not in dependency and self.get_var_name_as_latest(dependency) in dependencies:
                removals.add(self.get_var_name_as_latest(dependency))

                # We need to check if the latest version is actually the newest, and if so add the newest
                latest_var_id = self.get_var_name(self.get_var_name_as_latest(dependency))
                if dependency not in self.vars or self.vars[dependency].version < self.vars[latest_var_id].version:
                    additions.add(latest_var_id)

        dependencies = dependencies - removals
        dependencies = dependencies.union(additions)
        return dependencies
