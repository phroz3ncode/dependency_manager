from depmanager.common.shared.console_menu_item import ConsoleMenuItem
from depmanager.common.shared.enums import DIVIDER

DEBUG_MODE = True


class ConsoleMenu:
    def __init__(self, local_path, remote_path, menu_name=None, menu_version=None):
        self.remote_path = remote_path
        self.local_path = local_path
        self.action = None
        self.menu_name = menu_name if menu_name is not None else "Console Menu"
        self.menu_version = menu_version if menu_version is not None else 1
        self.menu_info = None

    def menu_main(self):
        raise NotImplementedError("should be implemented in descendents")

    def run(self):
        print(f"{self.menu_name} v{self.menu_version}")
        print(f"{DIVIDER}Local: {self.local_path}\nRemote:{self.remote_path}")
        action = self.menu_main()
        while action is not None:
            if isinstance(action, ConsoleMenuItem):
                action = action.build()
            if action[0] == "menu":
                action = self.run_menu(action)
            else:
                action = self.run_function(action)

    def run_menu(self, action):
        print(f"{DIVIDER}")
        if self.menu_info is not None:
            print(f"{self.menu_info}")
        print("Select choice:")
        menu = action[1]
        for index, menu_item in enumerate(menu):
            print(f"{index + 1}. {menu_item[0]}")
        print("0. Exit")
        try:
            choice = int(input("# "))
        except ValueError:
            choice = -1
        print("")
        if choice == 0:
            return None
        if 0 < choice <= len(menu):
            if isinstance(menu[choice - 1][1], list):
                return menu[choice - 1][1]
            return menu[choice - 1]
        return self.menu_main()

    def run_function(self, action):
        kwargs = {} if len(action) < 3 else action[2]
        func = action[1]
        try:
            response = func(**kwargs)
            if response is None:
                return self.menu_main()
            return response
        # pylint: disable=broad-except
        except Exception as exception:
            if not DEBUG_MODE:
                print(f"EXCEPTION OCCURRED: {exception}")
                return self.menu_main()
            raise exception
