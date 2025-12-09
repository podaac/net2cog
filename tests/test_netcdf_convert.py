"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import re
import pathlib
import subprocess
from os.path import basename, splitext
from unittest.mock import patch
from rio_cogeo.cogeo import cog_validate, cog_info

import numpy as np
import pytest
import xarray as xr

from net2cog.netcdf_convert import (
    Net2CogError,
    get_all_data_variables,
    netcdf_converter,
    _write_cogtiff,
    process_value_error_exception,
    process_invalid_dimension_order_exception,
    process_dimension_error_exception,
    process_missing_spatial_dimension_error_exception,
)


def test_single_cog_generation(smap_rss_l3_sss_file, temp_dir, logger):
    """
    Test that the conversion works and the output is a valid cloud optimized geotiff
    """
    test_file = pathlib.Path(temp_dir, smap_rss_l3_sss_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['sss_smap'],
        logger,
    )

    assert len(results) == 1, 'Incorrect number of output file names.'

    assert pathlib.Path(results[0]).is_file(), 'No file created.'
    assert basename(results[0]) == 'sss_smap.tif', 'Incorrect output file name'

    assert cog_validate(pathlib.Path(results[0]))[0]
    assert cog_info(pathlib.Path(results[0])).GEO.CRS == 'EPSG:4326'


@pytest.mark.parametrize(['in_bands'], [[['gland', 'fland', 'sss_smap']]])
def test_multiple_variable_selection(in_bands, temp_dir, smap_rss_l3_sss_file, logger):
    """
    Verify the correct bands asked for by the user are being converted
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, smap_rss_l3_sss_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        in_bands,
        logger
    )

    assert len(results) == 3, 'Incorrect number of output file names.'

    out_bands = []
    for entry in results:
        if pathlib.Path(entry).is_file():
            band_completed = splitext(basename(entry))[0]
            out_bands.append(band_completed)

    out_bands.sort()
    assert in_bands == out_bands, 'Incorrect output file names.'


def test_nested_variable_selection(temp_dir, logger, spl4cmdl_nested_file):
    """Verify a nested variable in a hierarchical granule can be converted."""
    test_file = pathlib.Path(temp_dir, spl4cmdl_nested_file)

    # Process test file:
    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['NEE/nee_mean'],
        logger
    )

    # Check results are as expected:
    assert len(results) == 1, 'Incorrect number of output file names.'

    assert pathlib.Path(results[0]).is_file(), 'No file created.'
    assert basename(results[0]) == 'NEE_nee_mean.tif', 'Incorrect output file name'

    assert cog_validate(pathlib.Path(results[0]))[0]


@pytest.mark.parametrize(['in_bands'], [[['waldo']]])
def test_unknown_band_selection(in_bands, temp_dir, smap_rss_l3_sss_file, logger):
    """
    Verify an incorrect band asked for by the user raises an exception
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, smap_rss_l3_sss_file)

    with pytest.raises(Net2CogError):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            in_bands,
            logger
        )


def test_non_spatial_variable_fails(temp_dir, logger, spl4cmdl_nested_file):
    """Verify a request for a non-spatial variable raises expected exception."""
    test_file = pathlib.Path(temp_dir, spl4cmdl_nested_file)
    expected_exception = (
        'EASE2_global_projection does not have spatial dimensions '
        'such as lat/lon, x/y, latitude/longitude, x-dim/y-dim, or XDim/YDim'
    )

    with pytest.raises(Net2CogError, match=expected_exception):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            ['EASE2_global_projection'],
            logger
        )


def test_excluded_variables_not_converted(temp_dir, logger, smap_rss_l3_sss_file):
    """Ensure variables that should be excluded are not converted."""
    test_file = pathlib.Path(temp_dir, smap_rss_l3_sss_file)

    requested_variables = ['gland', 'lat', 'lon', 'time']

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        requested_variables,
        logger
    )

    # Only gland should produce output from the input list of variables:
    assert len(results) == 1, 'Incorrect number of output file names.'
    assert pathlib.Path(results[0]).is_file(), 'No file created.'
    assert basename(results[0]) == 'gland.tif', 'Incorrect output file name'


