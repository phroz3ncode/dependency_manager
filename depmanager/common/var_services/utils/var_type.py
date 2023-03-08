from os import path
from typing import Optional

from depmanager.common.shared.tools import is_str_in_substrings


class VarType:
    ASSET = "asset"
    APPEARANCE = "appearance"
    CLOTHING = "clothing"
    HAIR = "hair"
    MORPH = "morph"
    PLUGIN = "plugin"
    POSE = "pose"
    PRESET = "preset"
    SCENE = "scene"
    SOUND = "sound"
    TEXTURE = "texture"
    UNITY = "unity"

    REFERENCE_ORDER = [
        TEXTURE,
        MORPH,
        SOUND,
        PLUGIN,
        HAIR,
        CLOTHING,
        ASSET,
        UNITY,
        POSE,
        APPEARANCE,
        PRESET,
        SCENE,
    ]

    DIR_SCENE = "scenes"
    DIR_LOOK = "looks"
    DIR_ASSET = "assets"
    DIR_CUSTOM = path.join(DIR_SCENE, "custom")
    DIR_VAMX = path.join(DIR_SCENE, "vamx")

    def __init__(self, contains_ref: Optional[dict[str, bool]]):
        self.contains_ref = contains_ref

    @property
    def type_priority(self) -> list[str]:
        return self.types_scene + self.types_preset + self.types_asset + self.types_unity

    @property
    def types_scene(self) -> list[str]:
        return [self.SCENE]

    @property
    def types_preset(self) -> list[str]:
        return [self.APPEARANCE, self.PRESET]

    @property
    def types_asset(self) -> list[str]:
        return [self.PLUGIN, self.POSE, self.CLOTHING, self.HAIR, self.MORPH, self.TEXTURE, self.SOUND]

    @property
    def types_unity(self) -> list[str]:
        return [self.ASSET]

    @property
    def types_with_json(self):
        return [self.SCENE, self.APPEARANCE, self.PRESET]

    @property
    def types_with_image(self):
        return [
            self.SCENE,
            self.APPEARANCE,
            self.PRESET,
            self.CLOTHING,
            self.HAIR,
            self.PLUGIN,
        ]

    @property
    def types_with_default_image(self):
        return [
            self.ASSET,
            self.MORPH,
            self.PLUGIN,
            self.SOUND,
            self.UNITY,
        ]

    @property
    def reference_priority(self):
        return self.REFERENCE_ORDER.index(self.type)

    @classmethod
    def ref_from_namelist(cls, namelist: list[str]) -> dict[str, bool]:
        return {
            cls.ASSET: is_str_in_substrings("custom/assets/", namelist),
            cls.CLOTHING: is_str_in_substrings("custom/clothing/", namelist),
            cls.HAIR: is_str_in_substrings("custom/hair/", namelist),
            cls.MORPH: is_str_in_substrings("custom/atom/person/morphs/", namelist),
            cls.TEXTURE: is_str_in_substrings("custom/atom/person/textures/", namelist),
            cls.PRESET: is_str_in_substrings("custom/atom/person/appearance/", namelist),
            cls.PLUGIN: is_str_in_substrings("custom/scripts/", namelist),
            cls.SCENE: is_str_in_substrings("saves/scene/", namelist),
            cls.APPEARANCE: is_str_in_substrings("saves/person/appearance/", namelist),
            cls.SOUND: is_str_in_substrings("custom/sounds/", namelist),
            cls.POSE: is_str_in_substrings("saves/person/pose/", namelist)
            or is_str_in_substrings("custom/atom/person/pose/", namelist),
        }

    @property
    def type(self) -> str:
        for priority in self.type_priority:
            if self.contains_ref[priority]:
                return priority
        return self.ASSET

    @property
    def type_subdirectory(self):
        if self.type in self.types_scene:
            return self.DIR_SCENE
        if self.type in self.types_preset:
            return self.DIR_SCENE
        if self.type in self.types_asset:
            return path.join(self.DIR_ASSET, self.type)
        if self.type in self.types_unity:
            return path.join(self.DIR_ASSET, self.UNITY)
        return self.type

    def contains_type(self, check_type: str) -> bool:
        if check_type not in self.type_priority:
            raise ValueError("Unspecified type")
        return self.contains_ref.get(check_type, False)

    @property
    def is_repairable(self):
        return self.type in self.types_with_json

    @property
    def is_symlink_type(self):
        if self.contains_type(self.ASSET):
            return False
        if self.contains_type(self.PLUGIN):
            return False
        return True
