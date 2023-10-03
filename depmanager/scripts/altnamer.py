import os

from depmanager.common.enums.rename import RENAME_MAPPINGS

ROOT_PATH = "E:\\Downloads\\looks"

FLIP = False
items = []

for root, _, files in os.walk(ROOT_PATH):
    print(root)
    for file in files:
        if FLIP:
            if "___" in file:
                continue
            author, name, version, ext = file.split(".")
            sort_name = next(
                (renamed for original, renamed in RENAME_MAPPINGS if f"{author}.{name}.{version}" == original), None
            )
            if sort_name:
                _, sort_name, _ = sort_name.split(".")
            else:
                sort_name = name.replace("_", " ")
            items.append(sort_name.split("_")[0])
            dest = os.path.join(root, f"{sort_name}___{author}.{name}.{version}.{ext}")
            os.rename(os.path.join(root, file), dest)
        else:
            if "___" not in file:
                continue
            _, new_name = file.split("___")
            os.rename(os.path.join(root, file), os.path.join(root, new_name))

# if FLIP:
#     os.makedirs(os.path.join(root_path, "UNIQUE"), exist_ok=True)
#     duplicates = [item for item, count in collections.Counter(items).items() if count > 1]
#     if len(duplicates) > 0:
#         for root, _, files in os.walk("E:\\Downloads\\looks"):
#             for file in files:
#                 if "___" not in file and "UNIQUE" not in file:
#                     continue
#                 sort_name, _ = file.split("___")
#                 sort_name = sort_name.split("_")[0]
#                 if sort_name not in duplicates:
#                     os.rename(os.path.join(root, file), os.path.join(root, "UNIQUE", file))
