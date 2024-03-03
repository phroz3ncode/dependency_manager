from __future__ import annotations

from typing import Dict

import numpy as np

from depmanager.common.shared.tools import is_str_in_substrings

PI = 3.1415927


# pylint: disable=invalid-name
class Vector3:
    def __init__(self, x: float, y: float, z: float):
        self.x = x
        self.y = y
        self.z = z

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> Vector3:
        x = float(data.get("x", data.get("X", np.nan)))
        y = float(data.get("y", data.get("Y", np.nan)))
        z = float(data.get("z", data.get("Z", np.nan)))

        return cls(x, y, z)

    @classmethod
    def from_array(cls, data) -> Vector3:
        return cls(data[0], data[1], data[2])

    def as_array(self) -> np.ndarray:
        return np.array([self.x, self.y, self.z])

    def __add__(self, value: Vector3) -> Vector3:
        vector1_arr = self.as_array()
        vector2_arr = value.as_array()
        result = vector1_arr + vector2_arr
        return Vector3.from_array(result)

    def __sub__(self, value: Vector3) -> Vector3:
        vector1_arr = self.as_array()
        vector2_arr = value.as_array()
        result = vector1_arr - vector2_arr
        return Vector3.from_array(result)

    @staticmethod
    def _to_degrees(radian: float) -> float:
        num = radian * 180.0 / 3.1415927
        if num > 0.0:
            return num
        return 360.0 + num

    @staticmethod
    def _to_radians(degree: float) -> float:
        return degree * 3.1415927 / 180.0

    def to_degrees(self) -> Vector3:
        X = self._to_degrees(self.x)
        Y = self._to_degrees(self.y)
        Z = self._to_degrees(self.z)
        return Vector3(X, Y, Z)

    def to_radians(self) -> Vector3:
        X = self._to_radians(self.x)
        Y = self._to_radians(self.y)
        Z = self._to_radians(self.z)
        return Vector3(X, Y, Z)

    def transform(self, rotation: Quaternion) -> Vector3:
        num = rotation.x + rotation.x
        num2 = rotation.y + rotation.y
        num3 = rotation.z + rotation.z
        num4 = rotation.w * num
        num5 = rotation.w * num2
        num6 = rotation.w * num3
        num7 = rotation.x * num
        num8 = rotation.x * num2
        num9 = rotation.x * num3
        num10 = rotation.y * num2
        num11 = rotation.y * num3
        num12 = rotation.z * num3

        X = self.x * (1.0 - num10 - num12) + self.y * (num8 - num6) + self.z * (num9 + num5)
        Y = self.x * (num8 + num6) + self.y * (1.0 - num7 - num12) + self.z * (num11 - num4)
        Z = self.x * (num9 - num5) + self.y * (num11 + num4) + self.z * (1.0 - num7 - num10)
        return Vector3(X, Y, Z)

    def from_world_to_local(self, child: Vector3, parent_world_quat: Quaternion) -> Vector3:
        value = child - self
        rotation = parent_world_quat.inverse()
        return value.transform(rotation)


