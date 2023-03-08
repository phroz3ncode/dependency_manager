import io
from os import path

import pytest

from depmanager.common.var_services.enums import Ext
from depmanager.common.var_services.utils.var_parser import VarParser


def test_scan(test_data_fixture_dir):
    with io.TextIOWrapper(
        open(path.join(test_data_fixture_dir, "test_scene.json"), "rb"), encoding="UTF-8"
    ) as read_item:
        packages = VarParser.scan(read_item.readlines())

    assert packages == {
        "Blazedust.Script_ParentHoldLink.1",
        "Roac.Arty.latest",
        "Hunting-Succubus.Enhanced_Eyes.latest",
        "Roac.Arty_ponytail.latest",
        "Spacedog.Import_Reloaded_Lite.latest",
        "kemenate.Decals.latest",
        "Hunting-Succubus.EyeBall_Shadow.latest",
    }


def test_scan_with_paths(test_data_fixture_dir):
    with io.TextIOWrapper(
        open(path.join(test_data_fixture_dir, "test_scene.json"), "rb"), encoding="UTF-8"
    ) as read_item:
        packages = VarParser.scan_with_paths(read_item.readlines())

    assert packages == {
        "Blazedust.Script_ParentHoldLink.1": {"Custom/Scripts/Blazedust/ParentHoldLink.cs"},
        "Hunting-Succubus.EyeBall_Shadow.latest": {
            "Custom/Clothing/Female/HUNTING-SUCCUBUS/EyeBall Shadow/EyeBall Shadow.vam"
        },
        "Hunting-Succubus.Enhanced_Eyes.latest": {
            "Custom/Clothing/Female/HUNTING-SUCCUBUS/Enhanced_Eyes/Enhanced Eyes Realastic.vam"
        },
        "Roac.Arty.latest": {"Custom/Hair/Female/Roac/Roac Arty wisps.vam"},
        "Roac.Arty_ponytail.latest": {
            "Custom/Hair/Female/Roac/ROAC/Roac Arty pony.vam",
            "Custom/Hair/Female/Roac/ROAC/Roac Arty ponytail tuck.vam",
        },
        "Spacedog.Import_Reloaded_Lite.latest": {"Custom/Atom/Person/Morphs/female/Chest_Reloaded-Lite/Aureola.vmi"},
        "kemenate.Decals.latest": {"Custom/Atom/Person/Textures/kemenate/Decals Female/Face/d_makeup_M_02.png"},
    }


@pytest.mark.parametrize("extension", Ext.TYPES_REPLACE + [Ext.VAM, Ext.VMI])
def test_replace_line_replaces_all_formats_with_matched_mapping(extension):
    line = f'"some_id_thing" : "Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}"'
    replace_mappings = {f"Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}": "replaced"}
    result_line = VarParser.replace_line(line, replace_mappings)
    assert result_line == '"some_id_thing" : "replaced"'


@pytest.mark.parametrize("extension", Ext.TYPES_REPLACE)
def test_replace_line_replaces_supported_formats_with_null_mapping(extension):
    line = f'"some_id_thing" : "Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}"'
    replace_mappings = {f"Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}": None}
    result_line = VarParser.replace_line(line, replace_mappings)
    assert result_line == '"some_id_thing" : ""'


@pytest.mark.parametrize("extension", [Ext.VAM, Ext.VMI])
def test_replace_line_does_not_replace_unsupported_with_null_mapping(extension):
    line = f'"some_id_thing" : "Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}"'
    replace_mappings = {
        f"Author.Package.1:/Custom/Scripts/Author/DoSomething.{extension}": None,
    }
    result_line = VarParser.replace_line(line, replace_mappings)
    assert result_line == line


def test_replace_line_does_not_replace_with_empty_mapping():
    line = '"plugin#0" : "Author.Package.1:/Custom/Scripts/Author/DoSomething.cs"'
    result_line = VarParser.replace_line(line, {})
    assert result_line == line


def test_replace_line_does_not_replace_with_alternate_mapping():
    line = '"plugin#0" : "Author.Package.1:/Custom/Scripts/Author/DoSomething.cs"'
    replace_mappings = {"Author.Package.1:/Custom/Scripts/Author/DoSomething.JPG": "replaced"}
    result_line = VarParser.replace_line(line, replace_mappings)
    assert result_line == line
