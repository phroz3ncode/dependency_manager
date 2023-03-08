def test_var_object_original_file_path(test_var_object):
    assert test_var_object.original_file_path == "test_data\\fixtures_database\\custom.test_scene.1.var"


def test_var_object_file_path(test_var_object):
    assert test_var_object.file_path == "test_data\\fixtures_database\\custom.test_scene.1.var"


def test_var_object_directory(test_var_object):
    assert test_var_object.directory == "test_data\\fixtures_database"


def test_var_object_relative_path(test_var_object):
    assert test_var_object.relative_path == "custom.test_scene.1.var"


def test_var_object_root_path(test_var_object):
    assert test_var_object.root_path == "test_data\\fixtures_database"


def test_var_object_filename(test_var_object):
    assert test_var_object.filename == "custom.test_scene.1.var"


def test_var_object_author(test_var_object):
    assert test_var_object.author == "custom"


def test_var_object_name(test_var_object):
    assert test_var_object.package_name == "test_scene"


def test_var_object_clean_name(test_var_object):
    assert test_var_object.clean_name == "custom.test_scene.1"


def test_var_object_id(test_var_object):
    assert test_var_object.var_id == "custom.test_scene.1"


def test_var_object_id_as_latest(test_var_object):
    assert test_var_object.id_as_latest == "custom.test_scene.latest"


def test_var_object_duplicate_id(test_var_object):
    assert test_var_object.duplicate_id == "custom.test_scene"


def test_var_object_sub_directory(test_var_object):
    assert test_var_object.sub_directory == ""


def test_var_object_preferred_subdirectory(test_var_object):
    assert test_var_object.preferred_subdirectory == "scenes\\custom"


def test_var_object_contains(test_var_object):
    assert test_var_object.contains == {
        "asset": False,
        "clothing": False,
        "hair": False,
        "morph": False,
        "texture": False,
        "preset": False,
        "plugin": False,
        "scene": True,
        "appearance": False,
        "sound": False,
        "pose": False,
    }


def test_var_object_dependencies(test_var_object):
    assert sorted(test_var_object.dependencies) == sorted(
        [
            "Roac.Arty_ponytail.latest",
            "Hunting-Succubus.Enhanced_Eyes.latest",
            "Spacedog.Import_Reloaded_Lite.latest",
            "Hunting-Succubus.EyeBall_Shadow.latest",
            "kemenate.Decals.latest",
            "Blazedust.Script_ParentHoldLink.1",
            "Roac.Arty.latest",
        ]
    )


def test_var_object_exists(test_var_object):
    assert test_var_object.exists


def test_var_object_includes_as_list(test_var_object):
    assert test_var_object.includes_as_list == [
        ("custom.test_scene.1", "Saves/scene/test_scene.jpg", "test_scene.jpg"),
        ("custom.test_scene.1", "Saves/scene/test_scene.json", "test_scene.json"),
    ]


def test_var_object_info(test_var_object):
    assert test_var_object.info["modified"] == 1676300602.5992532
    assert test_var_object.info["size"] == 19409


def test_var_object_is_custom(test_var_object):
    assert test_var_object.is_custom


def test_var_object_is_vamx(test_var_object):
    assert not test_var_object.is_vamx


def test_var_object_namelist(test_var_object):
    assert test_var_object.namelist == ["meta.json", "Saves/scene/test_scene.jpg", "Saves/scene/test_scene.json"]


def test_var_object_type(test_var_object):
    assert test_var_object.var_type.type == "scene"
