"""A pytest module containing test fixtures to be reused through out multiple tests."""

import json
import os
from logging import getLogger
from os.path import dirname, join, realpath
from pathlib import Path
from shutil import copyfile, rmtree
from tempfile import mkdtemp
from typing import Callable

from pytest import fixture
import numpy as np
import xarray as xr


@fixture(scope='session')
def logger():
    return getLogger(__name__)

class DataFiles:
    """Centralized mapping of test collection directories and file basenames."""
    # SMAP L3 (2D)
    SMAP_RSS_L3_SSS_COLLECTION = 'SMAP_RSS_L3_SSS_SMI_8DAY-RUNNINGMEAN_V4'
    SMAP_RSS_L3_SSS_BASENAME = 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.nc'
    SMAP_RSS_L3_SSS_MSG_BASENAME = 'data_operation_message.json'
    SMAP_RSS_L3_SSS_STAC_CATALOG = 'catalog.json'
    SMAP_RSS_L3_SSS_STAC_ITEM = 'RSS_smap_SSS_L3_8day_running_2020_005_FNL_v04.0.json'

    # SPL4CMDL
    SPL4CMDL_COLLECTION = 'SPL4CMDL_007'
    SPL4CMDL_BASENAME = 'SMAP_L4_C_mdl_20150403T000000_Vv7042_001.h5'

    # SPL2SMP
    SPL2SMP_COLLECTION = 'SPL2SMP_008'
    SPL2SMP_BASENAME = 'SMAP_L2_SM_P_00867_A_20150331T194640_R18290_001_subsetted_regridded.nc'

    # SPL3SMP
    SPL3SMP_COLLECTION = 'SPL3SMP_009'
    SPL3SMP_BASENAME = 'SMAP_L3_SM_P_20150410_R19240_001_subset_3d_annotated.nc4'

    # SPL3FTP_E
    SPL3FTP_COLLECTION = 'SPL3FTP_E_004'
    SPL3FTP_BASENAME = 'SMAP_L3_FT_P_E_freeze_thaw_time_seconds_subsetted_regridded.nc4'

    # MISR_AM1_CGAS
    MISR_AM1_CGAS_COLLECTION = 'MIRS_AM1_CGAS_004'
    MISR_AM1_CGAS_BASENAME = 'MISR_AM1_CGAS_OCT_12_2022_F15_0032_subsetted.nc'


@fixture(scope='session')
def data_dir():
    """Location of the tests/data directory in the environment running the tests."""
    test_dir = dirname(realpath(__file__))
    return join(test_dir, 'data')


@fixture(scope='function')
def temp_dir():
    """A temporary directory used for each test, to ensure tests are isolated."""
    temp_directory = mkdtemp()
    yield temp_directory
    rmtree(temp_directory)


@fixture(scope="function")
def copy_test_file(
    data_dir: Path,
    temp_dir: Path,
) -> Callable[[str, str], Path]:
    """Copy any specific test file from a collection folder
    into the per-test temporary directory

    Parameters
    ----------
    data_dir : pathlib.Path
        Base directory containing source data files.
    temp_dir : pathlib.Path
        Temporary directory for test execution.

    Returns
    -------
    pathlib.Path
        Path to the copied file in the temporary directory.

    """
    def copy_file(collection: str, file_basename: str) -> Path:
        temporary_data_file = Path(
            join(temp_dir, file_basename)
        )
        copyfile(
            join(
                data_dir,
                collection,
                file_basename,
            ),
            temporary_data_file,
        )
        return temporary_data_file

    return copy_file


@fixture(scope='function')
def smap_rss_l3_sss_file(copy_test_file: Callable):
    """Path to SMAP NetCDF-4 input file, copied into the test directory."""
    return copy_test_file(
        DataFiles.SMAP_RSS_L3_SSS_COLLECTION,
        DataFiles.SMAP_RSS_L3_SSS_BASENAME
    )


