import os
import zipfile

from depmanager.common.enums.paths import TEMP_REPAIR_DIR
from depmanager.common.menu_service.base_actions_menu import BaseActionsMenu
from depmanager.common.shared.console_menu_item import ConsoleMenuItem

# from depmanager.common.menu_service.menu_maintenance import MenuMaintenance


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
                ConsoleMenuItem("Repair remote vars", self.repair_and_optimize),
                ConsoleMenuItem(
                    "Backup custom settings to zip",
                    self.backup_custom,
                ),
                # ConsoleMenuItem(
                #     "MAINTENANCE TOOLS",
                #     MenuMaintenance(self.cache).menu,
                # ),
            ],
        )

    def refresh_full(self):
        self.cache.remote.auto_organize()
        self.cache.remote.check_health()

    def fix_local_missing(self):
        self.cache.fix_local_missing()
        # self.cache.auto_check_local_files_health()

    def organize_local_to_remote(self):
        filters = self.get_var_filters()
        self.cache.auto_organize_local_files_to_remote(filters=filters)
        self.cache.clear()

    def backup_custom(self):
        root_path = os.path.abspath(os.path.join(self.cache.local.path, "../var_services"))
        zip_root_path = os.path.abspath(os.path.join(root_path, "../var_services"))

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
            "VaM_EULA.html",
            "VaM_Updater.exe",
            "version",
            "vrmanifest",
            "WinPixEventRuntime.dll",
        ]
        includes = {
            root_path: ["AddonPackages", "AddonPackagesUserPrefs", "Custom", "Keys", "Tools", "Saves"],
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

    def repair_and_optimize(self):
        filters = self.get_var_filters()

        self.cache.remote.refresh()

        var_to_process = set()
        var_to_process.update(self.cache.remote.db.find_unoptimized_vars())
        var_to_process.update(self.cache.remote.db.find_broken_vars())

        var_to_process = self.filter_remote_var_list(var_to_process, filters)
        self.copy_remote_var_list_to_local(var_to_process, TEMP_REPAIR_DIR)
        self.cache.local.clear()
        print(f"Please place all vars to repair/optimize inside a '{TEMP_REPAIR_DIR}' folder...")
        repairable_var_ids = [
            k for k, value in self.cache.local.db.vars.items() if TEMP_REPAIR_DIR in value.sub_directory
        ]
        for var_id in repairable_var_ids:
            var_ref = self.cache.local.db[var_id]
            repaired = self.cache.remote.db.repair_broken_var(var_ref, remove_confirm=False, remove_skip=True)
            if not repaired:
                continue
            self.cache.remote.db.repair_metadata(var_ref)
