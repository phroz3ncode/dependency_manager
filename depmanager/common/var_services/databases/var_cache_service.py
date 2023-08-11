import json
import os

from depmanager.common.shared.enums import GIGABYTE
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.shared.tools import are_substrings_in_str
from depmanager.common.shared.tools import remove_empty_directories
from depmanager.common.var_services.databases.var_database import VarDatabase
from depmanager.common.var_services.entities.var_object import VarObject
from depmanager.common.var_services.enums import ADDON_PACKAGE_USER_PREFS_DIR
from depmanager.common.var_services.enums import TEMP_SYNC_DIR
from depmanager.common.var_services.enums import Ext
from depmanager.common.var_services.enums import OrganizeMethods
from depmanager.common.var_services.utils.var_type import VarType
from depmanager.common.var_services.var_config import VarConfig


class VarCacheService:
    def __init__(self, var_config: VarConfig):
        self.var_config = var_config
        self.remote_db_cache = None
        self.local_db_cache = None

    @property
    def remote_path(self) -> str:
        return self.var_config.remote_path

    @property
    def local_path(self) -> str:
        return self.var_config.local_path

    @property
    def remote_db(self) -> VarDatabase:
        if self.remote_db_cache is None:
            if self.var_config.remote_image_db:
                self.remote_db_cache = VarDatabase(self.remote_path, image_root=self.remote_path)
            else:
                self.remote_db_cache = VarDatabase(self.remote_path, image_root=self.local_path)
        return self.remote_db_cache

    @property
    def local_db(self) -> VarDatabase:
        if self.local_db_cache is None:
            self.local_db_cache = VarDatabase(self.local_path, disable_save=True, quick_scan=True)
        return self.local_db_cache

    def clear(self):
        self.remote_db_cache = None
        self.local_db_cache = None

    @property
    def invalid_local(self):
        return self.remote_path == self.local_path

    @property
    def remote_duplicates(self):
        return self.remote_db.find_unversioned_duplicates()

    @property
    def remote_missing(self):
        return self.remote_db.find_missing_vars()

    @property
    def local_required(self) -> set[str]:
        required_vars = self.local_db.unique_required_dependencies
        required_vars.update(self.local_db.get_var_ids_from_deps())
        # Check for a "sync" folder and if images in it, sync them as vars
        required_vars.update(self.local_sync_image_deps())
        return required_vars

    def local_sync_image_deps(self) -> set[str]:
        deps = set()
        local_sync_path = os.path.join(self.local_path, TEMP_SYNC_DIR)
        if not os.path.exists(local_sync_path):
            return deps

        for (_, _, files) in os.walk(os.path.join(self.local_path, TEMP_SYNC_DIR)):
            for file in files:
                deps.add(file.replace(Ext.JPG, Ext.EMPTY))
        return deps

    @property
    def all_local_required(self):
        """This logic replaces the old dependency loop logic. We assume that if the remote
        database knows the var then it should also know all of the actual used_dependencies.
        """
        all_required = set()
        for var in self.local_required:
            all_required.add(var)
            # If the dependency is known to the remote_db, we should make sure we have all real dependencies
            # If it is unknown we will defer what is needed to the local dependencies, which may be right
            # or wrong.
            var_name = self.remote_db.get_var_name(var, always=True)
            additional_required = self.remote_db.required_dependencies.get(var_name, set())
            all_required.update(additional_required)

        # If we have specific versions listed, we only want to copy a single version unless we actually
        # need multiple versions
        all_required = self.remote_db.dedupe_dependency_list(all_required)
        return all_required

    def get_remote_repairable(self, filters=None):
        return self._get_repairable(self.remote_db, filters)

    def get_local_repairable(self, filters=None, include_clothing=False):
        return self._get_repairable(self.local_db, filters, include_clothing)

    def _get_repairable(self, database, filters=None, include_clothing=False):
        var_list = []
        for var_id, var in database.vars.items():
            can_include = var.var_type.is_repairable
            if include_clothing:
                can_include = var.var_type.is_repairable or var.var_type.type in (
                    VarType.CLOTHING,
                    VarType.TEXTURE,
                )
            if not can_include:
                continue
            if filters is not None and not are_substrings_in_str(var.sub_directory, filters):
                continue
            var_list.append(var_id)
        return sorted(set(var_list))

    @property
    def local_missing(self) -> set[str]:
        missing = set()
        for var in self.all_local_required:
            if self.local_db.get_var_name(var) is None:
                missing.add(var)
        return missing

    def get_remote_present_and_missing_ids(self):
        remote_present_ids = set()
        remote_missing_ids = set()
        for var in self.local_missing:
            # See if the remote_db is aware of the missing var
            var_name = self.remote_db.get_var_name(var)
            if var_name is not None:
                # No longer add dependencies from remote here, this is now
                # done as part of the local_missing call when the
                # all_local_required is constructed.
                remote_present_ids.add(var_name)
            else:
                remote_missing_ids.add(var)

        remote_present_ids = remote_present_ids - set(self.local_db.keys)
        return remote_present_ids, remote_missing_ids

    def filter_remote_var_ids_to_remove_favorites(self, var_id_list) -> set[str]:
        favorites = self.var_config.favorites
        filtered = set()
        for var_id in var_id_list:
            var_data = self.remote_db[var_id]
            if "assets" in var_data.sub_directory:
                if not are_substrings_in_str(var_data.author, favorites.get("assets", [])):
                    filtered.add(var_id)
            elif "look" in var_data.sub_directory:
                if not are_substrings_in_str(var_data.author, favorites.get("look", [])):
                    filtered.add(var_id)
            elif "scene" in var_data.sub_directory:
                if not are_substrings_in_str(var_data.author, favorites.get("scene", [])):
                    filtered.add(var_id)
            else:
                filtered.add(var_id)
        return filtered

    def get_remote_unused(self, filters=None):
        unused_vars = self.remote_db.find_unused_vars(filters=filters)
        return self.filter_remote_var_ids_to_remove_favorites(unused_vars)

    def get_remote_used(self, filters=None):
        return self.remote_db.find_unused_vars(filters=filters, invert=True)

    def get_removed_unused(self, filters=None):
        return self.remote_db.find_removed_unused_vars(filters=filters)

    def get_suffix_dep(self, filename):
        with open(os.path.join(self.local_path, filename), "r", encoding="UTF-8") as read_file:
            return {line.rstrip().replace(Ext.VAR, Ext.EMPTY) for line in read_file}

    def organize_remote_files(self, mode, filters=None, remove_empty=True):
        if mode == OrganizeMethods.AUTO:
            self.remote_db.manipulate_file_list(self.remote_db.keys, sub_directory="AUTO")
        elif mode == OrganizeMethods.ADD_UNUSED_TAG:
            var_list = self.get_remote_unused(filters)
            self.remote_db.manipulate_file_list(var_list, "unused_", append=True)
        elif mode == OrganizeMethods.REMOVE_UNUSED_TAG:
            var_list = self.get_remote_unused(filters)
            self.remote_db.manipulate_file_list(var_list, "unused_", remove=True)
        elif mode == OrganizeMethods.ADD_USED_TAG:
            var_list = self.get_remote_used(filters)
            self.remote_db.manipulate_file_list(var_list, "used_", append=True)
        elif mode == OrganizeMethods.REMOVE_USED_TAG:
            var_list = self.get_remote_used(filters)
            self.remote_db.manipulate_file_list(var_list, "used_", remove=True)
        elif mode == OrganizeMethods.ADD_REMOVE_TAG:
            var_list = self.get_removed_unused(filters)
            self.remote_db.manipulate_file_list(var_list, "removed")
        elif mode == OrganizeMethods.TO_VERSIONED:
            self.remote_db.manipulate_file_list(self.remote_duplicates, "_versioned")
        elif mode == OrganizeMethods.SUFFIX_DEP:
            var_list = self.get_suffix_dep(filters)
            self.remote_db.manipulate_file_list(var_list, filters.replace(Ext.DEP, Ext.EMPTY), suffix=True)

        if remove_empty:
            remove_empty_directories(self.remote_db.rootpath)

    def auto_organize_remote_files(self):
        print("Auto organizing remote vars...")
        self.organize_remote_files(mode=OrganizeMethods.AUTO, remove_empty=False)
        self.organize_remote_files(mode=OrganizeMethods.TO_VERSIONED, remove_empty=False)
        self.organize_remote_files(mode=OrganizeMethods.ADD_UNUSED_TAG, filters=["_versioned"], remove_empty=False)
        remove_empty_directories(self.remote_db.rootpath)

    def auto_check_remote_files_health(self):
        print("Checking health of remote files")
        size = sum(var_data.info["size"] for _, var_data in self.remote_db.vars.items())
        missing = self.remote_missing
        duplicates = self.remote_duplicates
        unused_versioned = self.get_remote_unused(["_versioned"])
        unoptimized_vars = self.remote_db.find_unoptimized_vars()
        broken_vars = self.remote_db.find_broken_vars(health_check=True)
        print("\nResults:")
        print(f"Remote size: {len(self.remote_db)} vars - {round(size / GIGABYTE, 2)} GB")
        self.remote_db.display_var_list(missing, "Missing", show_used_by=True)
        self.remote_db.display_var_list(duplicates, "Unversioned duplicate")
        self.remote_db.display_var_list(unused_versioned, "Unused version")
        self.remote_db.display_var_list(unoptimized_vars, "Unoptimized dependencies")
        self.remote_db.display_var_list(broken_vars, "Broken")

    def auto_check_local_files_health(self):
        print("Checking health of local files")
        missing = self.local_missing
        print("\nResults:")
        self.local_db.display_var_list(missing, "Missing", show_used_by=True)

    def auto_organize_local_files_to_remote(self, filters=None):
        if self.invalid_local:
            print("WARNING: Remote and local path are the same. Cannot update local missing.")
            return

        self.clear()
        self.remote_db.refresh()
        new_var_ids = self.local_db.keys - self.remote_db.keys

        if filters is not None:
            filters = [f.strip() for f in filters]
            new_var_ids = {v for v in new_var_ids if any(f for f in filters if f in self.local_db[v].sub_directory)}

        if len(new_var_ids) == 0:
            print("No local vars missing from remote...")
            return

        local_var_ids = []
        for var_id in sorted(new_var_ids):
            print(f"PROCESSING {var_id}...")
            var_ref = self.local_db[var_id]
            if self.var_config.auto_repair:
                remove_confirm = not self.var_config.auto_fix
                remove_skip = self.var_config.auto_skip
                repaired = self.remote_db.repair_broken_var(
                    var_ref, remove_confirm=remove_confirm, remove_skip=remove_skip
                )
                # If the repair failed or was cancelled, don't attempt to import the var
                if not repaired:
                    continue
                self.remote_db.repair_metadata(var_ref)
            if self.var_config.auto_compress and var_ref.is_compressible:
                var_ref.compress()
            local_var_ids.append(var_id)

        if len(local_var_ids) == 0:
            print("No local vars to copy to remote...")
            return

        progress = ProgressBar(len(local_var_ids), description="Copying local to remote")
        for var_id in local_var_ids:
            progress.inc()
            var = self.local_db[var_id]
            self.local_db.manipulate_file(
                var.var_id,
                os.path.join(self.remote_db.rootpath, var.sub_directory),
                move=False,
            )
            self.remote_db.add_file(os.path.join(self.remote_db.rootpath, var.sub_directory, var.filename))
        self.auto_organize_remote_files()
        self.remote_db.save()
        self.remote_db.refresh()

    def fix_local_missing(self):
        if self.invalid_local:
            print("WARNING: Remote and local path are the same. Cannot update local missing.")
            return
        if not self.var_config.is_admin:
            print("WARNING: Files will be copied instead of symlinked. Run as admin to enable symlinks.")

        self.clear()
        remote_present_ids, _ = self.get_remote_present_and_missing_ids()
        if len(remote_present_ids) == 0:
            print("No remote vars to move...")

        if len(remote_present_ids) > 0:
            progress = ProgressBar(len(remote_present_ids), "Copying remote to local")
            os.makedirs(os.path.join(self.local_db.rootpath, "dependencies"), exist_ok=True)
            for var_id in remote_present_ids:
                progress.inc()
                var = self.remote_db[var_id]
                self.remote_db.manipulate_file(
                    var.var_id,
                    os.path.join(self.local_db.rootpath, "dependencies", var.sub_directory),
                    move=False,
                    symlink=self.var_config.is_admin,
                )
        self.enable_local_plugins()

        # if len(remote_missing_ids) > 0:
        #     self.local_db.display_var_list(remote_missing_ids, "Missing", show_used_by=True)

    def enable_local_plugins(self):
        self.local_db_cache = None
        template = {"pluginsAlwaysEnabled": "true", "pluginsAlwaysDisabled": "false"}
        pref_path = os.path.join(
            os.path.abspath(os.path.join(self.local_db.rootpath, "..")),
            ADDON_PACKAGE_USER_PREFS_DIR,
        )
        if not os.path.exists(pref_path):
            return
        for var_id, var in self.local_db.vars.items():
            if var.var_type.contains_type(VarType.PLUGIN):
                file_path = os.path.join(pref_path, f"{var_id}{Ext.PREFS}")
                with open(file_path, "w", encoding="UTF-8") as write_file:
                    json.dump(template, write_file, indent=4)

    def compress_local(self, filters=None):
        total_saved = 0
        for var_id in self.get_local_repairable(filters, include_clothing=True):
            var = self.local_db[var_id]
            saved = var.compress()
            if saved != 0:
                var = VarObject(root_path=self.local_db.rootpath, file_path=var.file_path)
                self.local_db[var.var_id] = var
                total_saved += saved
        print(f"Total space compressed: {total_saved}")
