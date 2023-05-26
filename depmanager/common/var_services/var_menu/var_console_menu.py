from depmanager.common.shared.console_menu import ConsoleMenu
from depmanager.common.var_services.databases.var_cache_service import VarCacheService
from depmanager.common.var_services.var_config import VarConfig
from depmanager.common.var_services.var_menu.menu_main import MenuMain
from depmanager.version_var import VAR


class VarConsoleMenu(ConsoleMenu):
    def __init__(self, var_config: VarConfig):
        super().__init__(var_config.local_path, var_config.remote_path, "VAR Manager", VAR)
        self.var_config = var_config
        self.cache = VarCacheService(self.var_config)
        if not self.var_config.is_admin:
            print("WARNING: Symlinks can only be used when run as admin.")

    def menu_main(self):
        return MenuMain(self.cache).menu()
