"""
==============
test_subset_harmony.py
==============

Test the harmony service
"""
import json
import os.path
import pathlib
import shutil
import sys
from unittest.mock import patch

import pytest
from harmony.exceptions import HarmonyException
from pystac import Catalog

import net2cog.netcdf_convert_harmony


@pytest.fixture(scope='function')
def mock_environ(tmp_path):
    """
    Replace AWS env variables with fake values, to ensure no real AWS
    calls are executed. During fixture shutdown, revert environment
    variables to their original values.
    """
    old_env = os.environ

    os.environ['AWS_ACCESS_KEY_ID'] = 'foo'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'foo'
    os.environ['AWS_SECURITY_TOKEN'] = 'foo'
    os.environ['AWS_SESSION_TOKEN'] = 'foo'
    os.environ['AWS_REGION'] = 'us-west-2'
    os.environ['AWS_DEFAULT_REGION'] = 'us-west-2'
    os.environ['SHARED_SECRET_KEY'] = "shhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh"
    os.environ['ENV'] = "test"
    os.environ['DATA_DIRECTORY'] = str(tmp_path)

    os.environ['OAUTH_CLIENT_ID'] = ''
    os.environ['OAUTH_UID'] = ''
    os.environ['OAUTH_PASSWORD'] = ''
    os.environ['OAUTH_REDIRECT_URI'] = ''
    os.environ['STAGING_PATH'] = ''
    os.environ['STAGING_BUCKET'] = ''

    yield

    os.environ = old_env


def test_service_invoke(mock_environ, tmp_path):
    test_dir = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    data_operation_message = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                                          'data_operation_message.json')
    stac_catalog = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4', 'catalog.json')
    stac_item = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                             'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0',
                             'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.json')
    test_granule = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                                'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc')

    data_operation_message_json = json.load(open(test_dir.joinpath(data_operation_message)))
    data_operation_message_json['sources'][0]['granules'][0]['url'] = f'file://{test_dir.joinpath(test_granule)}'
    tmp_path.joinpath(data_operation_message).parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath(data_operation_message).touch()
    with open(tmp_path.joinpath(data_operation_message), 'w') as f:
        f.write(json.dumps(data_operation_message_json))

    stac_item_json = json.load(open(test_dir.joinpath(stac_item)))
    stac_item_json['assets']['data']['href'] = f'file://{test_dir.joinpath(test_granule)}'
    tmp_path.joinpath(stac_item).parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath(stac_item).touch()
    with open(tmp_path.joinpath(stac_item), 'w') as f:
        f.write(json.dumps(stac_item_json))

    shutil.copy(test_dir.joinpath(stac_catalog), tmp_path.joinpath(stac_catalog))

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", f"{tmp_path.joinpath(data_operation_message)}",
        "--harmony-sources", f"{tmp_path.joinpath(stac_catalog)}",
        "--harmony-metadata-dir", str(tmp_path),
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_error(mock_environ, tmp_path):
    test_dir = pathlib.Path(os.path.dirname(os.path.realpath(__file__)))
    data_operation_message = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                                          'data_operation_message.json')
    stac_catalog = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4', 'catalog.json')
    stac_item = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                             'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0',
                             'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.json')
    test_granule = pathlib.Path('data', 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4',
                                'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc')

    data_operation_message_json = json.load(open(test_dir.joinpath(data_operation_message)))
    data_operation_message_json['sources'][0]['granules'][0]['url'] = f'file://{test_dir.joinpath(test_granule)}'
    data_operation_message_json['sources'][0]['variables'][0]['name'] = 'thor'
    tmp_path.joinpath(data_operation_message).parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath(data_operation_message).touch()
    with open(tmp_path.joinpath(data_operation_message), 'w') as f:
        f.write(json.dumps(data_operation_message_json))

    stac_item_json = json.load(open(test_dir.joinpath(stac_item)))
    stac_item_json['assets']['data']['href'] = f'file://{test_dir.joinpath(test_granule)}'
    tmp_path.joinpath(stac_item).parent.mkdir(parents=True, exist_ok=True)
    tmp_path.joinpath(stac_item).touch()
    with open(tmp_path.joinpath(stac_item), 'w') as f:
        f.write(json.dumps(stac_item_json))

    shutil.copy(test_dir.joinpath(stac_catalog), tmp_path.joinpath(stac_catalog))

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", f"{tmp_path.joinpath(data_operation_message)}",
        "--harmony-sources", f"{tmp_path.joinpath(stac_catalog)}",
        "--harmony-metadata-dir", str(tmp_path),
    ]

    with patch.object(sys, 'argv', test_args):
        with pytest.raises(HarmonyException):
            net2cog.netcdf_convert_harmony.main()
