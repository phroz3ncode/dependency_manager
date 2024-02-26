import os
from zipfile import ZIP_DEFLATED

from depmanager.common.enums.ext import Ext
from depmanager.common.enums.variables import TEMP_VAR_NAME
from depmanager.common.menu_service.base_actions_menu import BaseActionsMenu
from depmanager.common.parser.appearance_parser import AppearanceParser
from depmanager.common.parser.clothing_parser import ClothingParser
from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.ziptools import ZipReadInto
from depmanager.common.shared.ziptools import ZipWrite


class MenuExtract(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("BACKUP local settings", self.backup_local_settings),
                ConsoleMenuItem("EXTRACT appearances", self.extract_appearance_presets),
                ConsoleMenuItem("EXTRACT clothing", self.extract_clothing_presets),
                ConsoleMenuItem("SYNC clothing presets to vars", self.sync_clothing_presets),
            ],
        )

    def backup_local_settings(self):
        root_path = os.path.abspath(os.path.join(self.cache.local.path, ".."))
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
            "VaM_EULA.html",
            "VaM_Updater.exe",
            "version",
            "vrmanifest",
            "WinPixEventRuntime.dll",
        ]
        includes = {
            root_path: ["AddonPackages", "Custom", "Keys", "Tools", "Saves"],
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
        with ZipWrite(zip_name, compress=False) as zf_dest:
            for item in file_list:
                zf_dest.write(item, os.path.relpath(item, zip_root_path))

    def extract_appearance_presets(self):
        self.cache.local.refresh()

        appearance_storage = os.path.realpath(
            os.path.join(self.cache.local.db.rootpath, "..", "Custom", "Atom", "Person", "Appearance")
        )
        linked_storage = os.path.realpath(
            os.path.join(self.cache.local.db.rootpath, "..", "Custom", "Scripts", "Blazedust", "CUAManager", "presets")
        )
        os.makedirs(appearance_storage, exist_ok=True)
        os.makedirs(linked_storage, exist_ok=True)

        for _, var_ref in self.cache.local.db.vars.items():
            parser = AppearanceParser(var_ref)
            parser.extract_to_file(appearance_storage, linked_storage)

    def extract_clothing_presets(self):
        self.cache.local.refresh()
        preset_storage = os.path.join(self.cache.local.db.rootpath, "presets_clothing")
        os.makedirs(preset_storage, exist_ok=True)

        progress = ProgressBar(len(self.cache.local.db.vars), description="Extracting clothing presets")
        for var_id, var_ref in self.cache.local.db.vars.items():
            progress.inc()
            parser = ClothingParser(var_ref)
            found = parser.extract()
            if found is not None:
                write_file_path = os.path.join(preset_storage, f"Preset_{var_id}{Ext.VAP}")
                with open(write_file_path, "w", encoding="UTF-8") as write_file:
                    write_file.write(found)

    def sync_clothing_presets(self):
        self.cache.local.refresh()
        preset_storage = os.path.join(self.cache.local.db.rootpath, "presets_clothing")
        os.makedirs(preset_storage, exist_ok=True)

        preset_files = os.listdir(preset_storage)
        unique_presets = list(
            set(preset.replace(Ext.VAP, "").replace(Ext.JPG, "").replace("Preset_", "") for preset in preset_files)
        )

        progress = ProgressBar(len(self.cache.local.db.vars), description="Syncing clothing presets")
        for var_id, var_ref in self.cache.local.db.vars.items():
            progress.inc()
            if var_id in unique_presets:
                temp_file = os.path.join(var_ref.directory, TEMP_VAR_NAME)
                with ZipReadInto(var_ref.file_path, temp_file) as (zf_src, zf_dest):
                    for item in zf_src.infolist():
                        zf_dest.writestr(item.filename, zf_src.read(item.filename), ZIP_DEFLATED)
                    with open(os.path.join(preset_storage, f"Preset_{var_ref.clean_name}{Ext.JPG}"), "rb") as read_file:
                        zf_dest.writestr(
                            f"Custom/Atom/Person/Clothing/Preset_{var_ref.clean_name}{Ext.JPG}",
                            read_file.read(),
                            ZIP_DEFLATED,
                        )
                    with open(os.path.join(preset_storage, f"Preset_{var_ref.clean_name}{Ext.VAP}"), "rb") as read_file:
                        zf_dest.writestr(
                            f"Custom/Atom/Person/Clothing/Preset_{var_ref.clean_name}{Ext.VAP}",
                            read_file.read(),
                            ZIP_DEFLATED,
                        )

                os.remove(var_ref.file_path)
                os.rename(temp_file, var_ref.file_path)
