"""
==============
test_subset_harmony.py
==============

Test the harmony service
"""
import json
import os.path
import sys
from unittest.mock import patch

import pytest

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


def test_service_invoke(mock_environ):
    test_dir = os.path.dirname(os.path.realpath(__file__))
    input_json = json.load(
        open(os.path.join(test_dir, 'data', 'test_netcdf_convert_harmony', 'test_service_invoke.input.json')))
    test_granule = os.path.join(test_dir, 'data', 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc')
    input_json['sources'][0]['granules'][0]['url'] = f'file://{test_granule}'

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input", json.dumps(input_json)
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()
