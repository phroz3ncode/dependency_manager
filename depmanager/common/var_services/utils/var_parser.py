from collections import defaultdict
from os import path
from typing import Optional

from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.shared.tools import substrings_in_str
from depmanager.common.var_services.enums import Ext


class VarParser:
    @staticmethod
    def scan(contents: list[str]) -> set[str]:
        """Scan the contents of a readable file for references"""
        packages = set()
        for line in contents:
            if ":/" in line:
                if "https://" in line.lower() or "http://" in line.lower():
                    continue
                package_str = [word for word in line.split('"') if ":/" in word][0]
                package, _ = package_str.split(":/")
                if package.lower() != "self":
                    packages.add(package)
        return packages

    @staticmethod
    def scan_with_paths(contents: list[str]) -> dict[str, set[str]]:
        packages = defaultdict(set)
        for line in contents:
            if ":/" in line:
                if "https://" in line.lower() or "http://" in line.lower():
                    continue
                package_str = [word for word in line.split('"') if ":/" in word][0]
                package_parts = package_str.split(":/")
                package = "::".join(package_parts[:-1])
                # If there are "name" or "displayName" hooks we should dump the A_ referencing
                if package[:2] == "A_" and "name" in line.lower():
                    if ":" in package:
                        package = package.split(":")[1]
                    else:
                        package = package[2:]

                package_path = package_parts[-1]
                package_path = package_path.replace(":False", "").replace(":True", "")
                packages[package].add(package_path)
            elif "Custom/" in line or "Saves/" in line:
                split_on = "Custom/" if "Custom/" in line else "Saves/"
                package_path = [word for word in line.split('"') if split_on in word][0]
                if package_path[:2] == "A_" and ":" in package_path:
                    package_path = package_path.split(":")[1]
                packages["SELF_UNREF"].add(package_path)
        return packages

    @staticmethod
    def replace_line(line: str, replacement_mappings: dict[str, Optional[str]]) -> str:
        replacement_matches = substrings_in_str(line, list(replacement_mappings.keys()))
        # If we don't have anything to replace, just return the line
        if len(replacement_matches) == 0:
            return line

        # If we have multiple matches, idk, something is really seriously wrong with the logic or var
        # if len(replacement_matches) > 1:
        #     raise ValueError("Duplicate matches detected for replacement! Something went really wrong :(")

        # Perform an in-line repair if possible
        original_value = replacement_matches[0]
        replaced_value = replacement_mappings[original_value]

        # If the replacement mapping is a "null" style replacement, check if we can replace it or return it as is
        if replaced_value is None:
            check_ext = path.splitext(original_value)[1].lower()
            if check_ext in Ext.TYPES_REPLACE:
                line = line.replace(original_value, "")
            return line

        # If the replacement is fix for some files, but there are also good references in the file, we don't want
        # to insert duplicate line adjustments for already correct lines. Check to make sure we aren't replacing an
        # already good reference by matching a bad references substring
        if replaced_value in line:
            return line
        # It is possible our replacement is also a subset of something else, we don't want to replace these instances
        if f":/{original_value}" in line:
            return line

        # Replace the bad reference with the good reference
        return line.replace(original_value, replaced_value)

    @classmethod
    def replace(cls, contents: list[str], replacement_mappings: dict[str, Optional[str]]) -> list[str]:
        rebuilt_contents = []
        for line in contents:
            if are_substrings_in_str(line, [":/", "Custom/", "Saves/"]):
                line = cls.replace_line(line, replacement_mappings)
            rebuilt_contents.append(line)
        return rebuilt_contents

    @staticmethod
    def remove_from_elems(
        vmi_elems: list[dict], elems_to_remove: set[str], id_field: str, track_internal_ids: bool = False
    ) -> tuple[list[dict], set[str]]:
        repaired_elems = []
        internal_ids = set()
        for vmi_elem in vmi_elems:
            if vmi_elem[id_field] not in elems_to_remove:
                repaired_elems.append(vmi_elem)
            elif track_internal_ids:
                internal_ids.add(vmi_elem["internalId"])
        return repaired_elems, internal_ids

    @classmethod
    def remove_from_atom(cls, atom: dict[str, list[dict]], elems_to_remove: set[str]) -> dict[str, list[dict]]:
        geometry_index = next((i for i, item in enumerate(atom["storables"]) if item["id"] == "geometry"), None)
        if geometry_index is None:
            return atom

        supported_geometry = [("morphs", "uid", False), ("clothing", "id", True), ("hair", "id", True)]

        internal_ids = set()
        for geometry in supported_geometry:
            if geometry[0] not in atom["storables"][geometry_index]:
                continue
            atom["storables"][geometry_index][geometry[0]], geometry_internal_ids = cls.remove_from_elems(
                atom["storables"][geometry_index][geometry[0]],
                elems_to_remove,
                geometry[1],
                track_internal_ids=geometry[2],
            )
            internal_ids.update(geometry_internal_ids)

        # Check if internalIds need to be removed
        internal_ids = list(internal_ids)
        if len(internal_ids) > 0:
            remove_id_indexes = sorted(
                [i for i, item in enumerate(atom["storables"]) if are_substrings_in_str(item["id"], internal_ids)],
                reverse=True,
            )
            for remove_id_idx in remove_id_indexes:
                atom["storables"].pop(remove_id_idx)

        return atom
