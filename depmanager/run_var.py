from depmanager.common.var_services.var_config import VarConfig
from depmanager.common.var_services.var_menu.var_console_menu import VarConsoleMenu

if __name__ == "__main__":
    config = VarConfig()
    if config.remote_var_path is None:
        input(
            "ERROR\nNo environment variables or remote path configured.\n"
            "Please edit the dependency_manager.cfg file created during the first run."
        )
    else:
        var_menu = VarConsoleMenu(config.local_path, config.remote_var_path, config.is_admin)
        var_menu.run()