def test_get_all_data_variables_flat_input(logger):
    """Verify returns all data variables from a file with a single root group."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science_one': (['lat', 'lon'], np.ones((2, 3))),
                'science_two': (['lat', 'lon'], np.ones((2, 3))),
                'science_three': (['lat', 'lon'], np.ones((2, 3))),
                'non_spatial': (['time'], np.ones((4))),
            },
            coords={
                'lat': ('lat', np.array([1, 2])),
                'lon': ('lon', np.array([3, 4, 5])),
                'time': ('time', np.array([6, 7, 8, 9])),
            },
        ),
    )
    assert set(get_all_data_variables(test_datatree, logger)) == set(
        ['/science_one', '/science_two', '/science_three']
    )


def test_get_all_data_variables_hierarchical_input(logger):
    """Verify returns all data variables from a file with nested groups.

    Tree structure in test:

    |- science_one(lat, lon)
    |- lat(lat)
    |- lon(lon)
    |- group_one
       |- science_two(lat, lon)
       |- group_two
          | science_three(lat, lon)

    """
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science_one': (['lat', 'lon'], np.ones((2, 3))),
            },
            coords={
                'lat': ('lat', np.array([1, 2])),
                'lon': ('lon', np.array([3, 4, 5])),
            },
        )
    )
    test_datatree['group_one'] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science_two': (['lat', 'lon'], np.ones((2, 3))),
            },
        ),
    )
    test_datatree['group_one/group_two'] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science_three': (['lat', 'lon'], np.ones((2, 3))),
            },
        ),
    )

    assert set(get_all_data_variables(test_datatree, logger)) == set(
        ['/science_one', '/group_one/science_two', '/group_one/group_two/science_three']
    )


def test_spl2smp_nested_variable_selection(temp_dir, logger, spl2smp_nested_file):
    """Verify a SPL2SMP nested variable in a hierarchical granule can be converted."""
    test_file = pathlib.Path(temp_dir, spl2smp_nested_file)

    # Process test file:
    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['Soil_Moisture_Retrieval_Data/vegetation_water_content'],
        logger
    )

    # Check results are as expected:
    assert len(results) == 1, 'Incorrect number of output file names.'

    assert pathlib.Path(results[0]).is_file(), 'No file created.'
    assert basename(results[0]) == 'Soil_Moisture_Retrieval_Data_vegetation_water_content.tif', 'Incorrect output file name'

    assert cog_validate(pathlib.Path(results[0]))[0]
    assert cog_info(pathlib.Path(results[0])).GEO.CRS == 'EPSG:6933'


@pytest.mark.parametrize(['in_bands'], [[['Soil_Moisture_Retrieval_Data/vegetation_opacity', 'Soil_Moisture_Retrieval_Data/vegetation_water_content']]])
def test_spl2smp_multiple_variable_selection(in_bands, temp_dir, spl2smp_nested_file, logger):
    """
    Verify the correct bands asked for by the user are being converted
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, spl2smp_nested_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        in_bands,
        logger
    )

    assert len(results) == 2, 'Incorrect number of output file names.'

    in_bands = [in_band.lstrip('/').replace('/', '_')
                for in_band in in_bands]

    out_bands = []
    for entry in results:
        if pathlib.Path(entry).is_file():
            band_completed = splitext(basename(entry))[0]
            out_bands.append(band_completed)
            assert cog_info(pathlib.Path(entry)).GEO.CRS == 'EPSG:6933'

    out_bands.sort()
    assert in_bands == out_bands, 'Incorrect output file names.'


def test_spl3smp_nested_variable_3d_annotated(
    temp_dir, logger, spl3smp_nested_3d_annotated_file
):
    """Verify a SPL3SMP nested variable with 3 dimension in a hierarchical granule
    can be converted.

    """
    test_file = pathlib.Path(temp_dir, spl3smp_nested_3d_annotated_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ["Soil_Moisture_Retrieval_Data_AM/landcover_class"],
        logger,
    )

    # Check results are as expected:
    assert len(results) == 1, "Incorrect number of output file names."

    assert pathlib.Path(results[0]).is_file(), "No file created."
    assert (
        basename(results[0]) == "Soil_Moisture_Retrieval_Data_AM_landcover_class.tif"
    ), "Incorrect output file name"
    assert cog_validate(pathlib.Path(results[0]))[0]


def test_spl3smp_all_variable_3d_annotated(
    temp_dir, logger, spl3smp_nested_3d_annotated_file
):
    """Verify a SPL3SMP all variable generate COG for supported dtype
    [ubyte|uint8|uint16|int16|uint32|int32|float32|float64] only.

    The string variables tb_time_utc_am and tb_time_utc_pm will not
    generate COG files."

    """
    test_file = pathlib.Path(temp_dir, spl3smp_nested_3d_annotated_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        [],
        logger,
    )

    # Check results are as expected:
    assert len(results) == 8, "Incorrect number of output file names."

    for entry in results:
        if pathlib.Path(entry).is_file():
            assert (
                basename(entry[0])
                != "Soil_Moisture_Retrieval_Data_AM_tb_time_utc_am.tif"
            )
            assert (
                basename(entry[0])
                != "Soil_Moisture_Retrieval_Data_AM_tb_time_utc_pm.tif"
            )
            assert cog_info(pathlib.Path(entry)).GEO.CRS == "EPSG:6933"
            assert cog_validate(pathlib.Path(entry))


