from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.var_services.databases.image_lib_database import ImageLibDatabase
from depmanager.common.var_services.var_menu.base_actions_menu import BaseActionsMenu
from depmanager.common.var_services.var_menu.menu_maintenance import MenuMaintenance
from depmanager.common.var_services.var_menu.menu_organize import MenuOrganize


class MenuMain(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("Refresh remote database", self.refresh_full),
                ConsoleMenuItem(
                    "Add missing local dependencies from remote",
                    self.fix_local_missing,
                ),
                ConsoleMenuItem("Add new local to remote", self.organize_local_to_remote),
                ConsoleMenuItem(
                    "Var file maintenance",
                    MenuMaintenance(self.cache, self.is_admin).menu,
                ),
                ConsoleMenuItem(
                    "Organize remote vars",
                    MenuOrganize(self.cache, self.is_admin).menu,
                ),
            ],
        )

    def refresh_full(self):
        self.cache.remote_db.refresh_files()
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        image_db.load()
        missing_vars = image_db.update(save_after_update=True)
        self.cache.remote_db.display_var_list(missing_vars, "Missing Images")
        self.cache.clear()

    def fix_local_missing(self):
        self.cache.fix_local_missing(self.is_admin)

    def organize_local_to_remote(self):
        filters = self.get_var_filters()
        self.cache.auto_organize_local_files_to_remote(filters=filters)
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        image_db.load()
        image_db.update(save_after_update=True)
        self.cache.clear()
