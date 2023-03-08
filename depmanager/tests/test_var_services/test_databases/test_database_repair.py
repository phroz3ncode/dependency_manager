def test_db_repair_index_builds(mock_var_database):
    repair_index = mock_var_database.repair_index
    assert len(repair_index) == 934


def test_db_required_dependencies_builds(mock_var_database):
    required_dependencies = mock_var_database.required_dependencies
    for var in mock_var_database.vars:
        assert var in required_dependencies
        if var != "custom.test_scene.1":
            assert required_dependencies[var] == set()
        else:
            assert required_dependencies[var] == {
                "Blazedust.Script_ParentHoldLink.1",
                "Hunting-Succubus.Enhanced_Eyes.latest",
                "Spacedog.Import_Reloaded_Lite.latest",
                "Roac.Arty_ponytail.latest",
                "Roac.Arty.latest",
                "kemenate.Decals.latest",
                "Hunting-Succubus.EyeBall_Shadow.latest",
            }
