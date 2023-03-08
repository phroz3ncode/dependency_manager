import io
import json
import os
import shutil
import zipfile
from collections import defaultdict
from json import JSONDecodeError
from os import path
from typing import Optional

from orjson import orjson

from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import find_fuzzy_file_match
from depmanager.common.shared.tools import select_fuzzy_match
from depmanager.common.var_services.entities.var_object import VarObject
from depmanager.common.var_services.enums import BACKWARDS_COMPAT_PLUGIN_AUTHORS
from depmanager.common.var_services.enums import IMAGE_LIB_DIR
from depmanager.common.var_services.enums import REPAIR_LIB_DIR
from depmanager.common.var_services.enums import TEMP_VAR_NAME
from depmanager.common.var_services.enums import Ext
from depmanager.common.var_services.utils.var_parser import VarParser
from depmanager.common.var_services.utils.var_type import VarType


class VarDatabase:
    INCLUDE_LIST = ["var"]
    EXCLUDE_LIST = ["disabled"]
    APPEARANCE_LIST = ["json", "vap"]

    rootpath: str
    root_db: str
    vars: dict[str, VarObject]
    disable_save: bool

    # pylint: disable=redefined-builtin
    def __init__(self, root: str = None, disable_save: bool = False, quick_scan: bool = False):
        self.rootpath = root
        self.root_db = "remote_db.json"
        self.vars = {}
        self.disable_save = disable_save
        self.quick_scan = quick_scan

        self.load()

    def __len__(self):
        return len(self.vars)

    def __getitem__(self, item):
        return self.vars.get(item)

    def __setitem__(self, key, value):
        self.vars[key] = value

    @property
    def keys(self):
        return set(self.vars.keys())

    def to_json(self) -> str:
        return orjson.dumps(
            {"rootpath": self.rootpath, "vars": [v.to_dict() for _, v in self.vars.items()]}, option=orjson.OPT_INDENT_2
        ).decode("UTF-8")

    def save(self) -> None:
        print(f"Saving database {self.root_db_path}")
        with open(self.root_db_path, "w", encoding="UTF-8") as write_db_file:
            write_db_file.write(self.to_json())

    def load(self):
        if not path.exists(self.root_db_path):
            self.add_files()
        else:
            try:
                print(f"Loading default database {self.root_db_path}")
                with open(self.root_db_path, "r", encoding="UTF-8") as read_db_file:
                    data = json.load(read_db_file)
                    for item in data["vars"]:
                        var = VarObject.from_dict(data=item, root_path=self.rootpath)
                        self[var.var_id] = var
            except JSONDecodeError:
                self.add_files()

    def _clear_cache(self):
        cached_properties = [
            "directory_count",
            "directory_listing",
            "vars_versions",
            "vars_required",
            "repair_index",
            "required_dependencies",
        ]
        for property in cached_properties:
            try:
                delattr(self, property)
            except AttributeError:
                continue

    @property
    def root_db_path(self):
        return path.join(self.rootpath, self.root_db)

    @property
    def directory_count(self):
        return sum(len(item) for _, item in self.directory_listing.items())

    @cached_property
    def directory_listing(self) -> defaultdict[str, list]:
        dir_listing = defaultdict(list)
        for (dirpath, _, filenames) in os.walk(self.rootpath):
            if self.ignore_directory(dirpath):
                continue
            dir_listing[dirpath].extend(f for f in filenames if Ext.VAR in f)
        return dir_listing

    @cached_property
    def vars_versions(self) -> defaultdict[str, set]:
        versions = defaultdict(set)
        for _, var in self.vars.items():
            versions[var.duplicate_id].add(var.version)
        return versions

    @cached_property
    def vars_required(self) -> defaultdict[str, list]:
        required = defaultdict(list)
        for _, var in self.vars.items():
            if len(var.dependencies) > 0:
                for dependency in var.dependencies:
                    var_name = self.get_var_name(dependency, always=True)
                    if var_name is not None:
                        required[var_name].append(var.var_id)
        return required

    @cached_property
    def reference_file_uses(self) -> list[tuple[str, int]]:
        refs = defaultdict(int)
        for var_id in self.keys:
            for package, package_path in self[var_id].used_packages_as_list:
                if package in ("SELF", "SELF_UNREF"):
                    continue
                refs[f"{package}:::{package_path}"] += 1
        return list(sorted(refs.items(), key=lambda item: item[1], reverse=True))

    @cached_property
    def reference_package_uses(self) -> list[tuple[str, int]]:
        refs = defaultdict(int)
        for package, uses in self.reference_file_uses:
            refs[package.split(":::")[0]] += uses
        return list(sorted(refs.items(), key=lambda item: item[1], reverse=True))

    @cached_property
    def reference_author_uses(self) -> list[tuple[str, int]]:
        refs = defaultdict(int)
        for package, uses in self.reference_file_uses:
            refs[package.split(".")[0]] += uses
        return list(sorted(refs.items(), key=lambda item: item[1], reverse=True))

    @cached_property
    # pylint: disable=consider-using-dict-items
    def repair_index(self) -> list[tuple[str, str, str]]:
        """Builds a repair index

        We sort by the following:
            - VarType.REFERENCE_PRIORITY (this is how likely the item is to be a base reference, not part of a scene)
            - Is the item used as a reference by other vars? If so it is preferred to an unused item
            - Name of the var (if the name is a well known resource maker, we append a . to bubble them to the top)
            - Version (we prioritize newer versions over old versions, so the sort version is 10000 - version)

        After sorting we unpack all the items and quickly convert them to lowercase for searching later on.
        """
        max_top_refs = 50
        top_references = [x for x, _ in self.reference_author_uses][:max_top_refs]

        indexes = []
        for var_id in self.keys:
            # Define the methods we will sort on
            priority_sort = self[var_id].var_type.reference_priority
            used_sort = 0 if var_id in self.vars_required.keys() else 1
            try:
                top_sort = top_references.index(self[var_id].author)
            except ValueError:
                top_sort = max_top_refs + 1
            name_sort = self[var_id].duplicate_id
            version_sort = 10000 - self[var_id].version

            # Add the list of files along with the sort ordering
            indexes.append((priority_sort, used_sort, top_sort, name_sort, version_sort, self[var_id].includes_as_list))

        # Sort based on the initial keys
        indexes.sort(key=lambda x: (x[0], x[1], x[2], x[3], x[4]))

        # Extract the includes only and convert to lower, drop the sort keys
        return [(item[0], item[1], item[2]) for sublist in indexes for item in sublist[5]]

    @cached_property
    def required_dependencies(self) -> defaultdict[str, set]:
        """Logic to retrieve all required dependencies"""
        required = defaultdict(set)
        progress = ProgressBar(len(self.vars), description="Building dependency map")
        # Using .items negates the cached_property benefits
        # pylint: disable=consider-using-dict-items
        for var_id in self.vars:
            progress.inc()

            # Quick scan databases do not scan every file to build a complete used_dependencies entity
            # The listed dependencies may or may not be accurate, but without a full scan this cannot
            # be determined, so we should assume what is listed is the minimum we need
            if self.quick_scan:
                required[var_id] = set(self[var_id].dependencies)
            # If we have a full scan, then we can determine the chain of any dependencies that would ever be
            # touched by a var. This is determined on the fly based on the current states of all stored
            # numbered and latest entities known to the database.
            else:
                dependencies = set(self[var_id].used_dependencies)

                # Need to collect all the associated dependencies
                while True:
                    additional_dependencies = set()
                    for dependency in dependencies:
                        dep_id = self.get_var_name(dependency)
                        # If the dep_id is none, the var is obviously broken, but we should not
                        # crash during this check. This can be detected and fixed with other methods
                        # later on.
                        if dep_id is None:
                            continue
                        additional_dependencies.update(self[dep_id].used_dependencies)
                    new_dependencies = additional_dependencies - dependencies
                    if len(new_dependencies) == 0:
                        break
                    dependencies.update(new_dependencies)

                # If an exact version is needed, we only need the exact reference, it will double as latest
                # duplicates = set()
                # for dependency in dependencies:
                #     if ".latest" not in dependency:
                #         if self.get_var_name_as_latest(dependency) in dependencies:
                #             duplicates.add(self.get_var_name_as_latest(dependency))

                required[var_id] = dependencies

        return required

    @cached_property
    def unique_required_dependencies(self) -> set[str]:
        unique_dependencies = set()
        for var_id, var_required_dependencies in self.required_dependencies.items():
            unique_dependencies.add(var_id)
            for dependency in var_required_dependencies:
                unique_dependencies.add(dependency)
        return unique_dependencies

    @cached_property
    def unique_referenced_dependencies(self) -> set[str]:
        unique_referenced = set()
        for _, var_required_dependencies in self.required_dependencies.items():
            for dependency in var_required_dependencies:
                var_name = dependency if ".latest" not in dependency else self.get_var_name(dependency)
                if var_name is not None:
                    unique_referenced.add(var_name)
        return unique_referenced

    def dedupe_dependency_list(self, dependencies: set[str]) -> set[str]:
        # If an exact version is needed, we only need the exact reference, it will double as latest
        duplicates = set()
        for dependency in dependencies:
            if ".latest" not in dependency:
                if self.get_var_name_as_latest(dependency) in dependencies:
                    duplicates.add(self.get_var_name_as_latest(dependency))
        return dependencies - duplicates

    def ignore_directory(self, dirpath: str) -> bool:
        return IMAGE_LIB_DIR in dirpath or REPAIR_LIB_DIR in dirpath or "_ignore" in dirpath

    def update_var(self, file_path):
        try:
            var = VarObject(root_path=self.rootpath, file_path=file_path, quick=self.quick_scan)
            self[var.var_id] = var
        except (ValueError, KeyError, PermissionError, zipfile.BadZipfile) as err:
            print(f"ERROR :: Could not read {file_path} >> {err}")

    def add_file(self, file_path, quick=False) -> bool:
        filename = path.basename(file_path)
        filename_ext = path.splitext(filename)[-1]
        if filename_ext != Ext.VAR:
            return False
        # If we find a temp var, we should destroy it
        if filename == TEMP_VAR_NAME:
            print(f"Removing temp var: {file_path}")
            os.remove(file_path)
            return False
        var = self.vars.get(filename.replace(Ext.VAR, Ext.EMPTY))
        if var is not None:
            if var.file_path == file_path:
                if quick or (not quick and not var.updated):
                    return False
                if var.updated:
                    print(f"Updating: {var.var_id}")
                    self.update_var(file_path)
                    return True
            print(f"Warning: {file_path} is a duplicate var")
            return False

        self.update_var(file_path)
        return True

    def add_files(self, quick=False, files_removed=False) -> None:
        new_files_added = False
        progress = ProgressBar(self.directory_count, description="Scanning vars")
        for (dirpath, _, filenames) in os.walk(self.rootpath):
            if self.ignore_directory(dirpath):
                continue
            for file_to_add in filenames:
                progress.inc()
                file_added = self.add_file(path.join(dirpath, file_to_add), quick=quick)
                if file_added:
                    new_files_added = True
        if not self.disable_save and (new_files_added or files_removed):
            self.save()

    def remove_files(self, display=True) -> bool:
        remove_vars = []
        progress = ProgressBar(len(self.keys), description="Scanning for removed")
        files_removed = False
        for var_id, var in self.vars.items():
            progress.inc()
            if var.filename not in self.directory_listing.get(var.directory, {}):
                files_removed = True
                remove_vars.append(var_id)

        if display:
            for var in sorted(remove_vars):
                print(f"Removing: {var}")
                self.vars.pop(var)
        return files_removed

    def get_var_ids_from_deps(self) -> set[str]:
        var_files = set()
        for (dirpath, _, filenames) in os.walk(self.rootpath):
            if self.ignore_directory(dirpath):
                continue
            for filename in filenames:
                if Ext.DEP in filename:
                    with open(path.join(dirpath, filename), encoding="UTF-8") as file:
                        lines = [line.rstrip().replace(Ext.VAR, Ext.EMPTY) for line in file]
                        var_files.update(lines)
        return var_files

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
                    shutil.copyfile(src_path, dest_path)
        else:
            if not path.isfile(dest_path):
                shutil.copyfile(src_path, dest_path)

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

    def refresh_files(self, quick=False) -> None:
        self._clear_cache()
        files_removed = self.remove_files()
        self.add_files(quick=quick, files_removed=files_removed)

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

    def get_dependencies_list_as_dict(self, dependency_list):
        dependencies = {}
        for dependency in sorted(dependency_list):
            package_id = self.get_var_name(dependency)
            if package_id is None:
                raise ValueError(f"ERROR {dependency}")
            dependencies[dependency] = {
                "licenseType": "FC",
                "dependencies": {},
            }
        return dependencies

    @staticmethod
    def get_var_name_as_latest(var_id):
        return f"{'.'.join(var_id.split('.')[:-1])}.latest"

    def display_var_list(self, var_id_list, prefix, show_used_by=False) -> None:
        if len(var_id_list) > 0:
            for var in sorted(var_id_list):
                if show_used_by:
                    used_by = self.vars_required.get(var)
                    print(f"{prefix} var detected: {var} - {used_by}")
                else:
                    print(f"{prefix} var detected: {var}")
        else:
            print(f"No {prefix.lower()} vars detected.")

    def find_unversioned_duplicates(self) -> set[str]:
        unversioned_duplicates = set()
        progress = ProgressBar(len(self.vars_versions.keys()), "Searching for unversioned duplicates")
        for var_name, versions in self.vars_versions.items():
            progress.inc()
            if len(versions) <= 1:
                continue

            max_version = max(versions)
            for version in versions:
                var_id = f"{var_name}.{version}"
                if version < max_version:
                    if "versioned" not in self[var_id].sub_directory:
                        unversioned_duplicates.add(var_id)
                else:
                    if "versioned" in self[var_id].sub_directory:
                        print(f"WARNING: Latest version of {var_id} is in versioned folder")
        return unversioned_duplicates

    def find_missing_vars(self) -> set[str]:
        missing_vars = set()
        progress = ProgressBar(len(self.keys), "Searching for missing vars")
        for var_id in self.unique_required_dependencies:
            progress.inc()
            if self.get_var_name(var_id) is None:
                missing_vars.add(var_id)
        return missing_vars

    def find_missing_dep_vars(self) -> set[str]:
        required_dep_vars = self.get_var_ids_from_deps()

        missing_vars = set()
        progress = ProgressBar(len(required_dep_vars), "Searching for missing .dep vars")
        for var in required_dep_vars:
            progress.inc()
            var_name = self.get_var_name(var)
            if var_name is None:
                missing_vars.add(var)
        return missing_vars

    def find_unused_vars(self, filters=None, invert=False) -> set[str]:
        # Get the unused vars
        var_list = self.keys - set(self.unique_referenced_dependencies)
        if invert:
            var_list = self.keys - var_list
        if filters is not None:
            if not isinstance(filters, list):
                raise ValueError("Filter must be a list")
            filters = [f.strip() for f in filters]
            var_list = {v for v in var_list if any(f for f in filters if f in self[v].sub_directory)}
        return set(var_list)

    def find_removed_unused_vars(self, filters=None) -> set[str]:
        print("Searching for vars that will no longer be used...")

        # Using .items negates the cached_property benefits
        # pylint: disable=consider-using-dict-items
        removed_vars = {v for v in self.vars if any(f for f in filters if f in self[v].sub_directory)}

        # Find the vars that are used by the vars being removed
        used_dependencies = set()
        for var_id in removed_vars:
            if len(self[var_id].dependencies) > 0:
                used_dependencies.update(self[var_id].dependencies)
        used_dependencies = {self.get_var_name(v, always=True) for v in used_dependencies}
        used_dependencies_lower = [v.lower() for v in used_dependencies]

        required_vars = {
            var_id: var_list
            for var_id, var_list in self.vars_required.items()
            if var_id.lower() in used_dependencies_lower
        }

        # Now simulate removing all these vars
        no_longer_used = set()
        removed_vars_lower = [v.lower() for v in removed_vars]
        for var_id, used_by_list in required_vars.items():
            used_by_list = [v for v in used_by_list if v.lower() not in removed_vars_lower]
            if len(used_by_list) == 0:
                no_longer_used.add(var_id)

        # Remove self references
        no_longer_used = {v for v in no_longer_used if v not in removed_vars}

        # Do not return vars already flagged for removal
        no_longer_used = {v for v in no_longer_used if "removed" not in self[v].sub_directory}

        return no_longer_used

    def find_unoptimized_vars(self):
        var_list = set()
        progress = ProgressBar(len(self.keys), description="Searching unoptimized vars")
        for var_id, var in self.vars.items():
            progress.inc()
            # This is a big change not made lightly. Ultimately if a single var tracks every change to all
            # downstream vars, when you have a ".latest" var that gets updated and adds or upgrades a new
            # dependency this can result in a MASSIVE need for downstream updates to fix all the metadata.
            # The native handling of this by storing everything in meta.json just doesn't work well.
            # As a result we should only store the actual "used_dependencies". During local synchronization,
            # we can ensure that everything is brought down properly.
            if var.dependencies_sorted != var.used_dependencies_sorted:
                var_list.add(var_id)
        return var_list

    def repair_metadata(self, var_ref: VarObject):

        print(f"CHECKING METADATA {var_ref.var_id}...")
        var_obj = VarObject(var_ref.root_path, var_ref.file_path)

        failed = False
        if var_obj.dependencies_sorted == var_obj.used_dependencies_sorted:
            return

        added = len(set(var_obj.used_dependencies_sorted).difference(var_obj.dependencies))
        removed = len(set(var_obj.dependencies).difference(var_obj.used_dependencies_sorted))
        action = f"Adding {added} dependencies. Removing {removed} dependencies."
        print(f"OPTIMIZING {var_obj.var_id}... {action}")

        temp_file = path.join(var_obj.directory, TEMP_VAR_NAME)
        with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as zf_dest:
            with zipfile.ZipFile(var_obj.file_path, "r") as read_zf:
                for item in read_zf.infolist():
                    if item.filename == "meta.json":
                        with io.TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                            meta = json.loads(read_item.read())
                            # Fix the contentList
                            meta["contentList"] = [
                                r for r in var_obj.namelist if r != "meta.json" and len(path.splitext(r)[1]) > 1
                            ]
                            meta["dependencies"] = self.get_dependencies_list_as_dict(var_obj.used_dependencies_sorted)
                            meta_data = orjson.dumps(meta, option=orjson.OPT_INDENT_2).decode("UTF-8")
                            zf_dest.writestr(item.filename, meta_data, zipfile.ZIP_DEFLATED)
                    else:
                        zf_dest.writestr(item.filename, read_zf.read(item.filename), zipfile.ZIP_DEFLATED)

        if failed:
            os.remove(temp_file)
        else:
            os.remove(var_obj.file_path)
            os.rename(temp_file, var_obj.file_path)

    def find_broken_vars(self):
        var_list = set()
        progress = ProgressBar(len(self.keys), description="Searching broken vars")
        track = {}
        for var_id in self.keys:
            progress.inc()
            replacement_mappings, _ = self.find_var_replacement_mappings(self[var_id])
            if len(replacement_mappings) > 0:
                var_list.add(var_id)
                track.update(replacement_mappings)
        return var_list

    def find_replacement_from_repair_index(self, filepath: str, exact_only=False):
        """Find the best occurrences from self.repair_index. The repair index is sorted
        such that the most preferable references will be hit first by next
        """
        # Attempt to return the first (best) exact match
        search_val = filepath.lower()
        result = next((index for index in self.repair_index if index[1].lower() == search_val), None)
        if result is not None:
            return result[0], result[1]

        # If exact only mode, don't attempt to fuzzy match
        if exact_only:
            return None, None

        # Attempt to return the best filename match
        search_val = path.basename(filepath).lower()
        found_approx = list((index[0], index[1]) for index in self.repair_index if index[2].lower() == search_val)
        return select_fuzzy_match(filepath, found_approx)

    def should_update_file_to_fixed(self, package: str) -> bool:
        var_package = self.vars.get(self.get_var_name(package))
        if var_package is None:
            return False

        if var_package.var_type.type == VarType.PLUGIN and var_package.author not in BACKWARDS_COMPAT_PLUGIN_AUTHORS:
            return True

        return False

    def should_update_file_to_latest(self, package: str, package_file: str) -> bool:
        package_parts = package.split(".")
        if len(package_parts) != 3:
            return False

        if package_parts[2] == "latest":
            return False

        var_package = self.vars.get(self.get_var_name(package))
        if var_package is None:
            return False

        if var_package.var_type.type == VarType.PLUGIN and var_package.author not in BACKWARDS_COMPAT_PLUGIN_AUTHORS:
            return False

        latest_version = max(self.vars_versions.get(var_package.duplicate_id))
        if package_parts[2] == latest_version:
            return True

        var_check_package_latest = self.vars[f"{var_package.duplicate_id}.{latest_version}"]
        if var_package is None:
            return False

        if package_file in var_check_package_latest.namelist:
            return True

        return False

    def get_name_and_version(self, var_id):
        package_parts = var_id.split(".")
        return f"{package_parts[0]}.{package_parts[1]}", package_parts[2]

    def find_var_replacement_mappings(self, var_obj: VarObject):
        mappings = self.find_broken_replacement_mappings(var_obj)

        # If no mappings, there is nothing to do
        if len(mappings) == 0:
            return {}, set()

        # Collect the versions used in the package
        mapping_versions = defaultdict(set)
        for _, package, version, _ in mappings:
            if version is not None:
                mapping_versions[package].add(str(version))

        has_multiple_versions = any(len(val) > 1 for _, val in mapping_versions.items())

        # If there are no replacements, and each package only has 1 version, there is nothing to do
        if has_multiple_versions:
            mappings = self.optimize_multiple_versions(mappings, mapping_versions)

        replacement_mappings = {
            key: f"{package}.{version}:/{package_file}" if package is not None else None
            for (key, package, version, package_file) in mappings
            if key is not None
        }
        replacement_mappings = {key: val for key, val in replacement_mappings.items() if key != val}
        used_packages = set(
            f"{package}.{version}" for (_, package, version, _) in mappings if package != "SELF" and package is not None
        )
        return replacement_mappings, used_packages

    def optimize_multiple_versions(self, mappings, mapping_versions):
        def replace_mapping(mappings, package, version):
            new_mappings = set()
            for map in mappings:
                if map[1] != package:
                    new_mappings.add(map)
                    continue
                replace_key = f"{map[1]}.{map[2]}:/{map[3]}" if map[0] is None else map[0]
                new_mappings.add((replace_key, map[1], version, map[3]))
            return new_mappings

        # The package is currently referencing > 1 version. If possible this should be reduced to a single version
        for package, versions in mapping_versions.items():
            # We don't need to "fix" any mappings with only one version
            if len(versions) == 1:
                continue

            # These are the files being referenced from this package
            files_from_package = set(file[3] for file in mappings if file[1] == package)

            # If we are using code/plugin, we want to try and have everything on one version
            if (
                len(
                    list(file for file in files_from_package if path.splitext(file)[1] in (Ext.CS, Ext.CSLIST, Ext.DLL))
                )
                > 0
            ):
                if package.split(".") in BACKWARDS_COMPAT_PLUGIN_AUTHORS:
                    versions = sorted(versions, reverse=True)
                else:
                    versions = sorted(versions)
                for ver in versions:
                    check_package = self.vars.get(self.get_var_name(f"{package}.{ver}"))
                    if all(file in check_package.namelist for file in files_from_package):
                        mappings = replace_mapping(mappings, package, ver)
                        break
                continue

            # Try to update everything to the latest version
            ver = sorted(versions, reverse=True)[0]
            check_package = self.vars.get(self.get_var_name(f"{package}.{ver}"))
            if all(file in check_package.namelist for file in files_from_package):
                mappings = replace_mapping(mappings, package, ver)

            assert True

        return mappings

    def find_broken_replacement_mappings(self, var_obj: VarObject):
        """Check the var for replacement references"""
        mappings = set()
        # Check each file that is used by the current var
        for check_package, check_package_file in var_obj.used_packages_as_list:
            replace_key = (
                check_package_file if check_package == "SELF_UNREF" else f"{check_package}:/{check_package_file}"
            )
            replace_key = replace_key.replace("::", ":/")
            # If the file is in the local package and uses SELF
            if check_package == "SELF" and check_package_file in var_obj.namelist:
                continue

            # If the file is in the local package but does NOT use SELF
            if check_package_file in var_obj.namelist:
                mappings.add((replace_key, "SELF", None, check_package_file))
                continue

            # If there is a valid external package
            var_check_package = self.vars.get(self.get_var_name(check_package))
            if var_check_package is not None and check_package_file in var_check_package.namelist:
                # If the package should be a fixed version and not latest
                if self.should_update_file_to_fixed(check_package):
                    mappings.add(
                        (replace_key, var_check_package.duplicate_id, var_check_package.version, check_package_file)
                    )
                    continue

                # If package should be update to be latest instead of direct reference
                if self.should_update_file_to_latest(check_package, check_package_file):
                    mappings.add((replace_key, var_check_package.duplicate_id, "latest", check_package_file))
                    continue

                version = "latest" if "latest" in check_package else var_check_package.version
                mappings.add((None, var_check_package.duplicate_id, version, check_package_file))
                continue

            # The reference is invalid, search to replace it
            found_id, found_path = self.find_replacement_from_repair_index(check_package_file)
            if found_id is None and check_package in ("SELF", "SELF_UNREF"):
                # Attempt a local fuzzy replacement (maybe the file is misspelled)
                found_id, found_path = find_fuzzy_file_match(check_package_file, var_obj.includes_as_list, threshold=3)

            # There are no suitable replacements, the reference must be removed
            if found_id is None:
                mappings.add((replace_key, None, None, None))
                continue

            # If found a suitable local replacement
            if found_id in (var_obj.var_id, "SELF"):
                mappings.add((replace_key, "SELF", None, found_path))
                continue

            # If should update the found replacement to latest
            author, var_name, version = found_id.split(".")
            if self.should_update_file_to_latest(found_id, found_path):
                version = "latest"

            # Replace the key
            mappings.add((replace_key, f"{author}.{var_name}", version, found_path))

        return mappings

    def repair_broken_var(self, var_ref: VarObject, remove_confirm=False) -> bool:
        # var_ref is from the local_db typically and is a quick load
        # This means it will not contain a detailed mapping of the var contents
        # We want to create a new object to make sure repairs are accurate by rescanning the local
        # object fully with the VarParser. This will make sure that the hidden _var_raw_data
        # cache is fully populated.
        print(f"CHECKING REPAIR {var_ref.var_id}...")
        var_obj = VarObject(var_ref.root_path, var_ref.file_path)
        replacement_mappings, replacement_used_packages = self.find_var_replacement_mappings(var_obj)

        # If the local object doesn't have problems we don't need to reprocess it
        if len(replacement_mappings) == 0:
            return True

        # Repairs are needed, let's analyze how bad it is and get to work...
        print(f"REPAIRING {var_ref.var_id}...")
        repairable = True
        removing_files = False
        # Check if repairable (currently unsupported repairs)
        null_elems = set()
        for check_value, replace_value in replacement_mappings.items():
            check_ext = path.splitext(check_value)[1].lower()
            # If there is any replace_value, this error type can always be fixed
            if replace_value is None:
                # Raw replacer only support fixing these types currently
                # These types can be succesfully removed, anything not in them isn't supported
                # This covers a lot, but there are some complex issues related to null sub-scenes
                # and broken nested asset references which can't be handled safely in the current
                # methods. The atom removal logic will need to be expanded to support these types
                # of edge cases.
                if check_ext in Ext.TYPES_ELEM:
                    null_elems.add(check_value)
                elif check_ext not in Ext.TYPES_REPLACE:
                    repairable = False
                removing_files = True
                print(f"{var_obj.var_id}: WILL REMOVE {check_value}")

        if remove_confirm and removing_files:
            confirm = input("Do you want to continue repairing this var? (y/n) ")
            if confirm.lower() != "y":
                return False

        if not repairable:
            print(f"{var_obj.var_id} >> Repairs not supported for issues in this var")
            return False

        temp_file = path.join(var_obj.directory, TEMP_VAR_NAME)
        with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as zf_dest:
            with zipfile.ZipFile(var_obj.file_path, "r") as read_zf:
                for item in read_zf.infolist():
                    if item.filename == "meta.json":
                        with io.TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                            meta = json.loads(read_item.read())
                            meta["contentList"] = [
                                r for r in read_zf.namelist() if r != "meta.json" and len(path.splitext(r)[1]) > 1
                            ]
                            meta["dependencies"] = self.get_dependencies_list_as_dict(replacement_used_packages)
                            zf_dest.writestr(
                                "meta.json",
                                orjson.dumps(meta, option=orjson.OPT_INDENT_2).decode("UTF-8"),
                                zipfile.ZIP_DEFLATED,
                            )
                            continue

                    # Copy unfixable files directly
                    if item.filename not in var_obj.json_like_files:
                        zf_dest.writestr(item.filename, read_zf.read(item.filename), zipfile.ZIP_DEFLATED)
                        continue

                    # Read and attempt to repair any readable files
                    try:
                        with io.TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                            contents = VarParser.replace(read_item.readlines(), replacement_mappings)
                        json_data = json.loads("".join(contents))

                        if len(null_elems) > 0:
                            if "storables" in json_data:
                                json_data = VarParser.remove_from_atom(json_data, null_elems)
                            elif "atoms" in json_data:
                                person_atoms = [
                                    i for i, item in enumerate(json_data["atoms"]) if item["type"] == "Person"
                                ]
                                for person_atom in person_atoms:
                                    json_data["atoms"][person_atom] = VarParser.remove_from_atom(
                                        json_data["atoms"][person_atom], null_elems
                                    )

                        write_data = orjson.dumps(json_data, option=orjson.OPT_INDENT_2).decode("UTF-8")
                        zf_dest.writestr(item.filename, write_data, zipfile.ZIP_DEFLATED)
                    except JSONDecodeError as err:
                        print(f"JSONDecodeError: {err}")
                        zf_dest.writestr(item.filename, read_zf.read(item.filename), zipfile.ZIP_DEFLATED)

        os.remove(var_obj.file_path)
        os.rename(temp_file, var_obj.file_path)
        return True
