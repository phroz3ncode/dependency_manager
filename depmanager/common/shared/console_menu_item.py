class ConsoleMenuItem:
    def __init__(self, desc, action, action_args=None) -> None:
        self.desc = desc
        self.action = action
        self.action_args = action_args

    def build(self):
        if self.desc == "menu":
            menu_items = [x.build() for x in self.action]
            return ["menu", menu_items, None]

        return [
            self.desc,
            self.action,
            self.action_args if self.action_args is not None else {},
        ]
