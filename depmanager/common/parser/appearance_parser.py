import json
import os
import random
import string
from io import TextIOWrapper

from orjson import orjson

from depmanager.common.enums.config import IMAGE_RESOURCE_DIR
from depmanager.common.enums.ext import Ext
from depmanager.common.parser.json_parser import JsonParser
from depmanager.common.parser.rigid_body import RigidBodyUtils
from depmanager.common.shared.ziptools import ZipRead
from depmanager.common.var_object.var_object import VarObject


class AppearanceParser(JsonParser):
    PATH_APPEARANCE = ["Custom", "Atom", "Person", "Appearance"]
    PATH_MORPHS = ["Custom", "Atom", "Person", "Morphs", "Female"]
    PATH_CUA_PRESETS = ["Custom", "Scripts", "Blazedust", "CUAManager", "presets"]
    PATH_CUA_SETTINGS = ["Saves", "PluginData", "Blazedust", "CUAManager"]

    def __init__(self, var_ref: VarObject):
        self.var = var_ref

    def get_default_morph(self) -> bytes:
        with open(os.path.join(IMAGE_RESOURCE_DIR, "cua_link.vmb"), "rb") as filepath:
            default_morph = filepath.read()
        return default_morph

    @property
    def valid(self):
        return self.var.is_scene_type

    def extract_to_file(self, root_dir):
        person_atoms = self.extract_person_atoms()

        for person_atom in person_atoms:
            preset_name = person_atom["preset_name"]

            # Write the preset
            preset_json = orjson.dumps(person_atom["preset"], option=orjson.OPT_INDENT_2).decode("UTF-8")
            image_data = person_atom["preset_image"]

            os.makedirs(os.path.join(root_dir, *self.PATH_APPEARANCE), exist_ok=True)
            with open(
                os.path.join(root_dir, *self.PATH_APPEARANCE, f"Preset_{preset_name}{Ext.VAP}"), "w", encoding="UTF-8"
            ) as write_file:
                write_file.write(preset_json)
            if image_data:
                image_data.save(
                    os.path.join(root_dir, *self.PATH_APPEARANCE, f"Preset_{preset_name}{Ext.JPG}"), format="JPEG"
                )

            # If linked cua data write the linked CUA
            if person_atom["linked_cuas"]:
                cua_preset = orjson.dumps(person_atom["linked_cuas"]["cua_preset"], option=orjson.OPT_INDENT_2).decode(
                    "UTF-8"
                )
                cua_link_vmi = orjson.dumps(
                    person_atom["linked_cuas"]["cua_link_vmi"], option=orjson.OPT_INDENT_2
                ).decode("UTF-8")
                cua_morph_name = person_atom["linked_cuas"]["cua_morph_name"]
                cua_link_auto_morph = person_atom["linked_cuas"]["cua_link_auto_morph"]

                os.makedirs(os.path.join(root_dir, *self.PATH_CUA_PRESETS), exist_ok=True)
                with open(
                    os.path.join(root_dir, *self.PATH_CUA_PRESETS, f"Preset_{preset_name}{Ext.JSON}"),
                    "w",
                    encoding="UTF-8",
                ) as write_file:
                    write_file.write(cua_preset)
                if image_data:
                    image_data.save(
                        os.path.join(root_dir, *self.PATH_CUA_PRESETS, f"Preset_{preset_name}{Ext.JPG}"), format="JPEG"
                    )

                os.makedirs(os.path.join(root_dir, *self.PATH_MORPHS), exist_ok=True)
                with open(
                    os.path.join(root_dir, *self.PATH_MORPHS, f"{cua_morph_name}{Ext.VMI}"), "w", encoding="UTF-8"
                ) as write_file:
                    write_file.write(cua_link_vmi)
                with open(os.path.join(root_dir, *self.PATH_MORPHS, f"{cua_morph_name}{Ext.VMB}"), "wb") as write_file:
                    write_file.write(self.get_default_morph())

                os.makedirs(os.path.join(root_dir, *self.PATH_CUA_SETTINGS), exist_ok=True)
                options_path = os.path.join(root_dir, *self.PATH_CUA_SETTINGS, "options.json")
                if os.path.exists(options_path):
                    with open(options_path, "r", encoding="UTF-8") as read_file:
                        options = json.load(read_file)
                else:
                    options = {
                        "id": "Options",
                        "autoSelectPerson": "true",
                        "autoSelectAssetController": "true",
                        "delayPhysicsProperties": "true",
                        "enableScalingModifier": "true",
                        "enableLoadTriggers": "true",
                        "ignoreAllSceneAssets": "true",
                        "ignoreSceneAsssetsContainingScripts": "true",
                        "ignoreSceneAssetsMarkedHidden": "true",
                        "smartRemovalOfPresets": "true",
                        "enablePersonUidLoadTriggers": "true",
                        "updateScriptAtomUids": "true",
                        "enablePrioritizedLoadingTriggers": "false",
                        "enableCUAReuseOnLoad": "true",
                        "ignoreDisabledLinkedAtoms": "true",
                        "includedAtomTypes": "CustomUnityAsset",
                    }
                if "autoMorphLoaders" not in options:
                    options["autoMorphLoaders"] = []
                if cua_link_auto_morph not in options["autoMorphLoaders"]:
                    options["autoMorphLoaders"].append(cua_link_auto_morph)
                    options_json = orjson.dumps(options, option=orjson.OPT_INDENT_2).decode("UTF-8")
                    with open(options_path, "w", encoding="UTF-8") as write_file:
                        write_file.write(options_json)

    def extract_person_atoms(self):
        person_atoms = []

        if not self.valid:
            return person_atoms

        with ZipRead(self.var.file_path) as read_zf:
            for filename in self.var.json_files:
                with TextIOWrapper(read_zf.open(filename, "r"), encoding="UTF-8") as read_item:
                    # Replace all SELF: references
                    raw_data = read_item.read()
                    raw_data = raw_data.replace("SELF:", f"{self.var.var_id}:")
                    json_data = json.loads(raw_data)

                    if "storables" in json_data and self.contains_geometry_storable(json_data["storables"]):
                        atoms = [json_data]
                    elif "atoms" in json_data:
                        json_data = json_data["atoms"]
                        atoms = self.get_person_atoms(json_data)
                    else:
                        continue

                    if len(atoms) > 0:
                        for atom in atoms:
                            random_id = self.get_random_id(filename, atom["id"])
                            preset_name = f"{self.var.duplicate_id}_{atom['id']}_{random_id}".replace(" ", "_")
                            # Get linked cuas
                            atom, linked_cuas = self.get_linked_cua_preset(json_data, atom, preset_name)
                            # Remove all rigid bodies
                            preset = {
                                "setUnlistedParamsToDefault": "true",
                                "storables": self.get_non_rigid_storables(atom),
                            }
                            # Get the thumbnail if available
                            preset_image = self.get_preset_image(filename)

                            person_atoms.append(
                                {
                                    "preset_name": preset_name,
                                    "preset": preset,
                                    "preset_image": preset_image,
                                    "linked_cuas": linked_cuas,
                                }
                            )

        return person_atoms

    def get_preset_image(self, filename):
        preset_image = None
        image_files = [f for f in self.var.namelist if os.path.splitext(filename)[0] in f]
        image_files = [f for f in image_files if os.path.splitext(f)[1].lower() in (Ext.JPG, Ext.PNG, Ext.TIF)]
        if len(image_files) > 0:
            preset_image = self.var.get_image(image_files[0])
        return preset_image

    def get_linked_cua_preset(self, json_data, atom, preset_name):
        rb_utils = RigidBodyUtils(atom)
        linked_cuas = self.get_linked_cua_atoms(json_data, filter_id=atom["id"])
        linked_cuas = [rb_utils.update_cuab_link(linked_cua) for linked_cua in linked_cuas]
        if len(linked_cuas) == 0:
            return atom, None

        cua_morph_name = f"{preset_name}_morph"
        cua_preset = self.get_cua_preset(linked_cuas, preset_name)
        cua_link_auto_morph = self.get_cua_link_auto_morph(cua_morph_name, preset_name)
        cua_morph = self.get_cua_link_morph(cua_morph_name)
        cua_link_vmi = self.get_cua_link_vmi(cua_morph_name)

        # Add the morph to the atom
        geometry_index = next(idx for idx, item in enumerate(atom["storables"]) if item.get("id") == "geometry")
        atom["storables"][geometry_index]["morphs"].append(cua_morph)

        linked_cua_presets = {
            "cua_preset": cua_preset,
            "cua_link_auto_morph": cua_link_auto_morph,
            "cua_morph_name": cua_morph_name,
            "cua_link_vmi": cua_link_vmi,
        }

        return atom, linked_cua_presets

    def get_random_id(self, filename, atom_id):
        random.seed(filename + atom_id)
        return "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(5))

    def get_cua_preset(self, linked_cua_atoms, cua_preset_name):
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
            "id": cua_preset_name,
            "type": "linkedAsset",
            "items": items,
        }
        return preset

    def get_cua_link_auto_morph(self, cua_morph_name, cua_preset_name):
        return {"id": cua_morph_name, "personUid": "", "preset": cua_preset_name}

    def get_cua_link_morph(self, cua_morph_name):
        return {
            "name": cua_morph_name,
            "uid": f"Custom/Atom/Person/Morphs/female/{cua_morph_name}.vmi",
            "value": "0.000001",
        }

    def get_cua_link_vmi(self, cua_morph_name):
        return {
            "id": cua_morph_name,
            "displayName": cua_morph_name,
            "group": "Empty",
            "region": "Empty",
            "min": "0",
            "max": "1",
            "numDeltas": "0",
            "isPoseControl": "false",
            "formulas": [{"targetType": "RotationX", "target": "rSmallToe4", "multiplier": "0.0"}],
        }
