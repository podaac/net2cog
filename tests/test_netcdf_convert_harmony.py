"""
==============
test_netcdf_convert_harmony.py
==============

Test the Harmony service by invoking it as Harmony would.
"""
import json
import os
import sys
from unittest.mock import patch

import pytest
from harmony_service_lib.exceptions import HarmonyException

import net2cog.netcdf_convert_harmony


def test_service_invoke(mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac):
    """Test service invocation, given an input granule, a Harmony message and
    a path to a single-item STAC.

    """
    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_rss_l3_sss_operation_message),
        "--harmony-sources", str(smap_rss_l3_sss_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_multiple_variables(mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac):
    """Test service invocation when including multiple variables."""
    with open(smap_rss_l3_sss_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'].append({
        'id': 'V12345-ABC',
        'name': 'gland',
        'fullPath': 'gland',
    })

    with open(smap_rss_l3_sss_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_rss_l3_sss_operation_message),
        "--harmony-sources", str(smap_rss_l3_sss_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_all_variables(mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac):
    """Test service invocation when no variables are in the input message, which
    occurs when "all" variables are requested.

    """
    with open(smap_rss_l3_sss_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'] = []

    with open(smap_rss_l3_sss_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_rss_l3_sss_operation_message),
        "--harmony-sources", str(smap_rss_l3_sss_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        net2cog.netcdf_convert_harmony.main()


def test_service_error(mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac):
    """Test service invocation when an incorrect variable is supplied and no other
    variables are provided. This should trigger a HarmonyException from an underlying
    Net2CogError that no output files were produced.

    """
    #expected_error = "*Variable ['thor'] cannot be converted to tif:*"
    with open(smap_rss_l3_sss_operation_message, 'r', encoding='utf-8') as file_handler:
        smap_data_operation_json = json.load(file_handler)

    smap_data_operation_json['sources'][0]['variables'][0]['name'] = 'thor'

    with open(smap_rss_l3_sss_operation_message, 'w', encoding='utf-8') as file_handler:
        json.dump(smap_data_operation_json, file_handler, indent=2)

    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(smap_rss_l3_sss_operation_message),
        "--harmony-sources", str(smap_rss_l3_sss_stac),
        "--harmony-metadata-dir", temp_dir,
    ]

    with patch.object(sys, 'argv', test_args):
        with pytest.raises(HarmonyException):
            net2cog.netcdf_convert_harmony.main()


def _set_message_variables(message_file, variables):
    """Overwrite the variables of the first source in a Harmony message file."""
    with open(message_file, 'r', encoding='utf-8') as file_handler:
        message_json = json.load(file_handler)

    message_json['sources'][0]['variables'] = variables

    with open(message_file, 'w', encoding='utf-8') as file_handler:
        json.dump(message_json, file_handler, indent=2)


def _set_item_variable(item_file, variable):
    """Add a ``harmony:variable`` property to a STAC item file."""
    with open(item_file, 'r', encoding='utf-8') as file_handler:
        item_json = json.load(file_handler)

    item_json['properties']['harmony:variable'] = variable

    with open(item_file, 'w', encoding='utf-8') as file_handler:
        json.dump(item_json, file_handler, indent=2)


def _invoke_service(message_file, catalog_file, metadata_dir):
    """Run the service via the CLI, spying on the netcdf_converter call.

    Elaborate setup to spy on the 3rd argument, var_list.
    """
    test_args = [
        net2cog.netcdf_convert_harmony.__file__,
        "--harmony-action", "invoke",
        "--harmony-input-file", str(message_file),
        "--harmony-sources", str(catalog_file),
        "--harmony-metadata-dir", metadata_dir,
    ]

    with patch.object(sys, 'argv', test_args), \
            patch('net2cog.netcdf_convert_harmony.netcdf_convert.netcdf_converter') as mock_netcdf_converter:
        net2cog.netcdf_convert_harmony.main()

    return mock_netcdf_converter


def test_service_item_variable(
    mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, smap_rss_l3_sss_item
):
    """When the message has no variables, the ``harmony:variable`` from the
    input STAC item properties is the only variable processed.

    """
    _set_message_variables(smap_rss_l3_sss_operation_message, [])
    _set_item_variable(smap_rss_l3_sss_item, 'harmony_item_variable')

    mock_converter = _invoke_service(
        smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, temp_dir
    )
    # var_list is the 3rd argument to netcdf_converter.
    assert mock_converter.call_args.args[2] == ['harmony_item_variable']


def test_service_message_variables_override_item_variable(
        mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, smap_rss_l3_sss_item):
    """Variables in the Harmony message take precedence over the
    ``harmony:variable`` in the input STAC item properties.

    This shouldn't happen ever, but if it does, we want to use the variable
    from the message, not the one in the item properties.

    """
    _set_message_variables(smap_rss_l3_sss_operation_message,
                           [{'name': 'message_variable'}, {'name': 'another_var'}])
    _set_item_variable(smap_rss_l3_sss_item, 'harmony_item_variable')

    mock_converter = _invoke_service(
        smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, temp_dir
    )

    assert mock_converter.call_args.args[2] == ['message_variable', 'another_var']


def test_service_no_item_variable(
    mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac
):
    """Without message variables or a ``harmony:variable``, all variables are
    processed.

    """
    _set_message_variables(smap_rss_l3_sss_operation_message, [])

    mock_converter = _invoke_service(
        smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, temp_dir
    )

    assert mock_converter.call_args.args[2] == []
