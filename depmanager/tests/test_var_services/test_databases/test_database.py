def test_db_initialized(mock_var_database):
    assert len(mock_var_database.vars) == 8


def test_db_directory_listing_and_count(mock_var_database):
    assert mock_var_database.directory_count == 8
    assert mock_var_database.directory_listing == {
        "test_data\\fixtures_database": [
            "Blazedust.Script_ParentHoldLink.1.var",
            "custom.test_scene.1.var",
            "Hunting-Succubus.Enhanced_Eyes.3.var",
            "Hunting-Succubus.EyeBall_Shadow.6.var",
            "kemenate.Decals.5.var",
            "Roac.Arty.2.var",
            "Roac.Arty_ponytail.1.var",
            "Spacedog.Import_Reloaded_Lite.2.var",
        ]
    }


def test_db_vars_required(mock_var_database):
    assert mock_var_database.vars_required == {
        "Blazedust.Script_ParentHoldLink.1": ["custom.test_scene.1"],
        "kemenate.Decals.5": ["custom.test_scene.1"],
        "Spacedog.Import_Reloaded_Lite.2": ["custom.test_scene.1"],
        "Roac.Arty_ponytail.1": ["custom.test_scene.1"],
        "Hunting-Succubus.Enhanced_Eyes.3": ["custom.test_scene.1"],
        "Roac.Arty.2": ["custom.test_scene.1"],
        "Hunting-Succubus.EyeBall_Shadow.6": ["custom.test_scene.1"],
    }


def test_vars_versions(mock_var_database):
    assert mock_var_database.vars_versions == {
        "Blazedust.Script_ParentHoldLink": {1},
        "custom.test_scene": {1},
        "Hunting-Succubus.Enhanced_Eyes": {3},
        "Hunting-Succubus.EyeBall_Shadow": {6},
        "kemenate.Decals": {5},
        "Roac.Arty": {2},
        "Roac.Arty_ponytail": {1},
        "Spacedog.Import_Reloaded_Lite": {2},
    }
