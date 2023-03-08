def test_var_repair_database_setup_is_correct(temporary_repair_database, removed_vars):
    var_id = "custom.test_scene.1"
    var_object = temporary_repair_database[var_id]

    for removed_id in removed_vars:
        assert removed_id not in temporary_repair_database.vars

    assert sorted(var_object.dependencies) == sorted(
        [
            "Roac.Arty.latest",
            "kemenate.Decals.latest",
            "Spacedog.Import_Reloaded_Lite.latest",
            "Blazedust.Script_ParentHoldLink.1",
            "Hunting-Succubus.Enhanced_Eyes.latest",
            "Hunting-Succubus.EyeBall_Shadow.latest",
            "Roac.Arty_ponytail.latest",
        ]
    )
    assert var_object.used_dependencies == {
        "Roac.Arty.latest",
        "kemenate.Decals.latest",
        "Spacedog.Import_Reloaded_Lite.latest",
        "Blazedust.Script_ParentHoldLink.1",
        "Hunting-Succubus.Enhanced_Eyes.latest",
        "Hunting-Succubus.EyeBall_Shadow.latest",
        "Roac.Arty_ponytail.latest",
    }
