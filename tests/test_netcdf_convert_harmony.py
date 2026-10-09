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

import pystac
import pytest
from harmony_service_lib import BaseHarmonyAdapter
from harmony_service_lib.exceptions import HarmonyException
from harmony_service_lib.message import Message

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


def _set_catalog_variable(catalog_file, variable):
    """Add a ``harmony:variable`` field to the item link of a STAC catalog file."""
    with open(catalog_file, 'r', encoding='utf-8') as file_handler:
        catalog_json = json.load(file_handler)

    the_link = next(link for link in catalog_json['links'] if link['rel'] == 'item')
    the_link['harmony:variable'] = variable

    with open(catalog_file, 'w', encoding='utf-8') as file_handler:
        json.dump(catalog_json, file_handler, indent=2)


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


def test_service_catalog_variable(
    mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac
):
    """When the message has no variables, the ``harmony:variable`` from the
    input catalog is the only variable processed.

    """
    _set_message_variables(smap_rss_l3_sss_operation_message, [])
    _set_catalog_variable(smap_rss_l3_sss_stac, 'harmony_catalog_variable')

    mock_converter = _invoke_service(
        smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, temp_dir
    )
    # var_list is the 3rd argument to netcdf_converter.
    assert mock_converter.call_args.args[2] == ['harmony_catalog_variable']


def test_service_message_variables_override_catalog_variable(
        mock_environ, temp_dir, smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac):
    """Variables in the Harmony message take precedence over the
    ``harmony:variable`` in the input catalog.

    This shouldn't happen ever, but if it does, we want to use the variable
    from the message, not the one in the catalog link.

    """
    _set_message_variables(smap_rss_l3_sss_operation_message,
                           [{'name': 'message_variable'}, {'name': 'another_var'}])
    _set_catalog_variable(smap_rss_l3_sss_stac, 'harmony_catalog_variable')

    mock_converter = _invoke_service(
        smap_rss_l3_sss_operation_message, smap_rss_l3_sss_stac, temp_dir
    )

    assert mock_converter.call_args.args[2] == ['message_variable', 'another_var']


def test_service_no_catalog_variable(
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


def test_invoke_no_item_links(mock_environ, smap_rss_l3_sss_operation_message):
    """invoke() leaves the catalog variable unset when there are no item links*.

    *This may never happen.
    """
    with open(smap_rss_l3_sss_operation_message, 'r', encoding='utf-8') as file_handler:
        message = Message(json.load(file_handler))


    with patch.object(BaseHarmonyAdapter, 'invoke') as mock_base_invoke:

        adapter = net2cog.netcdf_convert_harmony.NetcdfConverterService(
            message, catalog=pystac.Catalog('test', 'test no links')
        )
        adapter.invoke()

    mock_base_invoke.assert_called_once() # netcdfConverterService.invoke made it to the super().invoke().
    assert adapter._harmony_catalog_variable is None  # pylint: disable=protected-access
