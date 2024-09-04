"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import os.path
import pathlib
import subprocess
from os import walk
from os.path import dirname, join, realpath

import pytest

from net2cog import netcdf_convert
from net2cog.netcdf_convert import Net2CogError


@pytest.fixture(scope='session')
def data_dir():
    test_dir = dirname(realpath(__file__))
    test_data_dir = join(test_dir, 'data')
    return test_data_dir


@pytest.fixture(scope="function")
def output_basedir(tmp_path):
    return tmp_path


@pytest.mark.parametrize('data_file', [
    'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4/RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc'
])
def test_cog_generation(data_file, data_dir, output_basedir):
    """
    Test that the conversion works and the output is a valid cloud optimized geotiff
    """
    test_file = pathlib.Path(data_dir, data_file)

    results = netcdf_convert.netcdf_converter(test_file, pathlib.Path(output_basedir, data_file), [])

    assert len(results) > 0

    for entry in results:
        if pathlib.Path(entry).is_file():
            cogtif_val = [
                'rio',
                'cogeo',
                'validate',
                entry
            ]

            process = subprocess.run(cogtif_val, check=True, stdout=subprocess.PIPE, universal_newlines=True)
            cog_test = process.stdout
            cog_test = cog_test.replace("\n", "")

            valid_cog = entry + " is a valid cloud optimized GeoTIFF"
            assert cog_test == valid_cog


@pytest.mark.parametrize(['data_file', 'in_bands'], [
    ['SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4/RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc', ['gland', 'fland', 'sss_smap']]
])
def test_band_selection(data_file, in_bands, data_dir, output_basedir):
    """
    Verify the correct bands asked for by the user are being converted
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(data_dir, data_file)

    results = netcdf_convert.netcdf_converter(test_file, pathlib.Path(output_basedir, data_file), in_bands)

    assert len(results) == 3

    out_bands = []
    for entry in results:
        if pathlib.Path(entry).is_file():
            band_completed = entry.split("4.0_")[-1].replace(".tif", "")
            out_bands.append(band_completed)

    out_bands.sort()
    assert in_bands == out_bands


@pytest.mark.parametrize(['data_file', 'in_bands'], [
    ['SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4/RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc', ['waldo']]
])
def test_unknown_band_selection(data_file, in_bands, data_dir, output_basedir):
    """
    Verify an incorrect band asked for by the user raises an exception
    """

    in_bands = sorted(in_bands)
    test_file = pathlib.Path(data_dir, data_file)

    with pytest.raises(Net2CogError):
        netcdf_convert.netcdf_converter(test_file, pathlib.Path(output_basedir, data_file), in_bands)