def test_spl3smp_dtype_string_handle_exception(
    temp_dir, logger, spl3smp_nested_3d_annotated_file
):
    """Verify a SPL3SMP variable with dtype=string (S1) throws exception"""
    test_file = pathlib.Path(temp_dir, spl3smp_nested_3d_annotated_file)
    expected_exception = (
        "Variable /Soil_Moisture_Retrieval_Data_AM/tb_time_utc"
        " cannot be converted to tif: invalid dtype: dtype\\('S1'\\)"
    )

    with pytest.raises(Net2CogError, match=expected_exception):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            ["/Soil_Moisture_Retrieval_Data_AM/tb_time_utc"],
            logger,
        )


def test_spl3ftp_e_v4_dtype_timedelta(
    temp_dir, logger, spl3ftp_e_variable_selection_file
):
    """Verify a SPL3FTP_E variable with dtype timedelta/timestamp
    can be converted.

    """
    test_file = pathlib.Path(temp_dir, spl3ftp_e_variable_selection_file)

    # Process test file:
    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['Freeze_Thaw_Retrieval_Data_Polar/freeze_thaw_time_seconds'],
        logger
    )

    # Check results are as expected:
    assert len(results) == 1, "Incorrect number of output file names."

    assert pathlib.Path(results[0]).is_file(), "No file created."
    assert (
        basename(results[0]) == "Freeze_Thaw_Retrieval_Data_Polar_freeze_thaw_time_seconds.tif"
    ), "Incorrect output file name"
    assert cog_validate(pathlib.Path(results[0]))[0]


def test_spl3ftp_e_v4_convert_object_to_numpy_timedelta_valueerror_exception(
    temp_dir, logger, spl3ftp_e_variable_selection_file
):
    """Verify that attempting to open a SPL3FTP_E variable with a timedelta
    or timestamp dtype set to decode_timedelta=None (default) in
    xr.open_datatree(test_file, decode_timedelta=None, ...) raises the
    expected ValueError exception
    
    """
    test_file = pathlib.Path(temp_dir, spl3ftp_e_variable_selection_file)
    expected_exception = (
        'Could not convert object to NumPy timedelta'
    )

    input_datatree = xr.open_datatree(
        test_file,
        decode_coords=None,
        decode_times=None,
        decode_timedelta=None,
        use_cftime=None,
    )

    with pytest.raises(ValueError, match=expected_exception):
        _write_cogtiff(
            temp_dir,
            input_datatree,
            'Freeze_Thaw_Retrieval_Data_Polar/freeze_thaw_time_seconds',
            logger
        )


def test_spl3ftp_e_v4_timedelta_valueerror_exception_using_CFDatetimeCoder_set_true(
    temp_dir, logger, spl3ftp_e_variable_selection_file
):
    """Verify that attempting to open a SPL3FTP_E variable with a timedelta
    or timestamp dtype set to `decode_timedelta=xr.coders.CFDatetimeCoder(use_cftime=True)`
    using xr.open_datatree(test_file, decode_timedelta=True, ...) raises the
    expected ValueError exception
    
    """
    test_file = pathlib.Path(temp_dir, spl3ftp_e_variable_selection_file)
    expected_exception = (
        'Could not convert object to NumPy timedelta'
    )

    input_datatree = xr.open_datatree(
        test_file,
        decode_coords=True,
        decode_times=xr.coders.CFDatetimeCoder(use_cftime=True),
        decode_timedelta=True,
    )

    with pytest.raises(ValueError, match=expected_exception):
        _write_cogtiff(
            temp_dir,
            input_datatree,
            'Freeze_Thaw_Retrieval_Data_Polar/freeze_thaw_time_seconds',
            logger
        )

