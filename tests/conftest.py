"""A pytest module containing test fixtures to be reused through out multiple tests."""
import json
import os
from logging import getLogger
from os.path import dirname, join, realpath
from pathlib import Path
from shutil import copyfile, rmtree
from tempfile import mkdtemp

from pytest import fixture


@fixture(scope='session')
def logger():
    return getLogger(__name__)


@fixture(scope='session')
def data_dir():
    """Location of the tests/data directory in the environment running the tests."""
    test_dir = dirname(realpath(__file__))
    return join(test_dir, 'data')


@fixture(scope='session')
def smap_collection():
    """Name of SMAP collection, used as a subdirectory in tests/data."""
    return 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4'


@fixture(scope='session')
def smap_file_basename():
    """Basename of the SMAP file used as test input."""
    return 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc'


@fixture(scope='function')
def temp_dir():
    """A temporary directory used for each test, to ensure tests are isolated."""
    temp_directory = mkdtemp()
    yield temp_directory
    rmtree(temp_directory)


@fixture(scope='function')
def smap_file(data_dir, temp_dir, smap_collection, smap_file_basename):
    """Path to SMAP NetCDF-4 input file, copied into the test directory."""
    temporary_data_file = Path(join(temp_dir, smap_file_basename))
    copyfile(
        join(data_dir, smap_collection, smap_file_basename),
        temporary_data_file,
    )
    return temporary_data_file


@fixture(scope='function')
def smap_data_operation_message(data_dir, temp_dir, smap_collection, smap_file):
    """Message for SMAP request. JSON is scoped per function, to avoids affects
    of mutability when updating retrieved dictionary in some tests.

    The base message is updated for each test to include the path to the SMAP
    granule, as hosted in a per-test temporary directory.

    """
    temporary_message_file = Path(join(temp_dir, 'data_operation_message.json'))
    copyfile(
        join(data_dir, smap_collection, 'data_operation_message.json'),
        temporary_message_file,
    )

    with open(temporary_message_file, 'r', encoding='utf-8') as file_handler:
        data_operation_message = json.load(file_handler)

    data_operation_message['sources'][0]['granules'][0]['url'] = f'file://{smap_file}'

    with open(temporary_message_file, 'w', encoding='utf-8') as file_handler:
        json.dump(data_operation_message, file_handler, indent=2)

    return temporary_message_file


@fixture(scope='function')
def smap_stac(data_dir, temp_dir, smap_collection, smap_item):
    """Main STAC file containing catalog for SMAP data. While the smap_item
    fixture is not called in the body below, declaring it as a dependency
    ensures the file for the item is also populated in the temporary directory.

    """
    temporary_catalog_file = Path(join(temp_dir, 'catalog.json'))
    copyfile(
        join(data_dir, smap_collection, 'catalog.json'),
        temporary_catalog_file,
    )
    return temporary_catalog_file


@fixture(scope='function')
def smap_item(data_dir, temp_dir, smap_collection, smap_file):
    """File for STAC item representing the SMAP granule being processed in Harmony
    requests. The JSON object is updated each test to include the path to the
    SMAP granule as hosted in the per-test temporary directory.

    """
    stac_item_basename = 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.json'
    temporary_stac_item_file = Path(join(temp_dir, stac_item_basename))
    copyfile(
        join(data_dir, smap_collection, stac_item_basename),
        temporary_stac_item_file,
    )

    with open(temporary_stac_item_file, 'r', encoding='utf-8') as file_handler:
        stac_item_json = json.load(file_handler)

    stac_item_json['assets']['data']['href'] = f'file://{smap_file}'

    with open(temporary_stac_item_file, 'w', encoding='utf-8') as file_handler:
        json.dump(stac_item_json, file_handler, indent=2)

    return temporary_stac_item_file


@fixture(scope='function')
def mock_environ(tmp_path):
    """
    Replace AWS env variables with fake values, to ensure no real AWS
    calls are executed. During fixture teardown, revert environment
    variables to their original values.
    """
    environment_variables = {
        'AWS_ACCESS_KEY_ID': 'foo',
        'AWS_SECRET_ACCESS_KEY': 'foo',
        'AWS_SECURITY_TOKEN': 'foo',
        'AWS_SESSION_TOKEN': 'foo',
        'AWS_REGION': 'us-west-2',
        'AWS_DEFAULT_REGION': 'us-west-2',
        'SHARED_SECRET_KEY': "shhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
        'ENV': "test",
        'DATA_DIRECTORY': str(tmp_path),
        'OAUTH_CLIENT_ID': '',
        'OAUTH_UID': '',
        'OAUTH_PASSWORD': '',
        'OAUTH_REDIRECT_URI': '',
        'STAGING_PATH': '',
        'STAGING_BUCKET': '',
    }

    for variable_name, variable_value in environment_variables.items():
        os.environ[variable_name] = variable_value

    yield

    for variable_name in environment_variables:
        os.unsetenv(variable_name)
