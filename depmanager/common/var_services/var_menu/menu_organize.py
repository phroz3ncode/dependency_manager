from os import path

from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.var_services.databases.image_lib_database import ImageLibDatabase
from depmanager.common.var_services.enums import OrganizeMethods
from depmanager.common.var_services.var_menu.base_actions_menu import BaseActionsMenu


class MenuOrganize(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("ORGANIZE remote vars", self.organize_remote),
                ConsoleMenuItem("ORGANIZE remote vars with image_lib", self.organize_with_image_lib),
                ConsoleMenuItem("CREATE *.dep from local image_lib", self.build_dep_from_image_lib),
                ConsoleMenuItem("TAG unused vars", self.add_unused_var_tags),
                ConsoleMenuItem("TAG used vars", self.add_used_var_tags),
                ConsoleMenuItem("TAG vars with suffix from *.dep", self.add_suffix_var_tags),
                ConsoleMenuItem("TAG unused vars for removed directories", self.tag_unused_remove),
                ConsoleMenuItem("UNTAG unused vars", self.remove_unused_var_tags),
                ConsoleMenuItem("UNTAG used vars", self.remove_used_var_tags),
            ],
        )

    def organize_remote(self):
        self.cache.auto_organize_remote_files()

    def add_unused_var_tags(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.ADD_UNUSED_TAG, filters=filters)

    def remove_unused_var_tags(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.REMOVE_UNUSED_TAG, filters=filters)

    def add_used_var_tags(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.ADD_USED_TAG, filters=filters)

    def remove_used_var_tags(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.REMOVE_USED_TAG, filters=filters)

    def add_suffix_var_tags(self):
        filters = self.get_filename()
        self.cache.organize_remote_files(mode=OrganizeMethods.SUFFIX_DEP, filters=filters)

    def build_dep_from_image_lib(self):
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        image_db.build_dep_from_database()

    def organize_with_image_lib(self):
        self.cache.remote_db.refresh_files(quick=True)
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        image_db.load()
        missing_vars = image_db.update()
        self.cache.remote_db.display_var_list(missing_vars, "Missing Images")
        input("Press ENTER when you are finished organizing the image_lib...")
        image_lib_sub_directories = image_db.get_sub_directories_from_database()

        # Move vars to new subdirectories
        for var_id, var_item in self.cache.remote_db.vars.items():
            new_subdir = image_lib_sub_directories.get(var_id)
            if new_subdir is None:
                print(f"Moving to removed {var_id}: {var_item.sub_directory} to removed")
                self.cache.remote_db.manipulate_file(
                    var_id,
                    path.join(var_item.root_path, "removed"),
                    move=True,
                )
            elif var_item.sub_directory != new_subdir:
                print(f"Moving {var_id}: {var_item.sub_directory} to {new_subdir}")
                self.cache.remote_db.manipulate_file(
                    var_id,
                    path.join(var_item.root_path, new_subdir),
                    move=True,
                )

        self.cache.remote_db.save()
        image_db.save()

    def tag_unused_remove(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.ADD_REMOVE_TAG, filters=filters)
