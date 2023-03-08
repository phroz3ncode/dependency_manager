import copy
import os
from os import path

from depmanager.common.shared.cached_property import cached_property
from depmanager.common.var_services.enums import Ext


class VarObjectBase:
    INFO = {
        "created": None,
        "modified": None,
        "size": None,
    }

    root_path: str
    relative_path: str
    info: dict

    def __init__(
        self,
        root_path=None,
        file_path=None,
        info=None,
    ):
        self.root_path = root_path
        self.original_file_path = file_path
        self.info = info

        if self.info is None:
            self.info = copy.deepcopy(self.INFO)
            self.update_info()

    @cached_property
    def file_path(self) -> str:
        return path.join(self.root_path, self.relative_path)

    @cached_property
    def relative_path(self) -> str:
        try:
            return path.relpath(self.original_file_path, self.root_path)
        except ValueError:
            return self.original_file_path

    @cached_property
    def directory(self) -> str:
        return path.dirname(self.file_path)

    @cached_property
    def root_directory(self) -> str:
        return path.abspath(path.join(self.directory, "../.."))

    @cached_property
    def sub_directory(self) -> str:
        return path.split(self.relative_path)[0]

    @cached_property
    def filename(self) -> str:
        return path.basename(self.file_path)

    @cached_property
    def clean_name(self) -> str:
        return path.basename(self.file_path).replace(Ext.VAR, Ext.EMPTY)

    @cached_property
    def _filename_parts(self) -> list[str]:
        parts = self.filename.split(".")
        if len(parts) != 4:
            raise ValueError(f"Var name is invalid. {self.file_path}")
        return parts

    @cached_property
    def author(self) -> str:
        return self._filename_parts[0]

    @cached_property
    def package_name(self) -> str:
        return self._filename_parts[1]

    @cached_property
    def version(self) -> int:
        return int(self._filename_parts[2])

    @cached_property
    def var_id(self) -> str:
        return f"{self.author}.{self.package_name}.{self.version}"

    @cached_property
    def id_as_latest(self) -> str:
        return f"{self.author}.{self.package_name}.latest"

    @cached_property
    def duplicate_id(self) -> str:
        return f"{self.author}.{self.package_name}"

    @cached_property
    def exists(self) -> bool:
        return path.exists(self.file_path)

    @cached_property
    def is_versioned(self) -> bool:
        return "versioned" in self.directory

    @cached_property
    def is_vamx(self) -> bool:
        return str.lower(self.author) == "vamx"

    @cached_property
    def is_custom(self) -> bool:
        return str.lower(self.author) == "custom"

    @property
    def updated(self) -> bool:
        stats = os.stat(self.file_path)
        if (
            self.info["created"] != stats.st_ctime
            or self.info["modified"] != stats.st_mtime
            or self.info["size"] != stats.st_size
        ):
            return True
        return False

    def update_info(self) -> None:
        stats = os.stat(self.file_path)
        self.info["created"] = stats.st_ctime
        self.info["modified"] = stats.st_mtime
        self.info["size"] = stats.st_size