@fixture(scope='function')
def smap_rss_l3_sss_operation_message(copy_test_file: Callable, smap_rss_l3_sss_file):
    """Message for SMAP request. JSON is scoped per function, to avoids affects
    of mutability when updating retrieved dictionary in some tests.

    The base message is updated for each test to include the path to the SMAP
    granule, as hosted in a per-test temporary directory.

    """
    temporary_message_file = copy_test_file(
        DataFiles.SMAP_RSS_L3_SSS_COLLECTION,
        DataFiles.SMAP_RSS_L3_SSS_MSG_BASENAME
    )

    with open(temporary_message_file, 'r', encoding='utf-8') as file_handler:
        data_operation_message = json.load(file_handler)

    data_operation_message['sources'][0]['granules'][0]['url'] = f'file://{smap_rss_l3_sss_file}'

    with open(temporary_message_file, 'w', encoding='utf-8') as file_handler:
        json.dump(data_operation_message, file_handler, indent=2)

    return temporary_message_file


@fixture(scope='function')
def smap_rss_l3_sss_stac(copy_test_file: Callable, smap_rss_l3_sss_item):
    """Main STAC file containing catalog for SMAP data. While the smap_rss_l3_sss_item
    fixture is not called in the body below, declaring it as a dependency
    ensures the file for the item is also populated in the temporary directory.

    """
    return copy_test_file(
        DataFiles.SMAP_RSS_L3_SSS_COLLECTION,
        DataFiles.SMAP_RSS_L3_SSS_STAC_CATALOG
    )


@fixture(scope='function')
def smap_rss_l3_sss_item(copy_test_file: Callable, smap_rss_l3_sss_file):
    """File for STAC item representing the SMAP granule being processed in Harmony
    requests. The JSON object is updated each test to include the path to the
    SMAP granule as hosted in the per-test temporary directory.

    """
    temporary_stac_item_file = copy_test_file(
        DataFiles.SMAP_RSS_L3_SSS_COLLECTION,
        DataFiles.SMAP_RSS_L3_SSS_STAC_ITEM
    )

    with open(temporary_stac_item_file, 'r', encoding='utf-8') as file_handler:
        stac_item_json = json.load(file_handler)

    stac_item_json['assets']['data']['href'] = f'file://{smap_rss_l3_sss_file}'

    with open(temporary_stac_item_file, 'w', encoding='utf-8') as file_handler:
        json.dump(stac_item_json, file_handler, indent=2)

    return temporary_stac_item_file


@fixture(scope='function')
def spl4cmdl_nested_file(copy_test_file: Callable):
    """Path to SPL4CMDL HDF-5 input file, copied into the test directory.

    This file is already subsetted to be a bounding box region of a single
    science variable (NEE/nee_mean) to reduce file size in the repository.

    """
    return copy_test_file(
        DataFiles.SPL4CMDL_COLLECTION,
        DataFiles.SPL4CMDL_BASENAME
    )


@fixture(scope='function')
def mock_environ(tmp_path):
    """
    Replace AWS env variables with fake values, to ensure no real AWS
    calls are executed. During fixture teardown, revert environment
    variables to their original values.
    """
    environment_variables = {
        'AWS_ACCESS_KEY_ID': 'foo',
        'AWS_SECRET_ACCESS_KEY': 'foo',
        'AWS_SECURITY_TOKEN': 'foo',
        'AWS_SESSION_TOKEN': 'foo',
        'AWS_REGION': 'us-west-2',
        'AWS_DEFAULT_REGION': 'us-west-2',
        'SHARED_SECRET_KEY': "shhhhhhhhhhhhhhhhhhhhhhhhhhhhhhh",
        'ENV': "test",
        'DATA_DIRECTORY': str(tmp_path),
        'OAUTH_CLIENT_ID': '',
        'OAUTH_UID': '',
        'OAUTH_PASSWORD': '',
        'OAUTH_REDIRECT_URI': '',
        'STAGING_PATH': '',
        'STAGING_BUCKET': '',
    }

    for variable_name, variable_value in environment_variables.items():
        os.environ[variable_name] = variable_value

    yield

    for variable_name in environment_variables:
        os.unsetenv(variable_name)


@fixture(scope='function')
def spl2smp_nested_file(copy_test_file: Callable):
    """Path to SPL2SMP gridded input file, copied into the test directory.

    This file is already subsetted to be a bounding box region of a single
    science variable (Soil_Moisture_Retrieval_Data/vegetation_opacity and
    Soil_Moisture_Retrieval_Data/vegetation_water_content) to
    reduce file size in the repository.

    """
    return copy_test_file(
        DataFiles.SPL2SMP_COLLECTION,
        DataFiles.SPL2SMP_BASENAME
    )


