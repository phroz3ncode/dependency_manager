import json
import os
from typing import Dict
from typing import Optional

from depmanager.common.enums.content_type import ContentType
from depmanager.common.enums.ext import Ext
from depmanager.common.enums.methods import OrganizeMethods
from depmanager.common.enums.paths import ADDON_PACKAGE_USER_PREFS_DIR
from depmanager.common.enums.plugins import PLUGIN_BLACKLIST_ENABLE_BY_DEFAULT
from depmanager.common.enums.plugins import PLUGIN_TEMPLATE_DISABLE
from depmanager.common.enums.plugins import PLUGIN_TEMPLATE_ENABLE
from depmanager.common.enums.variables import GIGABYTE
from depmanager.common.shared.cached_object import CachedObject
from depmanager.common.shared.cached_property import cached_property
from depmanager.common.shared.tools import remove_empty_directories
from depmanager.common.var_database.var_database import VarDatabase
from depmanager.common.var_database_service.database_service_tools import DatabaseServiceTools


class DatabaseService(CachedObject, DatabaseServiceTools):
    def __init__(
        self, root: str, image_root: str = None, quick_scan: bool = False, favorites: Dict[str, Optional[str]] = None
    ):
        self.root = root
        self.image_root = image_root
        self.quick_scan = quick_scan
        self.favorites = favorites

    @property
    def _attributes(self):
        return ["db"]

    @cached_property
    # pylint: disable=invalid-name
    def db(self) -> VarDatabase:
        return VarDatabase(self.root, image_root=self.image_root, quick_scan=self.quick_scan, favorites=self.favorites)

    def refresh(self):
        self.db.refresh()
        if self.db.image_db_enabled:
            self.db.save()
            self.db.refresh_image_db()
            self.db.save_image_db()

    @property
    def path(self):
        return self.root

    @property
    def duplicates(self):
        return self.db.find_unversioned_duplicates()

    @property
    def missing(self):
        return self.db.find_missing_vars()

    @property
    def required_vars(self) -> set[str]:
        required_vars = self.db.unique_required_dependencies
        required_vars.update(self.db.get_var_ids_from_deps())
        required_vars.update(self.db.get_var_ids_from_sync_folder())
        return required_vars

    def display_list(self, var_id_list, prefix, show_used_by=False):
        self.db.display_var_list(var_id_list, prefix, show_used_by)

    def get_unused(self, filters=None):
        return self.db.find_unused_vars(filters=filters)

    def get_used(self, filters=None):
        return self.db.find_unused_vars(filters=filters, invert=True)

    def get_repairable(self, filters=None, include_clothing=False):
        return self._get_repairable(self.db, filters, include_clothing)

    def enable_plugins(self):
        pref_path = os.path.join(
            os.path.abspath(os.path.join(self.db.rootpath, "..")),
            ADDON_PACKAGE_USER_PREFS_DIR,
        )
        if not os.path.exists(pref_path):
            return
        for var_id, var in self.db.vars.items():
            if var.var_type.contains_type(ContentType.PLUGIN):
                file_path = os.path.join(pref_path, f"{var_id}{Ext.PREFS}")
                with open(file_path, "w", encoding="UTF-8") as write_file:
                    if var.duplicate_id in PLUGIN_BLACKLIST_ENABLE_BY_DEFAULT:
                        json.dump(PLUGIN_TEMPLATE_DISABLE, write_file, indent=4)
                    else:
                        json.dump(PLUGIN_TEMPLATE_ENABLE, write_file, indent=4)

    def organize_files(self, mode, filters=None, remove_empty=True):
        if mode == OrganizeMethods.AUTO:
            self.db.manipulate_file_list(self.db.keys, sub_directory="AUTO", desc="Auto organizing vars")
        elif mode == OrganizeMethods.ADD_UNUSED_TAG:
            var_list = self.get_unused(filters)
            self.db.manipulate_file_list(var_list, "unused", suffix=True, desc="Tagging unused vars")
        elif mode == OrganizeMethods.REMOVE_UNUSED_TAG:
            var_list = self.get_unused(filters)
            self.db.manipulate_file_list(var_list, "unused", remove=True, desc="Untagging unused vars")
        elif mode == OrganizeMethods.ADD_USED_TAG:
            var_list = self.get_used(filters)
            self.db.manipulate_file_list(var_list, "used", suffix=True, desc="Tagging used vars")
        elif mode == OrganizeMethods.REMOVE_USED_TAG:
            var_list = self.get_used(filters)
            self.db.manipulate_file_list(var_list, "used", remove=True, desc="Untagging used vars")
            self.db.manipulate_file_list(var_list, "removed")
        elif mode == OrganizeMethods.TO_VERSIONED:
            self.db.manipulate_file_list(self.duplicates, "_versioned", desc="Versioning duplicate vars")
        elif mode == OrganizeMethods.SUFFIX_DEP:
            var_list = self.get_suffix_dep(filters)
            self.db.manipulate_file_list(var_list, filters.replace(Ext.DEP, Ext.EMPTY), suffix=True)

        if remove_empty:
            remove_empty_directories(self.db.rootpath)

    def auto_organize(self):
        self.db.refresh()
        self.organize_files(mode=OrganizeMethods.AUTO, remove_empty=False)
        self.organize_files(mode=OrganizeMethods.TO_VERSIONED, remove_empty=False)
        self.organize_files(mode=OrganizeMethods.ADD_UNUSED_TAG, filters=["_versioned"], remove_empty=False)
        remove_empty_directories(self.db.rootpath)
        if self.db.image_db_enabled:
            self.db.save()
            self.db.refresh_image_db()
            self.db.save_image_db()

    def check_health(self):
        print(f"Checking health of {self.path}")
        size = sum(var_data.info["size"] for _, var_data in self.db.vars.items())
        missing = self.missing
        if self.db.image_db_enabled:
            duplicates = self.duplicates
            unused_versioned = self.get_unused(["_versioned"])
            unoptimized_vars = self.db.find_unoptimized_vars()
            broken_vars = self.db.find_broken_vars(health_check=True)
            print("\nResults:")
            print(f"Remote size: {len(self.db)} vars - {round(size / GIGABYTE, 2)} GB")
            self.display_list(missing, "Missing", show_used_by=True)
            self.display_list(duplicates, "Unversioned duplicate")
            self.display_list(unused_versioned, "Unused version")
            self.display_list(unoptimized_vars, "Unoptimized dependencies")
            self.display_list(broken_vars, "Broken")
        else:
            self.display_list(missing, "Missing", show_used_by=True)
