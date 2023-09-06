from depmanager.common.menu_service.base_actions_menu import BaseActionsMenu
from depmanager.common.menu_service.menu_maintenance import MenuMaintenance
from depmanager.common.shared.console_menu_item import ConsoleMenuItem


class MenuMain(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("Refresh remote database", self.refresh_full),
                ConsoleMenuItem("Fix missing local dependencies", self.fix_local_missing),
                ConsoleMenuItem("Add new local to remote", self.organize_local_to_remote),
                ConsoleMenuItem("Organize remote vars with image_lib", self.organize_with_image_lib),
                ConsoleMenuItem("> MAINTENANCE TOOLS <", MenuMaintenance(self.cache).menu),
            ],
        )

    def refresh_full(self):
        self.cache.remote.auto_organize()
        self.cache.remote.check_health()

    def fix_local_missing(self):
        self.cache.fix_local_missing()

    def organize_local_to_remote(self):
        filters = self.get_var_filters()
        self.cache.auto_organize_local_files_to_remote(filters=filters)

    def organize_with_image_lib(self):
        self.cache.remote.db.organize_with_image_db()