# pylint: disable=invalid-name
class Quaternion:
    def __init__(self, x: float, y: float, z: float, w: float):
        self.x = x
        self.y = y
        self.z = z
        self.w = w

    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> Quaternion:
        x = float(data.get("x", data.get("X", np.nan)))
        y = float(data.get("y", data.get("Y", np.nan)))
        z = float(data.get("z", data.get("Z", np.nan)))
        w = float(data.get("w", data.get("W", np.nan)))

        return cls(x, y, z, w)

    @classmethod
    def from_array(cls, data) -> Quaternion:
        return cls(data[0], data[1], data[2], data[3])

    @classmethod
    def from_vector3(cls, vector: Vector3) -> Quaternion:
        return cls.from_yaw_pitch_roll(vector.y, vector.x, vector.z)

    @classmethod
    def from_vector3_degrees(cls, vector: Vector3) -> Quaternion:
        vector_radians = vector.to_radians()
        return cls.from_vector3(vector_radians)

    @classmethod
    def from_yaw_pitch_roll(cls, yaw: float, pitch: float, roll: float) -> Quaternion:
        x = roll * 0.5
        num = np.sin(x)
        num2 = np.cos(x)
        x2 = pitch * 0.5
        num3 = np.sin(x2)
        num4 = np.cos(x2)
        x3 = yaw * 0.5
        num5 = np.sin(x3)
        num6 = np.cos(x3)
        X = num6 * num3 * num2 + num5 * num4 * num
        Y = num5 * num4 * num2 - num6 * num3 * num
        Z = num6 * num4 * num - num5 * num3 * num2
        W = num6 * num4 * num2 + num5 * num3 * num
        return cls(X, Y, Z, W)

    def multiply(self, value: Quaternion) -> Quaternion:
        x = self.x
        y = self.y
        z = self.z
        w = self.w
        x2 = value.x
        y2 = value.y
        z2 = value.z
        w2 = value.w
        num = y * z2 - z * y2
        num2 = z * x2 - x * z2
        num3 = x * y2 - y * x2
        num4 = x * x2 + y * y2 + z * z2
        X = x * w2 + x2 * w + num
        Y = y * w2 + y2 * w + num2
        Z = z * w2 + z2 * w + num3
        W = w * w2 - num4
        return Quaternion(X, Y, Z, W)

    def multiply_constant(self, value: float) -> Quaternion:
        X = self.x * value
        Y = self.y * value
        Z = self.z * value
        W = self.w * value
        return Quaternion(X, Y, Z, W)

    def inverse(self):
        num = self.x * self.x + self.y * self.y + self.z * self.z + self.w * self.w
        num2 = 1.0 / num
        X = (0.0 - self.x) * num2
        Y = (0.0 - self.y) * num2
        Z = (0.0 - self.z) * num2
        W = self.w * num2
        return Quaternion(X, Y, Z, W)

    def to_euler_angles(self) -> Vector3:
        y = 2.0 * (self.w * self.x + self.y * self.z)
        x = 1.0 - 2.0 * (self.x * self.x + self.y * self.y)
        X = np.arctan2(y, x)
        num = 2.0 * (self.w * self.y - self.z * self.x)
        if np.abs(num) >= 1.0:
            Y = np.copysign(np.pi / 2.0, num)
        else:
            Y = np.arcsin(num)
        y2 = 2.0 * (self.w * self.z + self.x * self.y)
        x2 = 1.0 - 2.0 * (self.y * self.y + self.z * self.z)
        Z = np.arctan2(y2, x2)
        return Vector3(X, Y, Z)

    def from_local_to_world(self, local: Quaternion) -> Quaternion:
        return self.multiply(local)

    def from_world_to_local(self, world: Quaternion) -> Quaternion:
        world_inv = world.inverse()
        return world_inv.multiply(self)

    def correct_angle_by_rigid_body(self, name: str) -> Quaternion:
        if name == "lNipple":
            return Quaternion(self.x, -1.0 * self.y, -1.0 * self.z, -1.0 * self.w)
        if "rNipple" in name:
            return Quaternion(-1.0 * self.x, self.y, self.z, self.w)
        if "rShldr" in name:
            return Quaternion(self.y, self.x, self.z, self.w)
        if "lShldr" in name:
            return Quaternion(self.y, -1.0 * self.x, self.z, self.w)
        return Quaternion(self.x, self.y, self.z, self.w)


class RigidBody:
    postition: Vector3
    rotation: Vector3

    def __init__(self, **kwargs):
        self.position = None
        self.rotation = None

        for pos_key in ["position", "localPosition", "rootPosition"]:
            if pos_key in kwargs:
                self.position = Vector3.from_dict(kwargs[pos_key])

        for pos_key in ["rotation", "localRotation", "rootRotation"]:
            if pos_key in kwargs:
                self.rotation = Vector3.from_dict(kwargs[pos_key])


