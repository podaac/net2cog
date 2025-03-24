"""
==============
test_netcdf_convert_harmony.py
==============

Test the Harmony service by invoking it as Harmony would.
"""
import json
import sys
from unittest.mock import patch

import pytest
from harmony_service_lib.exceptions import HarmonyException

import net2cog.netcdf_convert_harmony


def test_service_invoke(mock_environ, temp_dir, smap_data_operation_message, smap_stac):
    """Test service invocation, given an input granule, a Harmony message and
    a path to a single-item STAC.

    """
    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_data_operation_message),
        "--harmony-sources", str(smap_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_multiple_variables(mock_environ, temp_dir, smap_data_operation_message, smap_stac):
    """Test service invocation when including multiple variables."""
    with open(smap_data_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'].append({
        'id': 'V12345-ABC',
        'name': 'gland',
        'fullPath': 'gland',
    })

    with open(smap_data_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_data_operation_message),
        "--harmony-sources", str(smap_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_all_variables(mock_environ, temp_dir, smap_data_operation_message, smap_stac):
    """Test service invocation when no variables are in the input message, which
    occurs when "all" variables are requested.

    """
    with open(smap_data_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'] = []

    with open(smap_data_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_data_operation_message),
        "--harmony-sources", str(smap_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_error(mock_environ, temp_dir, smap_data_operation_message, smap_stac):
    """Test service invocation when an incorrect variable is supplied. This
    should trigger a HarmonyException containing the original xarray KeyError
    message.

    """
    with open(smap_data_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'][0]['name'] = 'thor'

    with open(smap_data_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_data_operation_message),
        "--harmony-sources", str(smap_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        with pytest.raises(HarmonyException, match="No variable named 'thor'."):
            net2cog.netcdf_convert_harmony.main()