@fixture(scope="function")
def spl3smp_nested_3d_annotated_file(copy_test_file: Callable):
    """Path to SPL3SMP gridded input file, copied into the test directory.

    This file is already subsetted and to be a bounding box region of a single
    science variable (Soil_Moisture_Retrieval_Data_AM/landcover_class and
    Soil_Moisture_Retrieval_Data_PM/landcover_class) to
    reduce file size in the repository.

    """
    return copy_test_file(
        DataFiles.SPL3SMP_COLLECTION,
        DataFiles.SPL3SMP_BASENAME
    )


@fixture(scope="function")
def spl3ftp_e_variable_selection_file(copy_test_file: Callable):
    """Path to SPL3FTP_E gridded input file, copied into the test directory.

    This file is already subsetted  of a single science variable 
    (Freeze_Thaw_Retrieval_Data_Polar/freeze_thaw_time_seconds) to
    reduce file size in the repository.

    """
    return copy_test_file(
        DataFiles.SPL3FTP_COLLECTION,
        DataFiles.SPL3FTP_BASENAME
    )


@fixture(scope="function")
def mirs_am1_cgas_v4_subsetted_variable(copy_test_file: Callable):
    """Path to MISR_AM1_CGAS input file, copied into the test directory.

    This file is already subsetted and to be a bounding box region to
    reduce file size in the repository.

    """
    return copy_test_file(
        DataFiles.MISR_AM1_CGAS_COLLECTION,
        DataFiles.MISR_AM1_CGAS_BASENAME
    )


@fixture()
def input_datatree():
    """Build Datatree to verify tests.

    Tree structure in test:

    |- science_one(lat, lon)
    |- lat(lat)
    |- lon(lon)
    |- group_one
       |- science_two(lat, lon)
       |- science_three(lat, lon)
       |- group_two
          | science_four(lat, lon)
    |- group_five
       |- variable_one(attr: grid_mapping)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["lat", "lon"], np.ones((2, 3))),
            },
            coords={
                "lat": ("lat", np.array([1, 2])),
                "lon": ("lon", np.array([3, 4, 5])),
            },
        )
    )
    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )
    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )
    dt["group_one/group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_four": (["lat", "lon"], np.ones((2, 3))),
            },
        ),
    )
    dt["group_five/variable_one"] = xr.DataArray(
        data=np.array([[1, 2], [3, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "grid_mapping": "science_one",
            "_FillValue": 355,
            "missing_value": 300, 
        },
    )

    dt["group_five/variable_two"] = xr.DataArray(
        data=np.array([[1, 2], [3, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "grid_mapping": "science_one",
        },
    )
    dt["group_five/variable_two"].encoding["_FillValue"] = 255
    dt["group_five/variable_two"].encoding["missing_value"] = 200

    dt["group_six/variable_one"] = xr.DataArray(
        data=np.array([[1, 999], [999, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "_FillValue": -999,
            "missing_value": 999, 
        },
    )

    dt["group_six/variable_two"] = xr.DataArray(
        data=np.array([[1, 999], [999, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "_FillValue": -999,
        },
    )

    dt["group_six/variable_three"] = xr.DataArray(
        data=np.array([[1, 999], [999, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "missing_value": 999, 
        },
    )

    dt["group_six/variable_four"] = xr.DataArray(
        data=np.array([[1, 2], [3, 4]]),
        dims=('x', 'y'),
        coords={'x': [0, 1], 'y': [0, 1]},
        attrs={
            "grid_mapping": "science_one",
        },
    )
    dt["group_six/variable_four"].encoding["_FillValue"] = 255
    dt["group_six/variable_four"].encoding["missing_value"] = 0

    return dt


@fixture()
def input_datatree_reorder_3d():
    """Build Datatree with 3 dimensions to verify tests.

    Tree structure in test:

    |- science_one(lat, lon, time)
    |- lat(lat)
    |- lon(lon)
    |- time(tim)
    |- group_one
       |- science_two(latitude, longitude, time)
    |- group_two
       |- science_three(x, y, z)
        |- group_three
          | science_four(x-dim, y-dim, z-dim)
    |- group_four
       |- science_five(abc, def, ghi)
    |- group_five
       |- science_six(y, x, "")
    |- group_six
       |- science_seven(x, y, z, w)
    |- group_seven
       |- science_eight(XDim, YDim, ZDim)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["lat", "lon", "time"], np.ones((2, 3, 4))),
            },
            coords={
                "lat": ("lat", np.array([1, 2])),
                "lon": ("lon", np.array([3, 4, 5])),
                "time": ("tim", np.array([6, 7])),
            },
        )
    )
    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["latitude", "longitude", "time"], np.ones((2, 3, 4))),
            },
            coords={
                "latitude": ("lat", np.array([1, 2])),
                "longitude": ("longitude", np.array([3, 4, 5])),
                "time": ("tim", np.array([6, 7])),
            },
        )
    )
    dt["group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["y", "x", "z"], np.ones((2, 3, 2))),
            },
            coords={
                "y": ("y", np.array([1, 2])),
                "x": ("x", np.array([3, 4, 5])),
                "z": ("z", np.array([6, 7])),
            },
        )
    )
    dt["group_two/group_three"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_four": (["y-dim", "x-dim", "z-dim"], np.ones((2, 3, 2))),
            },
            coords={
                "y-dim": ("y-dim", np.array([1, 2])),
                "x-dim": ("x-dim", np.array([3, 4, 5])),
                "z-dim": ("z-dim", np.array([6, 7])),
            },
        )
    )
    dt["group_four"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_five": (["XDim", "YDim", "ZDim"], np.ones((2, 2, 2))),
            },
            coords={
                "XDim": ("XDim", np.array([1, 2])),
                "YDim": ("YDim", np.array([3, 4])),
                "ZDim": ("ZDim", np.array([5, 6])),
            },
        )
    )
    return dt


