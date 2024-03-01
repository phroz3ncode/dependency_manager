import json
import os
from io import TextIOWrapper

from orjson import orjson

from depmanager.common.enums.ext import Ext
from depmanager.common.parser.json_parser import JsonParser
from depmanager.common.parser.rigid_body import RigidBodyUtils
from depmanager.common.shared.ziptools import ZipRead
from depmanager.common.var_object.var_object import VarObject


class AppearanceParser(JsonParser):
    def __init__(self, var_ref: VarObject):
        self.var = var_ref

    @property
    def valid(self):
        return self.var.is_scene_type

    def extract(self):
        person_atoms = []

        if not self.valid:
            return person_atoms

        with ZipRead(self.var.file_path) as read_zf:
            for item in self.var.json_files:
                with TextIOWrapper(read_zf.open(item, "r"), encoding="UTF-8") as read_item:
                    json_data = json.loads(read_item.read())

                    person_atom_references = self.get_person_atom_references(item, json_data)
                    person_atoms.extend(person_atom_references)

        return person_atoms

    def get_person_atom_references(self, filename, json_data):
        if "storables" in json_data and self.contains_geometry_storable(json_data["storables"]):
            atoms = [json_data]
        elif "atoms" in json_data:
            json_data = json_data["atoms"]
            atoms = self.get_person_atoms(json_data)
        else:
            return []

        # If there are any atoms extract linked cua and rigid bodies
        person_atoms = []
        if len(atoms) > 0:
            for atom in atoms:
                atom_id = atom["id"]
                atom = self.replace_self_references_with_id(atom, self.var.var_id)

                # Update the linked cuas
                rb_utils = RigidBodyUtils(atom)
                linked_cuas = self.get_linked_cua_atoms(json_data, filter_id=atom_id)
                linked_cuas = [rb_utils.update_cuab_link(linked_cua) for linked_cua in linked_cuas]

                # Remove all rigid bodies from the appearance
                atom["storables"] = self.get_non_rigid_storables(atom)

                person_atoms.append({"id": atom_id, "file": filename, "atom": atom, "linked_cuas": linked_cuas})
        return person_atoms

    def extract_to_file(self, save_dir, save_linked_dir):
        person_atoms = self.extract()

        for person_atom in person_atoms:
            scene_name = person_atom["file"]
            atom_name = person_atom["id"]
            storables = person_atom["atom"]["storables"]
            linked_cua_atoms = person_atom["linked_cuas"]

            basename = os.path.basename(scene_name)
            basename = os.path.splitext(basename)[0]
            preset_name = f"Preset_{self.var.duplicate_id}_{basename}_{atom_name}"

            self.extract_vap_to_file(save_dir, preset_name, storables)
            self.extract_vap_linked_to_file(save_linked_dir, preset_name, linked_cua_atoms)
            self.extract_vap_image_to_file(save_dir, preset_name, scene_name)

    def extract_vap_to_file(self, save_dir, preset_name, storables):
        preset = {"setUnlistedParamsToDefault": "true", "storables": storables}

        preset_json = orjson.dumps(preset, option=orjson.OPT_INDENT_2).decode("UTF-8")

        write_file_path = os.path.join(save_dir, f"{preset_name}{Ext.VAP}")
        with open(write_file_path, "w", encoding="UTF-8") as write_file:
            write_file.write(preset_json)

    def extract_vap_linked_to_file(self, save_dir, preset_name, linked_cua_atoms):
        if len(linked_cua_atoms) == 0:
            return

        items = []
        for linked_cua in linked_cua_atoms:
            cua_id = linked_cua.pop("id")
            linked_cua.pop("on", None)
            linked_cua.pop("position", None)
            linked_cua.pop("rotation", None)
            linked_cua.pop("containerPosition", None)
            linked_cua.pop("containerRotation", None)
            linked_cua["setUnlistedParamsToDefault"] = "true"
            items.append({"cua": cua_id, "atoms": [linked_cua]})

        preset = {
            "id": preset_name,
            "type": "linkedAsset",
            "items": items,
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

    # @staticmethod
    # def _clean_person_atom(atom, self_id):
    #     """Remove garbage from the person atom"""
    #     storables = []
    #     for storable in atom["storables"]:
    #         if storable["id"] not in UNUSED_NODES and len(storable) > 1:
    #             storable = orjson.loads(orjson.dumps(storable).decode("utf-8").replace("SELF:", f"{self_id}:"))
    #             storables.append(storable)
    #
    #     return atom.get("id"), storables
    #
    # @staticmethod
    # def _get_rigid_bodies(atom):
    #     """Remove garbage from the person atom"""
    #     rigid_bodies = {}
    #     for storable in atom["storables"]:
    #         if is_str_in_substrings("pos", storable.keys()):
    #             rigid_bodies[storable["id"]] = storable
    #
    #     return atom.get("id"), rigid_bodies
