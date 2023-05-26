import os

from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.shared.enums import MEGABYTE
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.var_services.databases.image_lib_database import ImageLibDatabase
from depmanager.common.var_services.enums import TEMP_REPAIR_DIR
from depmanager.common.var_services.enums import OrganizeMethods
from depmanager.common.var_services.var_menu.base_actions_menu import BaseActionsMenu


class MenuMaintenance(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("ORGANIZE remote vars", self.organize_remote),
                ConsoleMenuItem("CREATE *.dep from local image_lib", self.build_dep_from_image_lib),
                ConsoleMenuItem("REPAIR - Find and repair broken vars", self.find_and_repair),
                ConsoleMenuItem("REPAIR - Find and optimize var dependencies", self.find_and_optimize),
                ConsoleMenuItem("REPAIR - Compress vars images [SLOW]", self.compress_local),
                ConsoleMenuItem("FIND what uses var", self.search_that_use),
                ConsoleMenuItem("FIND low value vars", self.search_low_value),
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

    def refresh_image_lib(self):
        image_db = ImageLibDatabase(self.cache.remote_db, self.cache.local_path)
        missing_vars = image_db.update(save_after_update=True)
        self.cache.remote_db.display_var_list(missing_vars, "Missing Images")

    def check_remote_health(self):
        self.cache.clear()
        self.cache.auto_check_remote_files_health()

    def check_local_health(self):
        self.cache.clear()
        self.cache.auto_check_local_files_health()

    def compress_local(self):
        self.cache.clear()
        filters = self.get_var_filters()
        self.cache.compress_local(filters)
        self.cache.clear()

    def _copy_var_list_to_local(self, var_list, sub_dir):
        if len(var_list) == 0:
            return
        progress = ProgressBar(len(var_list), description=f"Copying {len(var_list)} {sub_dir} to local")
        os.makedirs(os.path.join(self.cache.local_db.rootpath, sub_dir), exist_ok=True)
        for var_id in var_list:
            progress.inc()
            var = self.cache.remote_db[var_id]
            self.cache.remote_db.manipulate_file(
                var.var_id,
                os.path.join(self.cache.local_db.rootpath, sub_dir, var.sub_directory),
                move=False,
                symlink=False,
            )

    def _filter_var_list(self, var_list, filters=None):
        if filters is None:
            return var_list
        return {v for v in var_list if are_substrings_in_str(self.cache.remote_db[v].sub_directory, filters)}

    def _get_filters(self):
        filters = self.get_var_filters()
        self.cache.clear()
        self.cache.remote_db.refresh_files()
        return filters

    def find_and_optimize(self):
        filters = self._get_filters()
        var_to_process = self.cache.remote_db.find_unoptimized_vars()
        var_to_process = self._filter_var_list(var_to_process, filters)
        self._copy_var_list_to_local(var_to_process, TEMP_REPAIR_DIR)
        self.cache.local_db_cache = None
        print("Please place all vars to optimize inside a 'optimize' folder at the root...")
        optimizable_var_ids = [
            k for k, value in self.cache.local_db.vars.items() if TEMP_REPAIR_DIR in value.sub_directory
        ]
        for var_id in optimizable_var_ids:
            self.cache.remote_db.repair_metadata(self.cache.local_db[var_id])

    def find_and_repair(self):
        filters = self._get_filters()
        var_to_process = self.cache.remote_db.find_broken_vars()
        var_to_process = self._filter_var_list(var_to_process, filters)
        self._copy_var_list_to_local(var_to_process, TEMP_REPAIR_DIR)
        self.cache.local_db_cache = None
        print("Please place all vars to optimize inside a 'repair' folder at the root...")
        repairable_var_ids = [
            k for k, value in self.cache.local_db.vars.items() if TEMP_REPAIR_DIR in value.sub_directory
        ]
        for var_id in repairable_var_ids:
            self.cache.remote_db.repair_broken_var(self.cache.local_db[var_id], remove_skip=True)

    def search_that_use(self):
        var_name = input("Name: ").strip()
        # noinspection PyTypeChecker
        required_by = self.cache.remote_db.vars_required.get(var_name)
        if required_by is None or len(required_by) == 0:
            print("Not used as a dependency by any vars.")
        else:
            print("Used by:")
            for var in required_by:
                print(var)

    def search_low_value(self):
        self.cache.clear()
        required_by = self.cache.remote_db.vars_required
        low_value = []
        for var_id, var_reqs in required_by.items():
            if len(var_reqs) == 1:
                var_item = self.cache.remote_db[str(var_id)]
                if var_item.info["size"] > 100 * MEGABYTE:
                    low_value.append((var_item.info["size"] / MEGABYTE, var_id, var_reqs))
        for var_id in sorted(low_value, reverse=True):
            print(var_id)

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

    def tag_unused_remove(self):
        filters = self.get_var_filters()
        self.cache.organize_remote_files(mode=OrganizeMethods.ADD_REMOVE_TAG, filters=filters)