@fixture()
def input_datatree_bad_3d_variables():
    """Build Datatree with bad 3 dimensions to verify exception tests"""
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["lat", "lon", "time"], np.ones((2, 3, 4))),
            },
            coords={
                "lat": ("lat", np.array([1, 2])),
                "lon": ("lon", np.array([3, 4, 5])),
                "time": ("tim", np.array([6, 7])),
            },
        )
    )
    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["abc", "def", "ghi"], np.ones((2, 2, 2))),
            },
            coords={
                "abc": ("abc", np.array([1, 2])),
                "def": ("def", np.array([3, 4])),
                "ghi": ("ghi", np.array([5, 6])),
            },
        )
    )
    dt["group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["y", "x", ""], np.ones((2, 2, 2))),
            },
            coords={
                "y": ("y", np.array([1, 2])),
                "x": ("x", np.array([3, 4])),
                "": ("", np.array([5, 6])),
            },
        )
    )
    dt["group_three"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["y", "x", "z", "w"], np.ones((2, 2, 2, 2))),
            },
            coords={
                "y": ("y", np.array([1, 2])),
                "x": ("x", np.array([3, 4])),
                "z": ("z", np.array([5, 6])),
                "w": ("w", np.array([7, 8])),
            },
        )
    )

    return dt

@fixture()
def input_datatree_reorder_2d_lon_lat():
    """Build 2 dimension lon, lat Datatree to verify tests.

    Tree structure in test:

    |- science_one(lon, lat)
    |- lat(lat)
    |- lon(lon)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["lon", "lat"], np.ones((2, 3))),
            },
            coords={
                "lon": ("lon", np.array([1, 2])),
                "lat": ("lat", np.array([3, 4, 5])),
            },
        )
    )

    return dt


@fixture()
def input_datatree_reorder_2d_longitude_latitude():
    """Build 2 dimension longitude, latitude Datatree to verify tests.

    Tree structure in test:

    |- science_two(longitude, latitude)
    |- latitude(lat)
    |- longitude(lon)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["longitude", "latitude"], np.ones((2, 3))),
            },
            coords={
                "longitude": ("longitude", np.array([1, 2])),
                "latitude": ("latitude", np.array([3, 4, 5])),
            },
        ),
    )

    return dt


