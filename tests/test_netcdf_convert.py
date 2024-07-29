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


@pytest.fixture(scope='session')
def data_dir():
    test_dir = dirname(realpath(__file__))
    test_data_dir = join(test_dir, 'data')
    return test_data_dir


@pytest.fixture(scope="function")
def output_basedir(tmp_path):
    return tmp_path


@pytest.mark.parametrize('data_file', [
    'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc'
])
def test_cog_generation(data_file, data_dir, output_basedir):
    """
    Test that the conversion works and the output is a valid cloud optimized geotiff
    """
    test_file = pathlib.Path(data_dir, data_file)
    output_dir = pathlib.Path(output_basedir, pathlib.Path(data_file).stem)

    netcdf_convert.netcdf_converter(test_file, pathlib.Path(output_basedir, data_file), [])

    assert os.path.isdir(output_dir)
    output_files = os.listdir(output_dir)
    assert len(output_files) > 0

    with os.scandir(output_dir) as outdir:
        for entry in outdir:
            if entry.is_file():

                cogtif_val = [
                    'rio',
                    'cogeo',
                    'validate',
                    entry.path
                ]

                process = subprocess.run(cogtif_val, check=True, stdout=subprocess.PIPE, universal_newlines=True)
                cog_test = process.stdout
                cog_test = cog_test.replace("\n", "")

                valid_cog = entry.path + " is a valid cloud optimized GeoTIFF"
                assert cog_test == valid_cog


def test_band_selection(data_dir, output_basedir):
    """
    Verify the correct bands asked for by the user are being converted
    """

    in_bands = sorted(['gland', 'fland', 'sss_smap'])
    data_file = 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc'
    test_file = pathlib.Path(data_dir, data_file)
    output_dir = pathlib.Path(output_basedir, pathlib.Path(data_file).stem)

    results = netcdf_convert.netcdf_converter(test_file, pathlib.Path(output_basedir, data_file), in_bands)

    assert os.path.isdir(output_dir)
    output_files = os.listdir(output_dir)
    assert len(output_files) == 3
    assert len(results) == 3

    out_bands = []
    with os.scandir(output_dir) as outdir:
        for entry in outdir:
            if entry.is_file():
                band_completed = entry.name.split("4.0_")[-1].replace(".tif", "")
                out_bands.append(band_completed)

    out_bands.sort()
    assert in_bands == out_bands
