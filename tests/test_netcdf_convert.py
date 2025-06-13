"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import pathlib
import subprocess
from os.path import basename, splitext
from rio_cogeo.cogeo import cog_validate, cog_info

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

    assert cog_validate(pathlib.Path(results[0]))[0]
    assert cog_info(pathlib.Path(results[0])).GEO.CRS == 'EPSG:4326'


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

    assert cog_validate(pathlib.Path(results[0]))[0]


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
        "\\['EASE2_global_projection'\\] variable\\(s\\) "
        "yields no results."
    )

    with pytest.raises(Net2CogError, match=expected_exception):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            ['EASE2_global_projection'],
            logger
        )


def test_excluded_variables_not_converted(temp_dir, logger, smap_file):
    """Ensure variables that should be excluded are not converted."""
    test_file = pathlib.Path(temp_dir, smap_file)

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


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim']],
)
def test_has_spatial_dimensions_present(dimensions):
    """Verify returns True for variable with spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimensions[0], dimensions[1]], np.ones((2, 4)))},
            coords={
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5, 6])),
            },
        ),
    )
    assert has_spatial_dimensions(test_datatree['science'])


@pytest.mark.parametrize(
    'dimensions',
    [['lat', 'lon'], ['latitude', 'longitude'], ['x', 'y'], ['x-dim', 'y-dim']],
)
def test_has_spatial_dimensions_and_others_present(dimensions):
    """Verify returns True, when spatial dimensions and others are present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                'science': (['time', dimensions[0], dimensions[1]], np.ones((1, 2, 4)))
            },
            coords={
                'time': ('time', np.array([0])),
                dimensions[0]: (dimensions[0], np.array([1, 2])),
                dimensions[1]: (dimensions[1], np.array([3, 4, 5, 6])),
            },
        ),
    )
    assert has_spatial_dimensions(test_datatree['science'])


@pytest.mark.parametrize('dimension', ['lat', 'latitude', 'x', 'x-dim'])
def test_has_spatial_dimensions_incomplete(dimension):
    """Verify returns False when only one spatial dimension present."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': ([dimension], np.ones((4)))},
            coords={
                dimension: (dimension, np.array([1, 2, 3, 4])),
            },
        ),
    )
    assert not has_spatial_dimensions(test_datatree['science'])


def test_has_spatial_dimensions_absent():
    """Verify returns False for variable without spatial dimensions."""
    test_datatree = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={'science': (['time'], np.ones(4))},
            coords={
                'time': ('time', np.array([1, 2, 3, 4])),
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

    with pytest.raises(Net2CogError):
        netcdf_converter(
            test_file,
            pathlib.Path(temp_dir),
            ["/Soil_Moisture_Retrieval_Data_AM/tb_time_utc"],
            logger,
        )


@pytest.mark.parametrize(
    ['in_bands'],
    [
        [
            [
                'Soil_Moisture_Retrieval_Data_AM/landcover_class',
                'Soil_Moisture_Retrieval_Data_AM/tb_time_utc',
                'Soil_Moisture_Retrieval_Data_PM/landcover_class_pm',
                'Soil_Moisture_Retrieval_Data_PM/tb_time_utc_pm',
            ]
        ]
    ],
)
def test_spl3smp_multiple_variable_selection_without_dtype_string(
    in_bands, temp_dir, spl3smp_nested_3d_annotated_file, logger
):
    """
    Verify non supported dtypes are not are being converted to COG

    Input in_bands: [
                        'Soil_Moisture_Retrieval_Data_AM/landcover_class',
                        'Soil_Moisture_Retrieval_Data_AM/tb_time_utc',
                        'Soil_Moisture_Retrieval_Data_PM/landcover_class_pm',
                        'Soil_Moisture_Retrieval_Data_PM/tb_time_utc_pm'
                    ]

    Remove unsupported dtypes:
                    [
                        'Soil_Moisture_Retrieval_Data_AM/tb_time_utc',
                        'Soil_Moisture_Retrieval_Data_PM/tb_time_utc_pm'
                    ]

    Generated COG output_in_band:
                    [
                        'Soil_Moisture_Retrieval_Data_AM_landcover_class.tif',
                        'Soil_Moisture_Retrieval_Data_PM_landcover_class_pm.tif'
                    ]

    """
    in_bands = sorted(in_bands)
    test_file = pathlib.Path(temp_dir, spl3smp_nested_3d_annotated_file)

    results = netcdf_converter(test_file, pathlib.Path(temp_dir), in_bands, logger)

    assert len(results) == 2, "Incorrect number of output file names."

    in_bands = [in_band.lstrip("/").replace("/", "_") for in_band in in_bands]

    out_bands = []
    for entry in results:
        if pathlib.Path(entry).is_file():
            band_completed = splitext(basename(entry))[0]
            out_bands.append(band_completed)
            assert cog_info(pathlib.Path(entry)).GEO.CRS == 'EPSG:6933'
            assert cog_validate(pathlib.Path(entry))

    out_bands.sort()
    output_in_band = [
        'Soil_Moisture_Retrieval_Data_AM_landcover_class',
        'Soil_Moisture_Retrieval_Data_PM_landcover_class_pm',
    ]
    assert output_in_band == out_bands, 'Incorrect output file names.'
