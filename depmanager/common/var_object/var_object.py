import json
from collections import defaultdict
from io import TextIOWrapper
from json import JSONDecodeError
from os import path
from typing import Any
from typing import List

from depmanager.common.enums.content_type import ContentType
from depmanager.common.enums.ext import Ext
from depmanager.common.enums.paths import FAVORITE
from depmanager.common.enums.variables import MEGABYTE
from depmanager.common.shared.cached_property import cached_property
from depmanager.common.parser.parser import VarParser
from depmanager.common.shared.ziptools import ZipRead
from depmanager.common.var_object.var_object_base import VarObjectBase
from depmanager.common.var_object.var_object_image_lib import VarObjectImageLib


class VarObject(VarObjectBase, VarObjectImageLib):
    contains: dict[str, bool]
    dependencies: list[str]
    var_type: ContentType
    infolist: list[tuple[str, int]]

    def __init__(
        self,
        root_path=None,
        file_path=None,
        info=None,
        contains=None,
        infolist=None,
        dependencies=None,
        used_packages=None,
        quick_scan=False,
    ):
        self.quick = quick_scan
        super().__init__(root_path, file_path, info)
        self.infolist = infolist if infolist is not None else self._var_raw_data["infolist"]
        self.dependencies = dependencies if dependencies is not None else self._var_raw_data["dependencies"]
        self.used_packages = used_packages if used_packages is not None else self._var_raw_data["used_packages"]
        self.contains = contains if contains is not None else ContentType.ref_from_namelist(self.namelist)
        self.var_type = ContentType(self.contains)
        self.favorite = False
        self.favorite_subdirectory = None

    def to_dict(self):
        return {
            "file_path": self.relative_path,
            "info": self.info,
            "contains": self.contains,
            "infolist": self.infolist,
            "dependencies": self.dependencies,
            "used_packages": {key: list(val) for key, val in self.used_packages.items()},
        }

    def from_new_path(self, root_path: str, file_path: str):
        """Will reinstantiate a new object but retain existing contents records"""
        return VarObject(
            root_path=root_path,
            file_path=file_path,
            info=None,
            contains=self.contains,
            infolist=self.infolist,
            dependencies=self.dependencies,
            used_packages=self.used_packages,
        )

    @classmethod
    def from_dict(cls, data, root_path=None):
        return VarObject(root_path=root_path, **data)

    @cached_property
    def _var_raw_data(self) -> dict[str, Any]:
        with ZipRead(self.file_path) as read_zf:
            # Load the infolist (file names and sizes)
            infolist = [(val.filename, val.file_size) for val in read_zf.infolist()]

            # Scan files for data
            dependencies = []
            used_packages = defaultdict(set)

            for item, _ in infolist:
                if path.splitext(item)[1].lower() in (Ext.JSON, Ext.VAP, Ext.VAJ):
                    try:
                        with TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                            if item == "meta.json":
                                json_data = json.loads(read_item.read())
                                dependencies = list(self._scan_keys_from_dict(json_data.get("dependencies")))
                            elif not self.quick:
                                packages = VarParser.scan_with_paths(read_item.readlines())
                                for package, package_paths in packages.items():
                                    used_packages[package].update(package_paths)
                    except JSONDecodeError as err:
                        raise ValueError(
                            f"ERROR: Var meta.json cannot be parsed >> {self.file_path}\nException: {repr(err)}"
                        ) from err

        return {"infolist": infolist, "dependencies": dependencies, "used_packages": used_packages}

    @cached_property
    def namelist(self) -> list[str]:
        return [val for val, _ in self.infolist]

    @property
    def is_scene_type(self):
        return self.var_type.type in self.var_type.types_with_json

    @property
    def is_look_type(self):
        return self.is_scene_type and ContentType.DIR_LOOK in self.sub_directory

    @cached_property
    def preferred_subdirectory(self) -> str:
        if self.is_custom:
            return self.var_type.DIR_CUSTOM

        contains_vartype_in_subdir = self.var_type.type in self.sub_directory
        contains_favorite_in_subdir = FAVORITE in self.sub_directory

        preferred_subdirectory = self.var_type.type_subdirectory
        if self.is_versioned:
            return self.sub_directory
        if self.is_scene_type:
            if ContentType.DIR_SCENE in self.sub_directory:
                return self.sub_directory
            if ContentType.DIR_LOOK in self.sub_directory:
                if not self.favorite:
                    return self.sub_directory
                if self.favorite and contains_favorite_in_subdir:
                    return self.sub_directory
                preferred_subdirectory = self.sub_directory
        else:
            if contains_vartype_in_subdir and not self.favorite:
                return self.sub_directory
            if contains_vartype_in_subdir and self.favorite and contains_favorite_in_subdir:
                return self.sub_directory

        if self.favorite:
            preferred_subdirectory = f"{preferred_subdirectory}_{FAVORITE}"

        return preferred_subdirectory

    @cached_property
    def incorrect_subdirectory(self) -> bool:
        return self.sub_directory != self.preferred_subdirectory

    @cached_property
    def prefer_symlink(self) -> bool:
        if self.var_type.is_symlink_type and self.info["size"] < 100 * MEGABYTE:
            return True
        return False

    @cached_property
    def dependencies_sorted(self) -> list[str]:
        return sorted(self.dependencies)

    @cached_property
    def used_dependencies(self) -> set[str]:
        used = set(self.used_packages)
        used.discard("SELF")
        used.discard("SELF_UNREF")
        used.discard(self.var_id)
        used.discard(self.id_as_latest)
        return used

    @cached_property
    def used_dependencies_sorted(self) -> list[str]:
        return sorted(self.used_dependencies)

    @cached_property
    def used_packages_as_list(self) -> list[tuple[str, str]]:
        used = []
        for package, package_files in self.used_packages.items():
            for package_file in package_files:
                used.append((package, package_file))
        return used

    @cached_property
    def includes_as_list(self) -> list[tuple[str, str, str]]:
        includes = []
        for row in self.namelist:
            if row != "meta.json" and len(path.splitext(row)[1]) > 0:
                includes.append((self.var_id, row, path.basename(row)))
        return includes

    @cached_property
    def json_like_files(self) -> list[str]:
        files = []
        for file in self.namelist:
            file_parts = path.splitext(file)
            if file_parts[1].lower() in (Ext.JSON, Ext.VAP, Ext.VAJ):
                if file == "meta.json" or "Custom/Scripts/" in file:
                    continue
                files.append(file)
        return files

    @cached_property
    def files(self) -> defaultdict[str, set[str]]:
        files = defaultdict(set)
        for file in self.namelist:
            file_parts = path.splitext(file)
            file_path = file_parts[0].lower()
            extension = file_parts[1].lower()
            if extension == Ext.JSON:
                if "Saves" in file:
                    files["saves"].add(file.replace(Ext.JSON, Ext.EMPTY))
            elif extension == Ext.VAP:
                if "appearance" in file_path:
                    files["appearance"].add(file.replace(Ext.VAP, Ext.EMPTY))
                elif "clothing" in file_path:
                    files["clothing_vap"].add(file.replace(Ext.VAP, Ext.EMPTY))
                elif "hair" in file_path:
                    files["hair_vap"].add(file.replace(Ext.VAP, Ext.EMPTY))
            elif extension == Ext.VAM:
                if "clothing" in file_path:
                    files["clothing"].add(file.replace(Ext.VAM, Ext.EMPTY))
                elif "hair" in file_path:
                    files["hair"].add(file.replace(Ext.VAM, Ext.EMPTY))
            elif extension == Ext.JPG:
                files["images"].add(file.replace(Ext.JPG, Ext.EMPTY).replace(Ext.JPG.upper(), Ext.EMPTY))
            elif extension == Ext.PNG:
                files["images_png"].add(file.replace(Ext.PNG, Ext.EMPTY).replace(Ext.PNG.upper(), Ext.EMPTY))
        return files

    def _scan_keys_from_dict(self, dependencies) -> set:
        required_dependencies = set()
        for key, value in dependencies.items():
            # Recursively call this to get nested dependencies
            if value.get("dependencies"):
                required_dependencies.update(self._scan_keys_from_dict(value["dependencies"]))
            required_dependencies.add(key)
        return required_dependencies

    def tag_as_favorite(self, favorites: List[str]):
        if self.author in favorites:
            self.favorite = True
