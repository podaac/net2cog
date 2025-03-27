"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import pathlib
import subprocess
from os.path import basename, splitext

import numpy as np
import pytest
import xarray as xr

from net2cog.netcdf_convert import (
    Net2CogError,
    get_all_data_variables,
    has_spatial_dimensions,
    netcdf_converter,
)


def test_single_cog_generation(smap_file, temp_dir, logger):
    """
    Test that the conversion works and the output is a valid cloud optimized geotiff
    """
    test_file = pathlib.Path(temp_dir, smap_file)

    results = netcdf_converter(
        test_file,
        pathlib.Path(temp_dir),
        ['sss_smap'],
        logger,
    )

    assert len(results) == 1, 'Incorrect number of output file names.'

    assert pathlib.Path(results[0]).is_file(), 'No file created.'
    assert basename(results[0]) == 'sss_smap.tif', 'Incorrect output file name'
    cogtif_val = [
        'rio',
        'cogeo',
        'validate',
        results[0]
    ]

    process = subprocess.run(cogtif_val, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    cog_test = process.stdout
    cog_test = cog_test.replace("\n", "")

    valid_cog = results[0] + " is a valid cloud optimized GeoTIFF"
    assert cog_test == valid_cog, 'Output COG not valid.'


@pytest.mark.parametrize(['in_bands'], [[['gland', 'fland', 'sss_smap']]])
def test_multiple_variable_selection(in_bands, temp_dir, smap_file, logger):
    """
    Verify the correct bands asked for by the user are being converted
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, smap_file)

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


def test_nested_variable_selection(temp_dir, logger, nested_file):
    """Verify a nested variable in a hierarchical granule can be converted."""
    test_file = pathlib.Path(temp_dir, nested_file)

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
    cogtif_val = [
        'rio',
        'cogeo',
        'validate',
        results[0]
    ]

    process = subprocess.run(cogtif_val, check=True, stdout=subprocess.PIPE, universal_newlines=True)
    cog_test = process.stdout
    cog_test = cog_test.replace('\n', '')

    valid_cog = results[0] + ' is a valid cloud optimized GeoTIFF'
    assert cog_test == valid_cog, 'Output is not valid COG.'


@pytest.mark.parametrize(['in_bands'], [[['waldo']]])
def test_unknown_band_selection(in_bands, temp_dir, smap_file, logger):
    """
    Verify an incorrect band asked for by the user raises an exception
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, smap_file)

    with pytest.raises(Net2CogError):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            in_bands,
            logger
        )


def test_non_spatial_variable_fails(temp_dir, logger, nested_file):
    """Verify a request for a non-spatial variable raises expected exception."""
    test_file = pathlib.Path(temp_dir, nested_file)
    expected_exception = (
        'EASE2_global_projection does not have spatial dimensions '
        'such as lat / lon or x / y'
    )

    with pytest.raises(Net2CogError, match=expected_exception):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            ['EASE2_global_projection'],
            logger
        )


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y']],
)
def test_has_spatial_dimensions_present(dimensions):
    """Verify returns True for variable with spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimensions[0], dimensions[1]], np.ones((2, 3)))},
            coords={
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5])),
            },
        ),
    )
    assert has_spatial_dimensions(test_datatree['science'])


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y']],
)
def test_has_spatial_dimensions_and_others_present(dimensions):
    """Verify returns True, when spatial dimensions and others are present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science': (['time', dimensions[0], dimensions[1]], np.ones((1, 2, 3)))
            },
            coords={
                'time': ('time', np.array([0])),
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5])),
            },
        ),
    )
    assert has_spatial_dimensions(test_datatree['science'])


@pytest.mark.parametrize('dimension', ['lat', 'latitude', 'x'])
def test_has_spatial_dimensions_incomplete(dimension):
    """Verify returns False when only one spatial dimension present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimension], np.ones((2)))},
            coords={
                dimension: (dimension, np.array([1, 2])),
            },
        ),
    )
    assert not has_spatial_dimensions(test_datatree['science'])


def test_has_spatial_dimensions_absent():
    """Verify returns False for variable without spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': (['time'], np.ones(3))},
            coords={
                'time': ('time', np.array([1, 2, 3])),
            },
        ),
    )
    assert not has_spatial_dimensions(test_datatree['science'])


def test_get_all_data_variables_flat_input():
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
    assert set(get_all_data_variables(test_datatree)) == set(
        ['/science_one', '/science_two', '/science_three']
    )


def test_get_all_data_variables_hierarchical_input():
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

    assert set(get_all_data_variables(test_datatree)) == set(
        ['/science_one', '/group_one/science_two', '/group_one/group_two/science_three']
    )
