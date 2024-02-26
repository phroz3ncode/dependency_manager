import json
import os
from io import TextIOWrapper

from orjson import orjson

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
            return [], []

        person_atoms = []
        linked_cua_atoms = []

        with ZipRead(self.var.file_path) as read_zf:
            for item in self.var.json_files:
                atoms, linked_atoms = [], []
                with TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                    json_data = json.loads(read_item.read())

                    if "storables" in json_data and self.contains_geometry_storable(json_data["storables"]):
                        atoms = [self._clean_person_atom(json_data, self_id=self.var.var_id)]

                    elif "atoms" in json_data:
                        json_data = json_data["atoms"]
                        atoms = [
                            self._clean_person_atom(atom, self_id=self.var.var_id)
                            for atom in self.get_person_atoms(json_data)
                        ]
                        linked_atoms = list(self.get_linked_cua_atoms(json_data))

                    if len(atoms) > 0:
                        for atom_id, atom_contents in atoms:
                            person_atoms.append((item, atom_id, atom_contents))
                        if len(linked_atoms) > 0:
                            linked_cua_atoms.append((item, linked_atoms))

        if len(person_atoms) == 0:
            return [], []

        return person_atoms, linked_cua_atoms

    def extract_to_file(self, save_dir, save_linked_dir):
        person_atoms, linked_cua_atoms = self.extract()
        if len(person_atoms) == 0:
            return

        for person_atom in person_atoms:
            scene_name, atom_name, storables = person_atom

            basename = os.path.basename(scene_name)
            basename = os.path.splitext(basename)[0]
            preset_name = f"Preset_{self.var.duplicate_id}_{basename}_{atom_name}"

            self.extract_vap_to_file(save_dir, preset_name, storables)
            self.extract_vap_linked_to_file(save_linked_dir, preset_name, linked_cua_atoms, scene_name)
            self.extract_vap_image_to_file(save_dir, preset_name, scene_name)

    def extract_vap_to_file(self, save_dir, preset_name, storables):
        preset = {"setUnlistedParamsToDefault": "true", "storables": storables}

        preset_json = orjson.dumps(preset, option=orjson.OPT_INDENT_2).decode("UTF-8")

        write_file_path = os.path.join(save_dir, f"{preset_name}{Ext.VAP}")
        with open(write_file_path, "w", encoding="UTF-8") as write_file:
            write_file.write(preset_json)

    def extract_vap_linked_to_file(self, save_dir, preset_name, linked_cua_atoms, scene_name):
        if len(linked_cua_atoms) == 0:
            return
        linked_cua_atom = [link for link in linked_cua_atoms if scene_name in link[0]]
        if len(linked_cua_atom) == 0:
            return

        preset = {
            "id": preset_name,
            "type": "linkedAsset",
            "items": [{"cua": cua["id"], "atoms": [cua]} for cua in linked_cua_atom[0][1]],
        }
        preset = orjson.loads(orjson.dumps(preset).decode("utf-8").replace("SELF:", f"{self.var.var_id}:"))
        preset_json = orjson.dumps(preset, option=orjson.OPT_INDENT_2).decode("UTF-8")

        write_file_path = os.path.join(save_dir, f"{preset_name}{Ext.JSON}")
        with open(write_file_path, "w", encoding="UTF-8") as write_file:
            write_file.write(preset_json)

    def extract_vap_image_to_file(self, save_dir, preset_name, scene_name):
        # Try to export a thumbnail for the look
        image_files = [f for f in self.var.namelist if os.path.splitext(scene_name)[0] in f]
        image_files = [f for f in image_files if os.path.splitext(f)[1].lower() in (Ext.JPG, Ext.PNG, Ext.TIF)]
        if len(image_files) > 0:
            image_data = self.var.get_image(image_files[0])
            write_image_path = os.path.join(save_dir, f"{preset_name}{Ext.JPG}")
            image_data.save(write_image_path, format="JPEG")

    @staticmethod
    def _clean_person_atom(atom, self_id):
        """Remove garbage from the person atom"""
        storables = []
        for storable in atom["storables"]:
            if storable["id"] not in UNUSED_NODES and len(storable) > 1:
                storable = orjson.loads(orjson.dumps(storable).decode("utf-8").replace("SELF:", f"{self_id}:"))
                storables.append(storable)

        return atom.get("id"), storables
