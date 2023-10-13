from orjson import orjson

from depmanager.common.enums.content_type import ContentType
from depmanager.common.enums.ext import Ext
from depmanager.common.var_object.var_object import VarObject


class ClothingParser:
    def __init__(self, var_ref: VarObject):
        self.var = var_ref

    @property
    def valid(self):
        return self.var.contains[ContentType.CLOTHING]

    def extract(self):
        if not self.valid:
            return None

        storables = []
        clothing_items = [v for v, _ in self.var.infolist if all(item in v for item in ("Custom/Clothing", Ext.VAM))]

        for item in clothing_items:
            item_name = item.split("/")[-1]
            item_name = item_name.replace(Ext.VAM, "")
            storables.append(
                {
                    "id": f"{self.var.clean_name}:/{item}",
                    "internalId": f"{self.var.author}:{item_name}",
                    "enabled": "true",
                }
            )

        if len(storables) == 0:
            return None

        preset = {"setUnlistedParamsToDefault": "true", "storables": [{"id": "geometry", "clothing": storables}]}
        preset_json = orjson.dumps(preset, option=orjson.OPT_INDENT_2).decode("UTF-8")
        return preset_json
