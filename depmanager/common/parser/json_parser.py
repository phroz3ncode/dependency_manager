from orjson import orjson

from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.shared.tools import is_str_in_substrings


class JsonParser:
    @staticmethod
    def contains_geometry_storable(storables):
        if storables is None:
            return False
        return len([e for e in storables if e["id"] == "geometry"]) > 0

    @classmethod
    def get_person_atoms(cls, atom_elems):
        person_atoms = []
        for atom_elem in atom_elems:
            if cls.contains_geometry_storable(atom_elem["storables"]):
                person_atoms.append(atom_elem)
        return person_atoms

    @classmethod
    def replace_self_references_with_id(cls, atom, self_id):
        """Replace self references with self_id"""
        storables = []
        for storable in atom["storables"]:
            if len(storable) > 1:
                storable = orjson.loads(orjson.dumps(storable).decode("utf-8").replace("SELF:", f"{self_id}:"))
                storables.append(storable)
        atom["storables"] = storables
        return atom

    @classmethod
    def get_non_rigid_storables(cls, atom):
        """Remove"""
        non_rigid_storables = []
        for storable in atom["storables"]:
            # Always remove triggers
            has_triggers = is_str_in_substrings("trigger", storable.keys())
            has_rigid = is_str_in_substrings("pos", storable.keys())
            if has_rigid or has_triggers:
                continue

            non_rigid_storables.append(storable)
        return non_rigid_storables

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
