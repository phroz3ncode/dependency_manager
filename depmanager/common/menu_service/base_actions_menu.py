import os

from depmanager.common.enums.ext import Ext
from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.var_database_service.var_database_service import VarDatabaseService


class BaseActionsMenu:
    cache: VarDatabaseService

    def __init__(self, cache: VarDatabaseService):
        self.cache = cache

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

    def copy_remote_var_list_to_local(self, var_list, sub_dir):
        if len(var_list) == 0:
            return
        progress = ProgressBar(len(var_list), description=f"Copying {len(var_list)} {sub_dir} to local")
        os.makedirs(os.path.join(self.cache.local.db.rootpath, sub_dir), exist_ok=True)
        for var_id in var_list:
            progress.inc()
            var = self.cache.remote.db[var_id]
            self.cache.remote.db.manipulate_file(
                var.var_id,
                os.path.join(self.cache.local.db.rootpath, sub_dir, var.sub_directory),
                move=False,
                symlink=False,
                track_move=False,
            )

    def filter_remote_var_list(self, var_list, filters=None):
        if filters is None:
            return var_list
        return {v for v in var_list if are_substrings_in_str(self.cache.remote.db[v].sub_directory, filters)}
