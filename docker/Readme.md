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

### Building from local code

First build the project with Poetry.

```
poetry build
```

That will create a folder `dist/` and a wheel file that is named with the version of the software that was built. 

In order to use the local wheel file, the `DIST_PATH` build arg must be provided to the `docker build` command
and the `SOURCE` build arg should be set to the path to the wheel file.

Example:

```shell script
docker build -f docker/Dockerfile -t ghcr.io/podaac/net2cog:SIT \
    --build-arg SOURCE="dist/net2cog-1.1.0a1-py3-none-any.whl[harmony]" \
    --build-arg DIST_PATH="dist/" .
```

To use with Harmony in a Box, the output image must be tagged, using the `-t`
flag, with a string that matches the `NET2COG_IMAGE` environment variable
used by Harmony. The default value for this environment variable in Harmony is
`ghcr.io/podaac/net2cog:SIT`, as specified in
[harmony/services/harmony/env-defaults](https://github.com/nasa/harmony/blob/main/services/harmony/env-defaults). This can be overwritten in your local `.env` file
for Harmony.

## Running

If given no arguments, running the docker image will invoke the [Harmony service](https://github.com/nasa/harmony-service-lib-py) CLI.  
This requires the `[harmony]` extra is installed when installing the `net2cog` package from pip (as shown in the examples above).

