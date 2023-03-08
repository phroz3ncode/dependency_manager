import os


def test_database_auto_organize(temporary_database, test_data_temporary_dir):
    temporary_database.manipulate_file_list(temporary_database.keys, sub_directory="AUTO")

    expected_sub_directory = {
        "Blazedust.Script_ParentHoldLink.1": "assets\\plugin",
        "custom.test_scene.1": "scenes\\custom",
        "Hunting-Succubus.Enhanced_Eyes.3": "assets\\clothing",
        "Hunting-Succubus.EyeBall_Shadow.6": "assets\\clothing",
        "kemenate.Decals.5": "assets\\texture",
        "Roac.Arty.2": "assets\\hair",
        "Roac.Arty_ponytail.1": "assets\\hair",
        "Spacedog.Import_Reloaded_Lite.2": "assets\\morph",
    }

    actual_files = list(os.walk(test_data_temporary_dir))
    assert actual_files == [
        (test_data_temporary_dir, ["assets", "scenes"], []),
        (os.path.join(test_data_temporary_dir, "assets"), ["clothing", "hair", "morph", "plugin", "texture"], []),
        (
            os.path.join(test_data_temporary_dir, "assets\\clothing"),
            [],
            ["Hunting-Succubus.Enhanced_Eyes.3.var", "Hunting-Succubus.EyeBall_Shadow.6.var"],
        ),
        (os.path.join(test_data_temporary_dir, "assets\\hair"), [], ["Roac.Arty.2.var", "Roac.Arty_ponytail.1.var"]),
        (os.path.join(test_data_temporary_dir, "assets\\morph"), [], ["Spacedog.Import_Reloaded_Lite.2.var"]),
        (os.path.join(test_data_temporary_dir, "assets\\plugin"), [], ["Blazedust.Script_ParentHoldLink.1.var"]),
        (os.path.join(test_data_temporary_dir, "assets\\texture"), [], ["kemenate.Decals.5.var"]),
        (os.path.join(test_data_temporary_dir, "scenes"), ["custom"], []),
        (os.path.join(test_data_temporary_dir, "scenes\\custom"), [], ["custom.test_scene.1.var"]),
    ]
    for var_id, var in temporary_database.vars.items():
        assert not var.incorrect_subdirectory
        assert var.sub_directory == expected_sub_directory[var_id]
