from collections import defaultdict

from depmanager.common.enums.ext import Ext
from depmanager.common.enums.methods import OrganizeMethods
from depmanager.common.enums.paths import TEMP_REPAIR_DIR
from depmanager.common.enums.variables import MEGABYTE
from depmanager.common.menu_service.base_actions_menu import BaseActionsMenu
from depmanager.common.shared.console_menu_item import ConsoleMenuItem


class MenuMaintenance(BaseActionsMenu):
    def menu(self) -> ConsoleMenuItem:
        return ConsoleMenuItem(
            "menu",
            [
                ConsoleMenuItem("REPAIR remote vars", self.repair_and_optimize),
                ConsoleMenuItem("TAG unused vars", self.add_unused_var_tags),
                ConsoleMenuItem("UNTAG unused vars", self.remove_unused_var_tags),
                ConsoleMenuItem("TAG used vars", self.add_used_var_tags),
                ConsoleMenuItem("UNTAG used vars", self.remove_used_var_tags),
                ConsoleMenuItem("CREATE *.dep from local image_lib", self.build_dep_from_image_lib),
                ConsoleMenuItem("FIND what uses var", self.search_that_use),
                ConsoleMenuItem("FIND low value vars", self.search_low_value),
            ],
        )

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

    def repair_duplication(self):
        # filters = self.get_var_filters()

        self.cache.remote.refresh()

        var_to_process = set()
        var_to_process.update(self.cache.remote.db.find_duplication_in_vars())

    def add_unused_var_tags(self):
        filters = self.get_var_filters()
        self.cache.remote.organize_files(mode=OrganizeMethods.ADD_UNUSED_TAG, filters=filters)

    def remove_unused_var_tags(self):
        filters = self.get_var_filters()
        self.cache.remote.organize_files(mode=OrganizeMethods.REMOVE_UNUSED_TAG, filters=filters)

    def add_used_var_tags(self):
        filters = self.get_var_filters()
        self.cache.remote.organize_files(mode=OrganizeMethods.ADD_USED_TAG, filters=filters)

    def remove_used_var_tags(self):
        filters = self.get_var_filters()
        self.cache.remote.organize_files(mode=OrganizeMethods.REMOVE_USED_TAG, filters=filters)

    def build_dep_from_image_lib(self):
        self.cache.remote.db.save_image_db_as_dep()

    def search_that_use(self):
        var_name = input("Name: ").strip()
        # noinspection PyTypeChecker
        required_by = self.cache.remote.db.vars_required.get(var_name)
        if required_by is None or len(required_by) == 0:
            print("Not used as a dependency by any vars.")
        else:
            print("Used by:")
            for var in required_by:
                print(var)

    def search_low_value(self):
        self.cache.clear()
        required_by = self.cache.remote.db.vars_required
        low_value = []
        for var_id, var_reqs in required_by.items():
            if len(var_reqs) == 1:
                var_item = self.cache.remote.db[str(var_id)]
                if var_item.info["size"] > 100 * MEGABYTE:
                    low_value.append((var_item.info["size"] / MEGABYTE, var_id, var_reqs))
        for var_id in sorted(low_value, reverse=True):
            print(var_id)

    def search_texture(self):
        self.cache.clear()
        files = defaultdict(list)
        files_used_by = defaultdict(list)
        for var_id, var in self.cache.remote.db.vars.items():
            for item, size in var.infolist:
                if Ext.JPG in item or Ext.PNG in item or Ext.TIF in item or Ext.ASSETBUNDLE in item:
                    files[item].append(size)
                    files_used_by[item].append(var_id)

        duplicates = [(sum(f_uses[1:]) / MEGABYTE, len(f_uses), f) for f, f_uses in files.items() if len(f_uses) > 1]
        duplicates = sorted(duplicates, reverse=True)
        total_duplication = sum(d[0] for d in duplicates)
        print(f"Total duplication: {total_duplication} MB")
        for idx, val in enumerate(duplicates):
            if idx < 100:
                print(val)
            else:
                break
