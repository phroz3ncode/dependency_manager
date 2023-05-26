from depmanager.common.var_services.var_config import VarConfig
from depmanager.common.var_services.var_menu.var_console_menu import VarConsoleMenu

if __name__ == "__main__":
    var_config = VarConfig()
    var_menu = VarConsoleMenu(var_config)
    var_menu.run()