def test_process_value_error_exception_catch_exception(
    input_datatree,
    logger,
    temp_dir
):
    """Test that process_value_error_exception re-raises a Net2CogError
    when the handler fails to resolve encoding issues.

    """
    test_file = pathlib.Path(temp_dir, 'output.tif')
    value_error_message = f"Variable None has conflicting _FillValue (255) " \
                          f"and missing_value (200). Cannot encode data."

    expected_exception = (
        "Variable group_five/variable_two cannot be converted to tif: "
        "Invalid dimension order. Expected order: ('y', 'x'). You can use "
        "`DataArray.transpose('y', 'x')` to reorder your dimensions. Data variable: variable_two"
    )

    with pytest.raises(Net2CogError, match=re.escape(expected_exception)):
        process_value_error_exception(
            input_datatree,
            "group_five/variable_two",
            value_error_message,
            logger,
            test_file,
        )

@pytest.mark.parametrize(
    "variable_path",
    [
        'group_four/science_five'
        'group_five/science_six',
        'group_six/science_seven',
    ]
)
def test_process_invalid_dimension_order_exception(
    input_datatree_reorder_3d,
    variable_path,
    logger,
    temp_dir
):
    """Ensure that the function handles exceptions when missing
    coordinates are not parsed correctly.

    """
    test_file = pathlib.Path(temp_dir, 'output.tif')

    with pytest.raises(Net2CogError):
        process_invalid_dimension_order_exception(
            input_datatree_reorder_3d,
            variable_path,
            logger,
            test_file,
        )

def test_process_dimension_error_exception_catch_exception(
    input_datatree,
    logger,
    temp_dir
):
    """Test that process_dimension_error_exception re-raises a Net2CogError
    when fails to create a new DataArray with swapped dimensions.

    """
    test_file = pathlib.Path(temp_dir, 'output.tif')

    expected_exception = (
        "Variable group_five/variable_two cannot be converted to tif: "
        "Variable 'y': Using a DataArray object to construct a variable "
        "is ambiguous, please extract the data using the .data property."
    )

    with pytest.raises(Net2CogError, match=re.escape(expected_exception)):
        process_dimension_error_exception(
            input_datatree,
            "group_five/variable_two",
            logger,
            test_file,
        )


def test_mirs_am1_cgas_v4_nested_variable(
    temp_dir, logger, mirs_am1_cgas_v4_subsetted_variable
):
    """Verify a MISR_AM1_CGAS nested variable with 3D in a hierarchical granule
    can be converted.

    """
    test_file = pathlib.Path(temp_dir, mirs_am1_cgas_v4_subsetted_variable)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['Aerosol_Parameter_Average/Absorbing_Optical_Depth'],
        logger,
    )

    # Check results are as expected:
    assert len(results) == 1, "Incorrect number of output file names."

    assert pathlib.Path(results[0]).is_file(), "No file created."
    assert (
        basename(results[0]) == "Aerosol_Parameter_Average_Absorbing_Optical_Depth.tif"
    ), "Incorrect output file name"
    assert cog_validate(pathlib.Path(results[0]))[0]


def test_mirs_am1_cgas_v4_all_variable(
    temp_dir, logger, mirs_am1_cgas_v4_subsetted_variable
):
    """Verify a MISR_AM1_CGAS all variable generate COG for 2D and 3D variables.

    """
    test_file = pathlib.Path(temp_dir, mirs_am1_cgas_v4_subsetted_variable)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        [],
        logger,
    )

   # Check results are as expected:
    assert len(results) == 20, "Incorrect number of output file names."

    for entry in results:
        if pathlib.Path(entry).is_file():
            assert cog_validate(pathlib.Path(entry))


def test_process_missing_spatial_dimension_error_catch_exception(
    temp_dir, logger, mirs_am1_cgas_v4_subsetted_variable
):
    """Verify a MISR_AM1_CGAS variable with 4D throws exception"""
    test_file = pathlib.Path(temp_dir, mirs_am1_cgas_v4_subsetted_variable)
    expected_exception = (
        "Variable Aerosol_Parameter_Average/Spectral_AOD_Scaling_Coefficient"
        " cannot be converted to tif: Only 2D and 3D data arrays supported."
        " ('Latitude', 'Longitude', 'Optical_Depth_Range', 'Coefficient')"
    )

    input_datatree = xr.open_datatree(
        test_file,
        decode_coords=True,
        decode_times=xr.coders.CFDatetimeCoder(use_cftime=True),
        decode_timedelta=True,
    )

    with pytest.raises(Net2CogError, match=re.escape(expected_exception)):
        process_missing_spatial_dimension_error_exception(
            input_datatree,
            "Aerosol_Parameter_Average/Spectral_AOD_Scaling_Coefficient",
            logger,
            test_file,
        )

