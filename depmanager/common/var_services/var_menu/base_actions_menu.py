from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.var_services.databases.var_cache_service import VarCacheService
from depmanager.common.var_services.enums import Ext


class BaseActionsMenu:
    cache: VarCacheService

    def __init__(self, cache: VarCacheService, is_admin: bool = False):
        self.cache = cache
        self.is_admin = is_admin

    def menu(self) -> ConsoleMenuItem:
        raise NotImplementedError("implement in descendents")

    @staticmethod
    def get_var_filters() -> list[str]:
        filters = input("Filter vars? (blank to use no filter, column separated: ").strip()
        filters = None if len(filters) == 0 else filters.split(",")
        return filters

    @staticmethod
    def get_filename() -> str:
        filename = input("Name of the file to use: ").strip()
        if filename[-4:] != Ext.DEP:
            filename = f"{filename}{Ext.DEP}"
        return filename
