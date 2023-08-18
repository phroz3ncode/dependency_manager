import os

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
        self.cache.clear()

    def organize_with_image_lib(self):
        self.cache.remote.db.refresh()
        self.cache.remote.db.refresh_image_db()
        input("Press ENTER when you are finished organizing the image_lib...")
        image_lib_sub_directories = self.cache.remote.db.image_file_subdirs

        # Move vars to new subdirectories
        for var_id, var_item in self.cache.remote.db.vars.items():
            new_subdir = image_lib_sub_directories.get(var_id)
            if new_subdir is None:
                print(f"Moving to removed {var_id}: {var_item.sub_directory} to removed")
                self.cache.remote.db.manipulate_file(
                    var_id,
                    os.path.join(var_item.root_path, "removed"),
                    move=True,
                )
            elif var_item.sub_directory != new_subdir:
                print(f"Moving {var_id}: {var_item.sub_directory} to {new_subdir}")
                self.cache.remote.db.manipulate_file(
                    var_id,
                    os.path.join(var_item.root_path, new_subdir),
                    move=True,
                )

        self.cache.remote.db.save()
        self.cache.remote.db.save_image_db()
