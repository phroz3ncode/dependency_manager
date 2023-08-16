import os
import shutil
from unittest import mock
from unittest.mock import PropertyMock

import pytest

from depmanager.common.var_database.var_database import VarDatabase
from depmanager.common.var_object.var_object import VarObject


@pytest.fixture(autouse=True)
def mock_image_dir():
    with mock.patch(
        "depmanager.common.var_services.var_config.IMAGE_RESOURCE_DIR",
        new_callable=PropertyMock(return_value="..\\resources"),
    ):
        yield


@pytest.fixture(name="test_data_dir")
def fixture_test_data_dir():
    return "test_data"


@pytest.fixture(name="test_data_fixture_dir")
def fixture_test_data_fixture_dir(test_data_dir):
    return os.path.join(test_data_dir, "fixtures")


@pytest.fixture(name="test_data_temporary_dir")
def fixture_test_data_temporary_dir(test_data_dir):
    return os.path.join(test_data_dir, "temp")


@pytest.fixture(name="test_database_dir")
def fixture_test_database_path(test_data_dir):
    return os.path.join(test_data_dir, "fixtures_database")


@pytest.fixture(name="temporary_database")
def fixture_temporary_database(test_database_dir, test_data_temporary_dir):
    """Temporary VarDatabase for manipulating files"""
    shutil.rmtree(test_data_temporary_dir, ignore_errors=True)
    shutil.copytree(test_database_dir, test_data_temporary_dir)
    yield VarDatabase(root=test_data_temporary_dir, disable_save=True)
    shutil.rmtree(test_data_temporary_dir, ignore_errors=True)


@pytest.fixture(name="mock_var_database")
@mock.patch("os.rename", return_value=mock.MagicMock())
@mock.patch("os.symlink", return_value=mock.MagicMock())
@mock.patch("shutil.copyfile", return_value=mock.MagicMock())
# pylint: disable=unused-argument
def fixture_mock_var_database(mock_copyfile, mock_symlink, mock_rename, test_database_dir):
    """Real VarDatabase with file manipulation disabled"""
    with mock.patch.object(VarDatabase, "manipulate_file"):
        return VarDatabase(root=test_database_dir, disable_save=True)


@pytest.fixture(name="mock_var_object_name")
def fixture_mock_object_name():
    return "custom.test_scene.1.var"


@pytest.fixture(name="test_var_object")
def fixture_test_var_object(test_database_dir, mock_var_object_name):
    return VarObject(root_path=test_database_dir, file_path=os.path.join(test_database_dir, mock_var_object_name))


@pytest.fixture(name="removed_vars")
def fixture_removed_vars():
    return [
        "Hunting-Succubus.EyeBall_Shadow.6",
        "Blazedust.Script_ParentHoldLink.1",
        "kemenate.Decals.5",
        "Roac.Arty.2",
        "Spacedog.Import_Reloaded_Lite.2",
    ]


@pytest.fixture(name="temporary_repair_database")
def fixture_temporary_repair_database(test_database_dir, test_data_temporary_dir, removed_vars):
    """Temporary VarDatabase for manipulating files"""
    shutil.rmtree(test_data_temporary_dir, ignore_errors=True)
    shutil.copytree(test_database_dir, test_data_temporary_dir)

    for var_name in removed_vars:
        os.remove(os.path.join(test_data_temporary_dir, f"{var_name}.var"))

    yield VarDatabase(root=test_data_temporary_dir, disable_save=True)
    shutil.rmtree(test_data_temporary_dir, ignore_errors=True)
