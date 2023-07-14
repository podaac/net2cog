"""
==============
test_netcdf_convert.py
==============

Test the netcdf conversion functionality.
"""
import shutil
import subprocess
import tempfile
import unittest
from os import listdir, walk
from os.path import dirname, join, realpath, isfile

import netCDF4 as nc
import numpy as np
import xarray as xr
import pytest

from podaac.netcdf_converter import netcdf_convert

class TestNetCDFConverter(unittest.TestCase):
    """
    Unit tests for the NetCDF converter. These tests are all related to the
    NetCDF conversion functionality itself, and should provide coverage on the
    following files:

    - podaac.netcdf_converter.netcdf_convert.py
    """

    @classmethod
    def setUpClass(cls):
        cls.test_dir = dirname(realpath(__file__))
        cls.test_data_dir = join(cls.test_dir, 'data')
        cls.nc_output_dir = tempfile.mkdtemp(dir=cls.test_data_dir)
        cls.test_files = [f for f in listdir(cls.test_data_dir)
                          if isfile(join(cls.test_data_dir, f)) and f.endswith(".nc")]

    @classmethod
    def tearDownClass(cls):
        # Remove the temporary directories used to house netcdf data
        shutil.rmtree(cls.nc_output_dir)


    def test_cog_validation(self):
        """
        Test that the input NetCDF file contains spatial attributes
        """
        for file in self.test_files:
            output_file = "{}_{}".format(self._testMethodName, file)
            netcdf_convert.netcdf_converter(
                join(self.test_data_dir, file), join(self.nc_output_dir, output_file), None)

            tmp_dir = dirname(join(self.nc_output_dir, output_file))
            for path, subdirs, files in walk(tmp_dir):
                for file in files:
                    cogtif_val = [
                        'rio',
                        'cogeo',
                        'validate',
                        file
                        ]

                    cog_name = str(join(tmp_dir, file))

                    cogtif_val = [
                        'rio',
                        'cogeo',
                        'validate',
                        cog_name
                        ]

                    process = subprocess.run(cogtif_val, check=True, stdout=subprocess.PIPE, universal_newlines=True)
                    cog_test = process.stdout
                    cog_test = cog_test.replace("\n", "")

                    valid_cog = cog_name + " is a valid cloud optimized GeoTIFF"
                    self.assertEqual(cog_test, valid_cog)

    def test_band_selection(self):
        """
        Verify the correct bands asked for by the user are being converted
        """

        var1 = 'gland'
        var2 = 'fland'
        var3 = 'sss_smap'

        test_message = {
            'identifier': 'job_id',
            'stagedOutputLocations': ['s3://www.dummyurl.com'],
            'meta': {
                'nc_vars': '{}, {}, {}'.format(var1, var2, var3)
            }
        }

        in_bands = test_message['meta']['nc_vars']
        in_bands = in_bands.split(", ")
        in_bands.sort()

        for file in self.test_files:
            output_file = "{}_{}".format(self._testMethodName, file)
            netcdf_convert.netcdf_converter(
                join(self.test_data_dir, file), join(self.nc_output_dir, output_file), in_bands)

            tmp_dir = dirname(join(self.nc_output_dir, output_file))

            out_bands = []
            for path, subdirs, files in walk(tmp_dir):
                for file in files:
                    # test_band_selection_RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0_fland.tif
                    # test_band_selection_RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0_sss_smap.tif
                    # test_band_selection_RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0_gland.tif

                    band_completed = file.split("4.0_")[-1].replace(".tif", "")
                    out_bands.append(band_completed)

            out_bands.sort()
            self.assertEqual(in_bands, out_bands)
