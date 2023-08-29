import ctypes
import json
import os
import sys
from typing import List

# pylint: disable=protected-access
IMAGE_RESOURCE_DIR = sys._MEIPASS if hasattr(sys, "_MEIPASS") else "resources"


class Config:
    DEFAULT = {
        "remote_path": os.getenv("REMOTE_PATH") if os.getenv("REMOTE_PATH") else "",
        "remote_image_db": False,
        "compress_on_import": False,
        "repair_on_import": True,
        "repair_auto_skip_on_missing": False,
        "repair_auto_fix_on_missing": False,
        "favorites": [],
    }

    def __init__(self):
        self.config = None
        self.config_file = (
            os.path.join(os.getenv("LOCAL_PATH"), "dependency_manager.cfg")
            if os.getenv("LOCAL_PATH")
            else "dependency_manager.cfg"
        )
        self.read_config()
        if self.config is None:
            self.default_config()

    def read_config(self):
        if os.path.exists(self.config_file):
            with open(self.config_file, "r", encoding="UTF-8") as read_file:
                self.config = json.load(read_file)

    def default_config(self):
        with open(self.config_file, "w", encoding="UTF-8") as write_file:
            write_file.write(json.dumps(self.DEFAULT, indent=2))
        self.config = self.DEFAULT
        if self.config["remote_path"] == "":
            input(
                "ERROR\nNo environment variables or remote path configured.\n"
                "Please edit the dependency_manager.cfg file created during the first run and restart this program."
            )

    @property
    def is_admin(self) -> bool:
        try:
            is_admin = os.getuid() == 0
        except AttributeError:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
        return is_admin

    @property
    def local_path(self) -> str:
        file_path = os.getenv("LOCAL_PATH")
        if file_path is None:
            # determine if application is a script file or frozen exe
            if getattr(sys, "frozen", False):
                file_path = os.path.dirname(os.path.realpath(sys.executable))
            elif __file__:
                file_path = os.path.dirname(os.path.realpath(__file__))
        return str(file_path)

    @property
    def remote_path(self) -> str:
        return self.config["remote_path"]

    @property
    def remote_image_db(self) -> bool:
        return self.config.get("remote_image_db", False)

    @property
    def auto_compress(self) -> bool:
        return self.config.get("compress_on_import", False)

    @property
    def auto_repair(self) -> bool:
        return self.config.get("repair_on_import", True)

    @property
    def auto_skip(self) -> bool:
        return self.config.get("repair_auto_skip_on_missing", True)

    @property
    def auto_fix(self) -> bool:
        return self.config.get("repair_auto_fix_on_missing", False)

    @property
    def favorites(self) -> List[str]:
        return self.config["favorites"]
