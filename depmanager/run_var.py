from depmanager.common.enums.config import Config
from depmanager.common.menu_service.var_console_menu import VarConsoleMenu

if __name__ == "__main__":
    var_config = Config()
    var_menu = VarConsoleMenu(var_config)
    var_menu.run()
