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
    ASSETBUNDLE = ".assetbundle"

    TYPES_ELEM = [VMI, VAM]
    TYPES_JSON = [VAP, JSON]
    TYPES_IMAGE = [JPG, PNG, TIF]
    TYPES_PLUGIN = [CS, CSLIST, DLL]

    TYPES_REPLACE = TYPES_JSON + TYPES_IMAGE + TYPES_PLUGIN
