import ctypes
import json
import os
import sys

# pylint: disable=protected-access
IMAGE_RESOURCE_DIR = sys._MEIPASS if hasattr(sys, "_MEIPASS") else "resources"


class VarConfig:
    @property
    def local(self):
        if os.path.exists("dependency_manager.cfg"):
            with open("dependency_manager.cfg", "r", encoding="UTF-8") as read_file:
                return json.load(read_file)
        else:
            with open("dependency_manager.cfg", "w", encoding="UTF-8") as write_file:
                write_file.write(json.dumps({"REMOTE_PATH": ""}, indent=2))
            return {}

    @property
    def local_path(self):
        file_path = os.getenv("LOCAL_PATH")
        if file_path is None:
            # determine if application is a script file or frozen exe
            if getattr(sys, "frozen", False):
                file_path = os.path.dirname(os.path.realpath(sys.executable))
            elif __file__:
                file_path = os.path.dirname(os.path.realpath(__file__))
        return file_path

    @property
    def remote_var_path(self):
        file_path = os.getenv("REMOTE_PATH")
        if file_path is None:
            file_path = self.local.get("REMOTE_PATH")
        return file_path

    @property
    def is_admin(self):
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        return is_admin

    @property
    def auto_compress(self):
        return False
