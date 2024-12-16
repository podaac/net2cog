"""
==============
test_flattening_by_concept_id.py
==============

Test the flattening of the data tree functionality by downloading a granule.
"""
import os.path
import pathlib
import subprocess
from os import walk
from os.path import dirname, join, realpath

import earthaccess

import pytest

from net2cog import netcdf_convert

from util.granule_downloader import download_granule
from util.flatten_nc import flatten_nc_file

@pytest.fixture(scope='session')
def data_dir():
    test_dir = dirname(realpath(__file__))
    return test_dir


@pytest.fixture(scope="function")
def output_basedir(tmp_path):
    return tmp_path

@pytest.fixture(scope="function")
def granule(concept_id):
    # Log in to earthaccess
    earthaccess.login(persist=True)

    # Download the granule
    files = download_granule(concept_id)

    # Provide the file paths to the test
    yield files

    # Cleanup the downloaded files after the test
    for file in files:
        if os.path.exists(file):
            os.remove(file)

def test_flattening(granule, data_dir, output_basedir):
    """
    Test that the flattening works and the output is a netcdf
    """
    assert len(granule) == 1  # Ensure there is exactly one file in granule
    data_file = granule[0]  # Get the single file from the granule list
    assert os.path.exists(data_file)  # Check that the file exists

    test_file = pathlib.Path(data_dir, data_file)
    output_dir = pathlib.Path(output_basedir, pathlib.Path(data_file).stem)
    
    out_file = flatten_nc_file(str(test_file),'geolocation,product,qa_statistics,support_data')
    
    test_file = os.path.splitext(test_file)[0] + "_flattened.nc"
    
    assert test_file == out_file
    
    if os.path.exists(out_file):
        os.remove(out_file)

