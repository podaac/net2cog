# net2cog Service Docker Image

This directory contains the `Dockerfile` used to build the Docker image capable of running the net2cog service.

## Building

The docker image is setup to install the net2cog project into userspace using pip. It will look
in both PyPi and TestPyPi indexes unless building from a local wheel file.

In order to build the image the following build arguments are needed

- `SOURCE` : The value of this build arg will be used in the `pip install` command to install the net2cog package 
- `DIST_PATH` (optional): The value of this build arg should be the path (relative to the context) to the directory containing a locally built wheel file 

### Building from PyPi or TestPyPi

If the version of the net2cog package has already been uploaded to PyPi, all that is needed is to supply
the `SOURCE` build argument with the package specification.  

Example:

```shell script
docker build -f docker/Dockerfile --build-arg SOURCE="net2cog[harmony]==1.1.0-alpha.9" .
```

### Local development:

Local testing of service functionality is best achieved via a local instance of
[Harmony](https://github.com/nasa/harmony). Please see instructions there
regarding creation of a local Harmony-In-A-Box instance.

## Test in Docker:

This service utilises the Python `pytest` package to perform unit tests on
classes and functions in the service. After local development is complete, and
test have been updated, they can be run via:

```bash
$ cd ..
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
$ cd ..
$ ./run_tests.sh
```

The `run_tests.sh` script will also generate a coverage report, rendered
in HTML, and scan the code with `pylint`.