from depmanager.common.enums.content_type import ContentType
from depmanager.common.enums.ext import Ext
from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.var_database.var_database import VarDatabase


class DatabaseServiceTools:
    @staticmethod
    def get_suffix_dep(filepath):
        with open(filepath, "r", encoding="UTF-8") as read_file:
            return {line.rstrip().replace(Ext.VAR, Ext.EMPTY) for line in read_file}

    @staticmethod
    def _get_repairable(database: VarDatabase, filters=None, include_clothing=False):
        var_list = []
        for var_id, var in database.vars.items():
            can_include = var.var_type.is_repairable
            if include_clothing:
                can_include = var.var_type.is_repairable or var.var_type.type in (
                    ContentType.CLOTHING,
                    ContentType.TEXTURE,
                )
            if not can_include:
                continue
            if filters is not None and not are_substrings_in_str(var.sub_directory, filters):
                continue
            var_list.append(var_id)
        return sorted(set(var_list))
