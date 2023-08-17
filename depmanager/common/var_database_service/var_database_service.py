import os

from depmanager.common.enums.config import Config
from depmanager.common.shared.progress_bar import ProgressBar
from depmanager.common.var_database_service.database_service import DatabaseService


class VarDatabaseService:
    def __init__(self, var_config: Config):
        self.var_config = var_config
        self.local = DatabaseService(root=self.var_config.local_path, quick_scan=True)
        self.remote = DatabaseService(root=self.var_config.remote_path, image_root=self.var_config.local_path)

    def clear(self):
        self.local.clear()
        self.remote.clear()

    @property
    def invalid_local(self):
        return self.var_config.remote_path == self.var_config.local_path

    def local_missing(self) -> set[str]:
        """This logic replaces the old dependency loop logic. We assume that if the remote
        database knows the var then it should also know all of the actual used_dependencies.
        """
        all_required = set()
        for var in self.local.required_vars:
            all_required.add(var)
            # If the dependency is known to the remote_db, we should make sure we have all real dependencies
            # If it is unknown we will defer what is needed to the local dependencies, which may be right
            # or wrong.
            var_name = self.remote.db.get_var_name(var, always=True)
            additional_required = self.remote.db.required_dependencies.get(var_name, set())
            all_required.update(additional_required)

        # If we have specific versions listed, we only want to copy a single version unless we actually
        # need multiple versions
        all_required = self.remote.db.dedupe_dependency_list(all_required)

        missing = set()
        for var in all_required:
            if self.local.db.get_var_name(var) is None:
                missing.add(var)
        return missing

    def get_remote_present_and_missing_ids(self):
        remote_present_ids = set()
        remote_missing_ids = set()
        for var in self.local_missing():
            # See if the remote_db is aware of the missing var
            var_name = self.remote.db.get_var_name(var)
            if var_name is not None:
                # No longer add dependencies from remote here, this is now
                # done as part of the local_missing call when the
                # all_local_required is constructed.
                remote_present_ids.add(var_name)
            else:
                remote_missing_ids.add(var)

        remote_present_ids = remote_present_ids - set(self.local.db.keys)
        return remote_present_ids, remote_missing_ids

    def fix_local_missing(self):
        if self.invalid_local:
            print("WARNING: Remote and local path are the same. Cannot update local missing.")
            return
        if not self.var_config.is_admin:
            print("WARNING: Files will be copied instead of symlinked. Run as admin to enable symlinks.")

        self.remote.refresh()
        self.local.clear()
        remote_present_ids, _ = self.get_remote_present_and_missing_ids()
        if len(remote_present_ids) == 0:
            print("No remote vars to move...")

        if len(remote_present_ids) > 0:
            progress = ProgressBar(len(remote_present_ids), "Copying remote to local")
            os.makedirs(os.path.join(self.local.db.rootpath, "dependencies"), exist_ok=True)
            for var_id in remote_present_ids:
                progress.inc()
                var = self.remote.db[var_id]
                self.remote.db.manipulate_file(
                    var.var_id,
                    os.path.join(self.local.db.rootpath, "dependencies", var.sub_directory),
                    move=False,
                    symlink=self.var_config.is_admin,
                    track_move=False,
                )
        self.local.clear()
        self.local.enable_plugins()
        self.local.check_health()

    def auto_organize_local_files_to_remote(self, filters=None):
        if self.invalid_local:
            print("WARNING: Remote and local path are the same. Cannot update local missing.")
            return

        self.remote.db.refresh()
        self.local.clear()
        new_var_ids = self.local.db.keys - self.remote.db.keys

        if filters is not None:
            filters = [f.strip() for f in filters]
            new_var_ids = {v for v in new_var_ids if any(f for f in filters if f in self.local.db[v].sub_directory)}

        if len(new_var_ids) == 0:
            print("No local vars missing from remote...")
            return

        local_var_ids = []
        for var_id in sorted(new_var_ids):
            print(f"PROCESSING {var_id}...")
            var_ref = self.local.db[var_id]
            if self.var_config.auto_repair:
                remove_confirm = not self.var_config.auto_fix
                remove_skip = self.var_config.auto_skip
                repaired = self.remote.db.repair_broken_var(
                    var_ref, remove_confirm=remove_confirm, remove_skip=remove_skip
                )
                # If the repair failed or was cancelled, don't attempt to import the var
                if not repaired:
                    continue
                self.remote.db.repair_metadata(var_ref)
            if self.var_config.auto_compress and var_ref.is_compressible:
                var_ref.compress()
            local_var_ids.append(var_id)

        if len(local_var_ids) == 0:
            print("No local vars to copy to remote...")
            return

        progress = ProgressBar(len(local_var_ids), description="Copying local to remote")
        for var_id in local_var_ids:
            progress.inc()
            var = self.local.db[var_id]
            self.local.db.manipulate_file(
                var.var_id,
                os.path.join(self.remote.db.rootpath, var.sub_directory),
                move=False,
            )
            self.remote.db.add_file(os.path.join(self.remote.db.rootpath, var.sub_directory, var.filename))
        self.remote.auto_organize()
