import os
import zipfile

from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.var_services.databases.image_lib_database import ImageLibDatabase
from depmanager.common.var_services.var_menu.base_actions_menu import BaseActionsMenu
from depmanager.common.var_services.var_menu.menu_maintenance import MenuMaintenance


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
                ConsoleMenuItem("Organize remote vars with image_lib", self.organize_with_image_lib),
                ConsoleMenuItem(
                    "Backup custom settings to zip",
                    self.backup_custom,
                ),
                ConsoleMenuItem(
                    "MAINTENANCE TOOLS",
                    MenuMaintenance(self.cache).menu,
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
        self.cache.auto_check_remote_files_health()

    def fix_local_missing(self):
        self.cache.fix_local_missing()
        self.cache.auto_check_local_files_health()

    def organize_local_to_remote(self):
        filters = self.get_var_filters()
        self.cache.auto_organize_local_files_to_remote(filters=filters)
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        image_db.load()
        image_db.update(save_after_update=True)
        self.cache.clear()

    def backup_custom(self):
        root_path = os.path.abspath(os.path.join(self.cache.local_path, ".."))
        zip_root_path = os.path.abspath(os.path.join(root_path, ".."))

        zip_name = os.path.join(root_path, "vam_custom.zip")
        if os.path.exists(zip_name):
            os.remove(zip_name)

        exclude_files = [
            "config",
            "MHLab.PATCH.dll",
            "migrate.log",
            "UnityCrashHandler64.exe",
            "UnityPlayer.dll",
            "VaM (Desktop Mode).bat",
            "VaM.exe",
            "VaM_Updater.exe",
            "version",
            "vrmanifest",
            "WinPixEventRuntime.dll",
        ]
        includes = {
            root_path: ["AddonPackages", "AddonPackagesUserPrefs", "Custom", "Keys", "Saves"],
            os.path.join(root_path, "AddonPackages"): ["_session"],
            os.path.join(root_path, "Custom"): ["PluginPresets"],
            os.path.join(root_path, "Saves"): ["PluginData", "scene"],
            os.path.join(root_path, "Saves", "scene"): ["MeshedVR"],
        }
        file_list = []
        for root, dirs, files in os.walk(root_path, topdown=True):
            if root in includes:
                dirs[:] = [d for d in dirs if d in includes[root]]
            for file in files:
                if file not in exclude_files:
                    file_list.append(os.path.join(root, file))
        with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf_dest:
            for item in file_list:
                zf_dest.write(item, os.path.relpath(item, zip_root_path), compress_type=zipfile.ZIP_DEFLATED)

    def organize_with_image_lib(self):
        self.cache.remote_db.refresh_files()
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
                    os.path.join(var_item.root_path, "removed"),
                    move=True,
                )
            elif var_item.sub_directory != new_subdir:
                print(f"Moving {var_id}: {var_item.sub_directory} to {new_subdir}")
                self.cache.remote_db.manipulate_file(
                    var_id,
                    os.path.join(var_item.root_path, new_subdir),
                    move=True,
                )

        self.cache.remote_db.save()
        image_db.save()
