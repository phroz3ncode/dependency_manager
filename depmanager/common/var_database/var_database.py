import io
import json
import os
from collections import defaultdict
from json import JSONDecodeError
from os import path

from orjson import orjson

from depmanager.common.enums.content_type import ContentType
from depmanager.common.enums.ext import Ext
from depmanager.common.enums.paths import TEMP_SYNC_DIR
from depmanager.common.enums.variables import BACKWARDS_COMPAT_PLUGIN_AUTHORS
from depmanager.common.enums.variables import MEGABYTE
from depmanager.common.enums.variables import TEMP_VAR_NAME
from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.json_parser import VarParser
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import find_fuzzy_file_match
from depmanager.common.shared.tools import select_fuzzy_match
from depmanager.common.shared.ziptools import ZipReadInto
from depmanager.common.var_database.var_database_image_db import VarDatabaseImageDB
from depmanager.common.var_object.var_object import VarObject


class VarDatabase(VarDatabaseImageDB):
    @property
    def _attributes(self):
        return [
            "vars_required",
            "required_dependencies",
            "repair_index",
        ] + super()._attributes

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
    def required_dependencies(self) -> defaultdict[str, set]:
        """Logic to retrieve all required dependencies"""
        required = defaultdict(set)
        # progress = ProgressBar(len(self.vars), description="Building dependency map")
        # Using .items negates the cached_property benefits
        # pylint: disable=consider-using-dict-items
        for var_id in self.vars:
            # progress.inc()

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

    @property
    def unique_required_dependencies(self) -> set[str]:
        unique_dependencies = set()
        for var_id, var_required_dependencies in self.required_dependencies.items():
            unique_dependencies.add(var_id)
            for dependency in var_required_dependencies:
                unique_dependencies.add(dependency)
        return unique_dependencies

    @property
    def reference_file_uses(self) -> list[tuple[str, int]]:
        refs = defaultdict(int)
        for var_id in self.keys:
            for package, package_path in self[var_id].used_packages_as_list:
                if package in ("SELF", "SELF_UNREF"):
                    continue
                refs[f"{package}:::{package_path}"] += 1
        return list(sorted(refs.items(), key=lambda item: item[1], reverse=True))

    @property
    def reference_author_uses(self) -> list[tuple[str, int]]:
        refs = defaultdict(int)
        for package, uses in self.reference_file_uses:
            refs[package.split(".")[0]] += uses
        return list(sorted(refs.items(), key=lambda item: item[1], reverse=True))

    @property
    def unique_referenced_dependencies(self) -> set[str]:
        unique_referenced = set()
        for _, var_required_dependencies in self.required_dependencies.items():
            for dependency in var_required_dependencies:
                var_name = dependency if ".latest" not in dependency else self.get_var_name(dependency)
                if var_name is not None:
                    unique_referenced.add(var_name)
        return unique_referenced

    @cached_property
    # pylint: disable=consider-using-dict-items
    def repair_index(self) -> list[tuple[str, str, str]]:
        """Builds a repair index

        We sort by the following:
            - ContentType.REFERENCE_PRIORITY (this is how likely the item is to be a base reference, not part of a scene)
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

    def duplication_index(self):
        return [item for item in self.repair_index if self.vars[item[0]].var_type.is_asset]

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

    def get_var_ids_from_sync_folder(self) -> set[str]:
        deps = set()
        local_sync_path = os.path.join(self.rootpath, TEMP_SYNC_DIR)
        if not os.path.exists(local_sync_path):
            return deps

        for (_, _, files) in os.walk(os.path.join(self.rootpath, TEMP_SYNC_DIR)):
            for file in files:
                deps.add(file.replace(Ext.JPG, Ext.EMPTY))
        return deps

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

    def find_unversioned_duplicates(self) -> set[str]:
        unversioned_duplicates = set()
        # progress = ProgressBar(len(self.vars_versions.keys()), "Searching for unversioned duplicates")
        for var_name, versions in self.vars_versions.items():
            # progress.inc()
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
        # progress = ProgressBar(len(self.keys), "Searching for missing vars")
        for var_id in self.unique_required_dependencies:
            # progress.inc()
            if self.get_var_name(var_id) is None:
                missing_vars.add(var_id)
        return missing_vars

    def find_unused_vars(self, filters=None, invert=False) -> set[str]:
        # Get the unused vars
        favorites = set(key for key, var in self.vars.items() if var.is_favorite)
        var_list = self.keys - set(self.unique_referenced_dependencies)
        var_list = var_list - favorites
        if invert:
            var_list = self.keys - var_list
        if filters is not None:
            if not isinstance(filters, list):
                raise ValueError("Filter must be a list")
            filters = [f.strip() for f in filters]
            var_list = {v for v in var_list if any(f for f in filters if f in self[v].sub_directory)}
        return set(var_list)

    def find_unoptimized_vars(self):
        var_list = set()
        # progress = ProgressBar(len(self.keys), description="Searching unoptimized vars")
        for var_id, var in self.vars.items():
            # progress.inc()
            # This is a big change not made lightly. Ultimately if a single var tracks every change to all
            # downstream vars, when you have a ".latest" var that gets updated and adds or upgrades a new
            # dependency this can result in a MASSIVE need for downstream updates to fix all the metadata.
            # The native handling of this by storing everything in meta.json just doesn't work well.
            # As a result we should only store the actual "used_dependencies". During local synchronization,
            # we can ensure that everything is brought down properly.
            if var.dependencies_sorted != var.used_dependencies_sorted:
                var_list.add(var_id)
        return var_list

    def find_duplication_in_vars(self):
        var_list = set()
        progress = ProgressBar(len(self.keys), description="Searching duplication in vars")
        duplication_index = self.duplication_index()
        for var_id, var in self.vars.items():
            progress.inc()
            # Do not attempt to de-duplicate core assets, these should be ground truth sources
            if var.var_type.is_asset:
                continue
            self_packages = var.used_packages.get("SELF")
            if self_packages is None:
                continue
            for self_package in self_packages:
                result = next((index for index in duplication_index if index[1].lower() == self_package), None)
                if result is not None:
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
        with ZipReadInto(var_obj.file_path, temp_file) as (read_zf, zf_dest):
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
                        zf_dest.writestr(item.filename, meta_data)
                else:
                    zf_dest.writestr(item.filename, read_zf.read(item.filename))

        if failed:
            os.remove(temp_file)
        else:
            os.remove(var_obj.file_path)
            os.rename(temp_file, var_obj.file_path)

    def find_broken_vars(self, health_check=False):
        var_list = set()
        progress = ProgressBar(len(self.keys), description="Searching broken vars")
        track = {}
        for var_id in self.keys:
            progress.inc()
            replacement_mappings, _ = self.find_var_replacement_mappings(self[var_id], health_check=health_check)
            if len(replacement_mappings) > 0:
                var_list.add(var_id)
                track.update(replacement_mappings)
        return var_list

    def find_oversize_vars(self):
        var_list = set()
        progress = ProgressBar(len(self.keys), description="Searching oversize vars")
        for var_id in self.keys:
            progress.inc()
            images_list = [
                filename
                for filename, size in self[var_id].infolist
                if (
                    (os.path.splitext(filename)[1] == Ext.TIF and size > (8 * MEGABYTE))
                    or (os.path.splitext(filename)[1] == Ext.PNG and size > (8 * MEGABYTE))
                    or (os.path.splitext(filename)[1] == Ext.JPG and size > (12 * MEGABYTE))
                )
            ]
            if len(images_list) > 0:
                var_list.add(var_id)
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

        if (
            var_package.var_type.type == ContentType.PLUGIN
            and var_package.author not in BACKWARDS_COMPAT_PLUGIN_AUTHORS
        ):
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

        if (
            var_package.var_type.type == ContentType.PLUGIN
            and var_package.author not in BACKWARDS_COMPAT_PLUGIN_AUTHORS
        ):
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

    def find_var_replacement_mappings(self, var_obj: VarObject, health_check=False):
        mappings = self.find_broken_replacement_mappings(var_obj, health_check=health_check)

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

        replacement_mappings = {}
        for key, package, version, package_file in mappings:
            if key is None:
                continue
            if package is not None:
                if version is not None:
                    replacement_mappings[key] = f"{package}.{version}:/{package_file}"
                else:
                    replacement_mappings[key] = f"{package}:/{package_file}"
            else:
                replacement_mappings[key] = None
        replacement_mappings = {key: val for key, val in replacement_mappings.items() if key != val}
        used_packages = set(
            f"{package}.{version}" for (_, package, version, _) in mappings if package != "SELF" and package is not None
        )
        return replacement_mappings, used_packages

    def optimize_multiple_versions(self, mappings, mapping_versions):
        def replace_mapping(mappings, package, version):
            new_mappings = set()
            for mapping in mappings:
                if mapping[1] != package:
                    new_mappings.add(mapping)
                    continue
                replace_key = f"{mapping[1]}.{mapping[2]}:/{mapping[3]}" if mapping[0] is None else mapping[0]
                new_mappings.add((replace_key, mapping[1], version, mapping[3]))
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

    def find_broken_replacement_mappings(self, var_obj: VarObject, health_check=False):
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

            # The reference is invalid, if health check, quickly exit
            if health_check:
                mappings.add((replace_key, None, None, None))
                continue

            # Search to replace invalid reference
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

    def repair_broken_var(self, var_ref: VarObject, remove_confirm=False, remove_skip=False) -> bool:
        # var_ref is from the local_db typically and is a quick load
        # This means it will not contain a detailed mapping of the var contents
        # We want to create a new object to make sure repairs are accurate by rescanning the local
        # object fully with the VarParser. This will make sure that the hidden _var_raw_data
        # cache is fully populated.
        print(f"CHECKING REPAIR {var_ref.var_id}...")
        var_obj = VarObject(var_ref.root_path, var_ref.file_path)
        replacement_mappings, replacement_used_packages = self.find_var_replacement_mappings(var_obj)
        json_errors_during_repair = False

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

        if removing_files:
            if remove_skip:
                print("Skipping file as removals required...")
                return False
            if remove_confirm:
                confirm = input("Do you want to continue repairing this var? (y/n) ")
                if confirm.lower() != "y":
                    return False

        if not repairable:
            print(f"{var_obj.var_id} >> Repairs not supported for issues in this var")
            return False

        temp_file = path.join(var_obj.directory, TEMP_VAR_NAME)
        with ZipReadInto(var_obj.file_path, temp_file) as (read_zf, zf_dest):
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
                        )
                        continue

                # Copy unfixable files directly
                if item.filename not in var_obj.json_like_files:
                    zf_dest.writestr(item.filename, read_zf.read(item.filename))
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
                            person_atoms = [i for i, item in enumerate(json_data["atoms"]) if item["type"] == "Person"]
                            for person_atom in person_atoms:
                                json_data["atoms"][person_atom] = VarParser.remove_from_atom(
                                    json_data["atoms"][person_atom], null_elems
                                )

                    write_data = orjson.dumps(json_data, option=orjson.OPT_INDENT_2).decode("UTF-8")
                    zf_dest.writestr(item.filename, write_data)
                except JSONDecodeError as err:
                    print(f"JSONDecodeError: {item.filename} >> {err}")
                    zf_dest.writestr(item.filename, read_zf.read(item.filename))
                    json_errors_during_repair = True

        if json_errors_during_repair:
            os.remove(temp_file)
            return False

        os.remove(var_obj.file_path)
        os.rename(temp_file, var_obj.file_path)
        return True
