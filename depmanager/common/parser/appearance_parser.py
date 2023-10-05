import json
from io import TextIOWrapper
from os import path

from depmanager.common.enums.ext import Ext
from depmanager.common.parser.enums import UNUSED_NODES
from depmanager.common.parser.json_parser import JsonParser
from depmanager.common.shared.ziptools import ZipRead
from depmanager.common.var_object.var_object import VarObject


class AppearanceParser(JsonParser):
    def __init__(self, var_ref: VarObject):
        self.var = var_ref

    @property
    def valid(self):
        return self.var.is_scene_type

    def extract(self):
        if not self.valid:
            return None

        person_atoms = []
        linked_cua_atoms = []

        with ZipRead(self.var.file_path) as read_zf:
            for item in self.var.json_like_files:
                atoms, linked_atoms = [], []
                item_name = path.split(item)[-1]
                with TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                    json_data = json.loads(read_item.read())

                    if "storables" in json_data and self.contains_geometry_storable(json_data["storables"]):
                        atoms = [self._clean_person_atom(json_data)]

                    elif "atoms" in json_data:
                        json_data = json_data["atoms"]
                        atoms = [self._clean_person_atom(atom) for atom in self.get_person_atoms(json_data)]
                        linked_atoms = [atom for atom in self.get_linked_cua_atoms(json_data)]

                    if len(atoms) > 0:
                        for atom_id, atom_contents in atoms:
                            person_atoms.append((item_name, atom_id, atom_contents))
                        if len(linked_atoms) > 0:
                            linked_cua_atoms.append((item_name, linked_atoms))

        if len(person_atoms) == 0:
            return None

        return person_atoms, linked_cua_atoms

    @staticmethod
    def _clean_person_atom(atom):
        """ Remove garbage from the person atom """
        storables = []
        for storable in atom["storables"]:
            if storable["id"] not in UNUSED_NODES and len(storable) > 1:
                storables.append(storable)

        return atom.get("id"), storables

        # return {
        #     "setUnlistedParamsToDefault": "true",
        #     "storables": storables
        # }
