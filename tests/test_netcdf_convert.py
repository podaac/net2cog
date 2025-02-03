"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import pathlib
import subprocess
from os.path import basename, splitext

import pytest

from net2cog.netcdf_convert import Net2CogError, netcdf_converter


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

    assert len(results) == 1

    if pathlib.Path(results[0]).is_file():
        assert basename(results[0]) == 'sss_smap.tif'
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
        assert cog_test == valid_cog


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

    assert len(results) == 3

    out_bands = []
    for entry in results:
        if pathlib.Path(entry).is_file():
            band_completed = splitext(basename(entry))[0]
            out_bands.append(band_completed)

    out_bands.sort()
    assert in_bands == out_bands


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
