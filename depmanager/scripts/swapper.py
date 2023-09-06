# import json
# import os
# from os import path
#
# from orjson import orjson
#
# from depmanager.common.var_services.databases.var_database import VarDatabase
# from depmanager.common.var_services.enums import Ext
# from depmanager.common.var_services.utils.var_parser import VarParser
# from depmanager.common.var_services.var_config import Config
#
# used_packages = set()
# remote_db = VarDatabase(Config().remote_path)
# local_path = path.join(Config().local_path, "../common/var_services", "Custom", "Atom", "Person", "Appearance")
# local_path_rebuilds = path.join(
#     Config().local_path, "../common/var_services", "Custom", "Atom", "Person", "Appearance_Rebuilds"
# )
# for (root, _, files) in os.walk(local_path):
#     for file in files:
#         if Ext.VAP in file:
#             vap_path = path.join(root, file)
#             with open(vap_path, "r", encoding="UTF-8") as read_item:
#                 vap_content = read_item.readlines()
#                 packages = VarParser.scan_with_paths(vap_content)
#                 used_files = set(list(packages.get("SELF", [])) + list(packages.get("SELF_UNREF", [])))
#
#                 replacement_mappings = {}
#                 for check_package_file in used_files:
#                     found_id, found_path = remote_db.find_replacement_from_repair_index(
#                         check_package_file, exact_only=True
#                     )
#                     if found_id is None:
#                         continue
#                     print(f"{check_package_file} -> {found_id}:/{found_path}")
#                     replacement_mappings[check_package_file] = f"{found_id}:/{found_path}"
#                     used_packages.add(found_id)
#
#                 fixed_content = VarParser.replace(vap_content, replacement_mappings)
#                 json_data = json.loads("".join(fixed_content))
#                 write_data = orjson.dumps(json_data, option=orjson.OPT_INDENT_2).decode("UTF-8")
#
#                 write_dir = path.join(local_path_rebuilds, path.relpath(root, local_path))
#                 os.makedirs(write_dir, exist_ok=True)
#
#                 with open(path.join(write_dir, file), "w", encoding="UTF-8") as write_file:
#                     write_file.write(write_data)
# print(used_packages)
