class OrganizeMethods:
    AUTO = "auto"
    REMOVE_UNUSED_TAG = "remove_unused"
    REMOVE_USED_TAG = "remove_used"
    ADD_UNUSED_TAG = "add_unused"
    ADD_USED_TAG = "add_used"
    TO_VERSIONED = "to_versioned"
    SUFFIX_DEP = "suffix_dep"
    ADD_REMOVE_TAG = "add_remove_tag"


class Ext:
    DEP = ".dep"
    JPG = ".jpg"
    JSON = ".json"
    PREFS = ".prefs"
    VAP = ".vap"
    VMI = ".vmi"
    VAM = ".vam"
    VAJ = ".vaj"
    VAR = ".var"
    ZIP = ".zip"
    EMPTY = ""
    PNG = ".png"
    PSD = ".psd"
    TIF = ".tif"
    CS = ".cs"
    CSLIST = ".cslist"
    DLL = ".dll"

    TYPES_ELEM = [VMI, VAM]
    TYPES_JSON = [VAP, JSON]
    TYPES_IMAGE = [JPG, PNG, TIF]
    TYPES_PLUGIN = [CS, CSLIST, DLL]

    TYPES_REPLACE = TYPES_JSON + TYPES_IMAGE + TYPES_PLUGIN


IMAGE_LIB_DIR = "_image_lib"
REPAIR_LIB_DIR = "repair_lib"
ADDON_PACKAGE_USER_PREFS_DIR = "AddonPackagesUserPrefs"
TEMP_VAR_NAME = "temp.temp.1.var"
TEMP_REPAIR_DIR = "repair"
TEMP_OPTIMIZE_DIR = "repair"
TEMP_SYNC_DIR = "sync"

BACKWARDS_COMPAT_PLUGIN_AUTHORS = ["AcidBubbles", "Hunting-Succubus", "MacGruber"]
