# Netcdf Converter

Conversion service for netcdf4 files to cloud optimized geotiff.  This repository contains the source code, unit test suite, and Jupyter notebook documentation.

## Directory structure

```
📁
├── .📁 github
├── 📁 cmr
├── 📁 bin
├── 📁 docker
├── 📁 docs
├── 📁 net2cog
├── 📁 tests
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── README.md
├── poetry.lock
├── pyproject.toml
└── run_tests.sh
```

* `.github` - Contains CI/CD workflows and pull request template.
* `cmr` - Contains files for updating the service's CMR UMM-S profile
* `bin` - A directory containing utility scripts to build the service and test
  images. A script to extract the release notes for the most recent version, as
  contained in `CHANGELOG.md` is also in this directory.
* `docker` - A directory containing the Dockerfiles for the service and test
  images. It also contains `service_version.txt`, which contains the semantic
  version number of the library and service image. Update this file with a new
  version to trigger a release.
* `docs` - A directory containing NetCDF Converter Service documentation.
* `example` - Directory containing Jupyter notebook documentation
* `net2cog` - The directory containing Python source code for
  the net2cog Service. `netcdf_convert_harmony.py` contains the `NetcdfConverterService`
  class that is invoked by calls to the service.
* `tests` -  Contains the `pytest` test suite.
* `CHANGELOG.md` - Contains a record of changes applied to each new release
  of the net2cog Service.
* `CONTRIBUTING.md` -  Instructions on how to contribute to the repository.
* `LICENSE` - Required for distribution under NASA open-source approval.
  Details conditions for use, reproduction and distribution.
* `README.md` - This file, containing guidance on developing the library and service.
* `poetry.lock` - Python's Poetry dependency management system. This file plays a crucial role in ensuring reproducible and consistent de.
* `pyproject.toml` - Contains a list of Python packages needed to run the service.
* `run_tests.sh` - Script to manage Python environment, install dependencies, and run tests. The script can be used to build and run pytest both locally and within Docker container.


## Developer Notes

### Local development:

Local testing of service functionality is best achieved via a local instance of
[Harmony](https://github.com/nasa/harmony). Please see instructions there
regarding creation of a local Harmony-In-A-Box instance.

## Test in Docker:

This service utilises the Python `pytest` package to perform unit tests on
classes and functions in the service. After local development is complete, and
test have been updated, they can be run via:

```bash
$ ./bin/build-image
$ ./bin/build-test
$ ./bin/run-test
```

The `run_tests.sh` script will also generate a coverage report, rendered
in HTML, and scan the code with `pylint`.

The `unittest` suite is run automatically via GitHub Actions as part of a
GitHub "workflow". These workflows are defined in the `.github/workflows`
directory.


## Test locally:

```bash
$ ./run_tests.sh
```

The `run_tests.sh` script will also generate a coverage report, rendered
in HTML, and scan the code with `pylint`.