class RigidBodyUtils:
    LINKABLES: Dict[str, str] = {
        "hip": "root",
        "pelvis": "hip",
        "rThigh": "pelvis",
        "rShin": "rThigh",
        "rFoot": "rShin",
        "LGlute": "pelvis",
        "RGlute": "pelvis",
        "lThigh": "pelvis",
        "lShin": "lThigh",
        "lFoot": "lShin",
        "abdomen": "hip",
        "abdomen2": "abdomen",
        "chest": "abdomen2",
        "rCollar": "chest",
        "rShldr": "rCollar",
        "rForeArm": "rShldr",
        "rHand": "rForeArm",
        "lPectoral": "chest",
        "lNipple": "lPectoral",
        "rPectoral": "chest",
        "rNipple": "rPectoral",
        "neck": "chest",
        "head": "neck",
        "lCollar": "chest",
        "lShldr": "lCollar",
        "lForeArm": "lShldr",
        "lHand": "lForeArm",
        "penisBaseControl": "control",
        "penisMidControl": "control",
        "penisTipControl": "control",
    }

    HAIR_ONLY = ["head", "neck"]

    def __init__(self, atom: Dict):
        self.rigid_body_map = self.get_rigid_body_map(atom)

    @staticmethod
    def get_rigid_body_map(atom):
        rigid_bodies = {}
        for storable in atom["storables"]:
            if is_str_in_substrings("trigger", storable.keys()):
                continue
            contains_rigid = is_str_in_substrings("pos", storable.keys())
            if contains_rigid:
                rigid_bodies[storable["id"]] = storable
        return rigid_bodies

    def get_rigid_body(self, target_rigid_body_name: str):
        if target_rigid_body_name == "root":
            target_rigid_body_name = "hip"

        rigid_body_data = self.rigid_body_map[target_rigid_body_name]
        return RigidBody(**rigid_body_data)

    @staticmethod
    def get_cua_control(linked_cua):
        return next((storable for storable in linked_cua["storables"] if storable.get("id") == "control"), None)

    def get_linkable_rigid_body_names(self, target_rigid_body_name: str):
        links = []
        while target_rigid_body_name in self.LINKABLES:
            if target_rigid_body_name == "root":
                break
            links.append(target_rigid_body_name)
            target_rigid_body_name = self.LINKABLES.get(target_rigid_body_name)
        links = links[::-1]
        return links

    def get_world_quaternion(self, target_rigid_body_name: str) -> Quaternion:
        if target_rigid_body_name == "root":
            rotation = self.get_rigid_body("root").rotation
            return Quaternion.from_vector3_degrees(rotation)

        rotation = self.get_rigid_body("root").rotation
        result = Quaternion.from_vector3_degrees(rotation)
        linkable_rigid_body_names = self.get_linkable_rigid_body_names(target_rigid_body_name)
        for item in linkable_rigid_body_names:
            if item != "hip":
                item_rotation = self.get_rigid_body(item).rotation
                item_q = Quaternion.from_vector3_degrees(item_rotation)
                item_q = item_q.correct_angle_by_rigid_body(item)
                result = result.multiply(item_q)
        return result

    def get_world_position(self, target_rigid_body_name: str) -> Vector3:
        if target_rigid_body_name == "root":
            return self.get_rigid_body("root").position

        result = self.get_rigid_body("root").position
        linkable_rigid_body_names = self.get_linkable_rigid_body_names(target_rigid_body_name)
        for item in linkable_rigid_body_names:
            if item != "hip":
                world_quaternion = self.get_world_quaternion(item)
                item_position = self.get_rigid_body(item).position
                item_rotation = self.get_rigid_body(item).rotation
                item_quaternion = Quaternion.from_vector3_degrees(item_rotation)
                item_quaternion = item_quaternion.inverse()

                world_item_quaternion = world_quaternion.multiply(item_quaternion)
                vector = item_position.transform(world_item_quaternion)
                result = result + vector
        return result

    def get_cua_local_quaternion(self, target_rigid_body_name: str, cua_world_rotation: Vector3) -> Quaternion:
        cua_world_quaternion = Quaternion.from_vector3_degrees(cua_world_rotation)
        world_quaternion = self.get_world_quaternion(target_rigid_body_name)
        world_to_local_quaternion = world_quaternion.from_world_to_local(cua_world_quaternion)
        world_to_local_quaternion = world_to_local_quaternion.multiply_constant(-1.0)
        return world_to_local_quaternion

    def get_cua_local_position(self, target_rigid_body_name: str, cua_world_position: Vector3):
        world_quaternion = self.get_world_quaternion(target_rigid_body_name)
        world_position = self.get_world_position(target_rigid_body_name)
        world_to_local_position = world_position.from_world_to_local(cua_world_position, world_quaternion)
        return world_to_local_position

    def get_data_for_cuablink(self, cua_rigid_body: RigidBody, target_rigid_body_name: str):
        cua_world_position = cua_rigid_body.position
        cua_world_rotation = cua_rigid_body.rotation

        # world_position = self.get_world_position(target_rigid_body_name)
        # world_quaternion = self.get_world_quaternion(target_rigid_body_name)
        cua_local_quaternion = self.get_cua_local_quaternion(target_rigid_body_name, cua_world_rotation)
        cua_local_position = self.get_cua_local_position(target_rigid_body_name, cua_world_position)
        vector_radians = cua_local_quaternion.to_euler_angles()
        vector_degrees = vector_radians.to_degrees()

        return {
            "id": "cuabLinkTo",
            "linkTo": target_rigid_body_name,
            "posx": str(np.round(cua_local_position.x, decimals=7)),
            "posy": str(np.round(cua_local_position.y, decimals=7)),
            "posz": str(np.round(cua_local_position.z, decimals=7)),
            "rotx": str(np.round(vector_degrees.x, decimals=7)),
            "roty": str(np.round(vector_degrees.y, decimals=7)),
            "rotz": str(np.round(vector_degrees.z, decimals=7)),
        }

    def update_cuab_link(self, linked_cua, hair_only=False):
        cua_control = self.get_cua_control(linked_cua)
        cua_rigid_body = RigidBody(**cua_control)
        target_rigid_body_name = cua_control["linkTo"].split(":")[-1]
        if hair_only and target_rigid_body_name not in self.HAIR_ONLY:
            return None
        cuab_link = self.get_data_for_cuablink(cua_rigid_body, target_rigid_body_name)
        return cuab_link

    def get_linked_cua_atoms(self, json_data, atom_id, hair_only=False):
        linked_cuas = self.parse_linked_cua_atoms(json_data, filter_id=atom_id)
        if len(linked_cuas) == 0:
            return []

        linked_cua_atoms = []
        for linked_cua in linked_cuas:
            cuab_link = self.update_cuab_link(linked_cua, hair_only=hair_only)
            if cuab_link is not None:
                linked_cua["storables"].append(cuab_link)
                linked_cua_atoms.append(linked_cua)

        return linked_cua_atoms

    @classmethod
    def parse_linked_cua_atoms(cls, atom_elems, filter_id=None):
        linked_cua_atoms = []
        for atom_elem in atom_elems:
            is_custom_unity_asset = atom_elem.get("type") == "CustomUnityAsset"
            if is_custom_unity_asset and cls.contains_cua_linkto_storable(atom_elem["storables"]):
                if filter_id:
                    atom_control = cls.get_linked_cua_atom_control(atom_elem)
                    link_from = cls.get_linked_cua_atom_link_from(atom_control)
                    if filter_id != link_from:
                        continue
                linked_cua_atoms.append(atom_elem)
        return linked_cua_atoms

    @staticmethod
    def contains_cua_linkto_storable(storables):
        if storables is None:
            return None
        return len([e for e in storables if e["id"] == "control" and "linkTo" in e.keys()]) > 0

    @classmethod
    def get_linked_cua_atom_control(cls, atom_elem):
        return next((storable for storable in atom_elem["storables"] if storable["id"] == "control"), {})

    @classmethod
    def get_linked_cua_atom_link_from(cls, linked_cua_atom_control):
        return linked_cua_atom_control.get("linkTo", "").split(":")[0]
