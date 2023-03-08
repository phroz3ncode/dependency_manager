from depmanager.common.shared.console_menu import ConsoleMenu
from depmanager.common.var_services.databases.var_cache_service import VarCacheService
from depmanager.common.var_services.var_menu.menu_main import MenuMain
from depmanager.common.version_var import VAR


class VarConsoleMenu(ConsoleMenu):
    def __init__(self, local_path, remote_path, is_admin=False):
        super().__init__(local_path, remote_path, "VAR Manager", VAR)
        self.cache = VarCacheService(local_path, remote_path)
        self.is_admin = is_admin
        if not self.is_admin:
            print("WARNING: Symlinks can only be used when run as admin.")

    def menu_main(self):
        return MenuMain(self.cache, self.is_admin).menu()
