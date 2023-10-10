from depmanager.common.shared.tools import are_substrings_in_str


class JsonParser:
    @staticmethod
    def contains_geometry_storable(storables):
        if storables is None:
            return False
        return len([e for e in storables if e["id"] == "geometry"]) > 0

    @staticmethod
    def contains_cua_linkto_storable(storables):
        if storables is None:
            return None
        return len([e for e in storables if e["id"] == "control" and "linkTo" in e.keys()]) > 0

    @classmethod
    def get_person_atoms(cls, atom_elems):
        return list(filter(lambda v: cls.contains_geometry_storable(v["storables"]), atom_elems))

    @classmethod
    def get_linked_cua_atoms(cls, atom_elems):
        return list(
            filter(
                lambda v: v["type"] == "CustomUnityAsset" and cls.contains_cua_linkto_storable(v["storables"]),
                atom_elems,
            )
        )

    # @classmethod
    # def get_linked_cua_atoms(cls, atom_elems):
    #     for v in atom_elems:
    #         cls.get_linkto_storables(v.get("storables"))
    #     return list(filter(lambda v: v['type'] == 'CustomUnityAsset' and "geometry" in cls.get_storables_ids(v["storables"], atom_elems))

    # @staticmethod
    # def get_cua_atoms(atom_elems):
    #     return list(filter(lambda v: v['type'] == 'CustomUnityAsset' and 'storables' in v.keys(), atom_elems))
    #
    # @classmethod
    # def get_person_cua_atoms(cls, atom_elems):
    #     cua_atoms = cls.get_cua_atoms(atom_elems)
    #
    #     person_cua_atoms = []
    #     for atom in cua_atoms:
    #         control_elem = next((storable for storable in atom['storables'] if storable["id"] == "control"), {})
    #         if "linkTo" in control_elem:
    #             person_cua_atoms.append(atom)
    #     return person_cua_atoms

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