@fixture()
def input_datatree_reorder_2d_x_y():
    """Build 2 dimension x, y Datatree to verify tests.

    Tree structure in test:

    |- science_three(x, y)
    |- x(x)
    |- y(y)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["x", "y"], np.ones((2, 3))),
            },
            coords={
                "x": ("x", np.array([1, 2])),
                "y": ("y", np.array([3, 4, 5])),
            },
        ),
    )

    return dt


@fixture()
def input_datatree_reorder_2d_x_dim_y_dim():
    """Build 2 dimension x-dim, y-dim Datatree to verify tests.

    Tree structure in test:

    |- science_four(x-dim, y-dim)
    |- x-dim(x-dim)
    |- y-dim(y-dim)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_four": (["x-dim", "y-dim"], np.ones((2, 3))),
            },
            coords={
                "x-dim": ("x-dim", np.array([1, 2])),
                "y-dim": ("y-dim", np.array([3, 4, 5])),
            },
        ),
    )

    return dt


@fixture()
def input_datatree_2d_XDim_YDim():
    """Build 2 dimension XDim, YDim Datatree to verify tests.

    Tree structure in test:

    |- science_one(XDim, YDim)
    |- XDim
    |- YDim
    |- group_one
       |- science_two(xDim, yDim)
    |- group_two
       |- science_three(Xdim, Ydim)
    |- group_three
       |- science_four(XDIM, YDIM)
    |- group_four
       |- science_five(xdim, ydim)

    """
    dt = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_one": (["XDim", "YDim"], np.ones((2, 3))),
            },
            coords={
                "XDim": ("XDim", np.array([1, 2])),
                "YDim": ("YDim", np.array([3, 4, 5])),
            },
        ),
    )

    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_two": (["xDim", "yDim"], np.ones((2, 3))),
            },
            coords={
                "xDim": ("xDim", np.array([1, 2])),
                "yDim": ("yDim", np.array([3, 4, 5])),
            },
        ),
    )

    dt["group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_three": (["Xdim", "Ydim"], np.ones((2, 3))),
            },
            coords={
                "Xdim": ("Xdim", np.array([1, 2])),
                "Ydim": ("Ydim", np.array([3, 4, 5])),
            },
        ),
    )

    dt["group_three"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_four": (["XDIM", "YDIM"], np.ones((2, 3))),
            },
            coords={
                "XDIM": ("XDIM", np.array([1, 2])),
                "YDIM": ("YDIM", np.array([3, 4, 5])),
            },
        ),
    )

    dt["group_four"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "science_five": (["xdim", "ydim"], np.ones((2, 3))),
            },
            coords={
                "xdim": ("xdim", np.array([1, 2])),
                "ydim": ("ydim", np.array([3, 4, 5])),
            },
        ),
    )

    return dt


@fixture()
def input_datatree_datetime_units():
    """ Build a DataTree containing datetime64[ns] variables
        for each CF‑compliant time unit (days, hours, minutes,
        milliseconds, microseconds). Used to verify
        apply_datetime_conversion.

    """
    reference_time = np.datetime64("2000-01-01 00:00:00")

    # Root DataTree
    dt = xr.DataTree()

    dt["group_one"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_days": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "days since 2000-01-01 11:58:55.816Z"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_two"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_hours": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "hours since 2000-01-01 11:58:55.816UTC"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_three"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_minutes": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "minutes since 2000-01-01 11:58:55.816Z"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_four"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_seconds": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "seconds since 2000-01-01 11:58:55.816ZUTC"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_five"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_milliseconds": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "milliseconds since 2000-01-01 11:58:55.816Z"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_six"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_microseconds": (
                    ["time"],
                    np.array([reference_time], dtype="datetime64[ns]"),
                    {"units": "microseconds since 2000-01-01 11:58:55.816UTC"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )
    dt["group_seven"] = xr.DataTree(
        dataset=xr.Dataset(
            data_vars={
                "time_seconds": (
                    ["time"],
                    np.array([reference_time], dtype="float64"),
                    {"units": "2000-01-01 11:58:55"},
                )
            },
            coords={"time": ("time", [0])},
        )
    )

    return dt
