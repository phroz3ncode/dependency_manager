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


class FileDatabase:
    INCLUDE_LIST = ["var"]
    EXCLUDE_LIST = ["disabled"]
    APPEARANCE_LIST = ["json", "vap"]

    def __init__(self, root: str = None):
        self.rootpath = root
        self._directory_files = None

    def refresh(self) -> None:
        # Cache must be cleared to perform a clean scan
        self._directory_files = None

    @property
    def directory_count(self):
        return len(self.directory_files)

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

    @property
    def directory_files(self) -> list[tuple[str, float, float]]:
        if self._directory_files is None:
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
            except BufferError:
                print("Failed to secure buffer...")
                files_with_stats = list(get_file_stat(file) for file in files)

            self._directory_files = files_with_stats

        return self._directory_files

    def ignore_directory(self, dirpath: str) -> bool:
        return IMAGE_LIB_DIR in dirpath or REPAIR_LIB_DIR in dirpath or "_ignore" in dirpath