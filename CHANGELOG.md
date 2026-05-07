# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Added
- Added a COG validation utility for checking compatibility with HyBIG
### Changed
- Minor changes and dependency updates
### Deprecated
### Removed
### Fixed
- [issue/94](https://github.com/podaac/net2cog/issues/94): Use `valid_min` and `valid_max` CF attributes for fill value masking
### Security

## [1.3.0]
### Added
- [issue/87](https://github.com/podaac/net2cog/issues/86): Added support for Big TIFF outputs if the input raster is determined to be sufficiently large (>4.6 GB)
### Changed
- [issue/72](https://github.com/podaac/net2cog/issues/72): Empty results that would previously log a message now throw a service error
- [issue/86](https://github.com/podaac/net2cog/issues/86): Data variables not found in the input granule now log a warning instead of throwing a service error
- More robust checking of xarray engine and chunking support for granule inputs
### Deprecated
### Removed
### Fixed
- [issue/85](https://github.com/podaac/net2cog/issues/85): Added complex dtypes to list of supported dtypes for data variables
### Security

## [1.2.0]
### Added
### Changed
- [issues/79](https://github.com/podaac/net2cog/issues/79): Updated python requirement, dependency versions and default netcdf engine used in xarray
### Deprecated
### Removed
### Fixed
### Security
- [issues/requests-update] Updated requests module

## [1.1.1]
### Added
### Changed
- [issues/74](https://github.com/podaac/net2cog/issues/74): Processing SPL3SMP_E list of variables to GeoTIFF fails on tb_time_seconds (float64, units=seconds since <epoch>), no results returned
### Deprecated
### Removed
### Fixed
### Security
- [pull/71](https://github.com/podaac/net2cog/pull/71): Bump urllib from 2.6.2 to 2.6.3
- [pull/69](https://github.com/podaac/net2cog/pull/69): Bump pynacl from 1.6.1 to 1.6.2

## [1.1.0]
### Changed
- [issues/59](https://github.com/podaac/net2cog/issues/59): Update code to support MIL3AEN.004 data due to 3D data with non-spatial dimension last (Latitude, Longitude, Optical_Depth_Range). Add method to retrieve dimensions name from CF-compliant standard_name/units.
- [issues/58](https://github.com/podaac/net2cog/issues/58): Update code to support MODIS V7 MOD10A1 data due to the presence of both "_FillValue" and "missing_value" attributes.
- [issues/61](https://github.com/podaac/net2cog/issues/61): Updated the code to prevent failures when processing SMAP L3 timestamp/timedelta variables by explicitly disabling xarray's default decoding via xr.open_datatree(decode_timedelta=False).  Create a script to build and run pytest unit tests and inside Docker containers.
- [issues/57](https://github.com/podaac/net2cog/issues/54): Update code to support MODIS V7 variable dimension `XDim` and `YDim`.  Also add secondary check for CF-compliant standard_name and units if dimension name does not match.
### Fixed
- [issues/8](https://github.com/podaac/net2cog/issues/8): Reduced peak memory usage of net2cog service, particularly on large granules, by ~60%, enabling high resolution collections to be processed on container images with 8GB RAM.

## [1.0.0]
### Fixed
- [issues/54](https://github.com/podaac/net2cog/issues/54): Update code to not fail on invalid dtypes, log an informative message and continue to process other variables if given. Valid dtypes: [ubyte|uint8|uint16|int16|uint32|int32|float32|float64]. This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).
### Changed
- [issues/50](https://github.com/podaac/net2cog/issues/50): Net2Cog handles the special case of SMAP data with (Y, X, Z) 3D dimensions. This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).
- [issues/46](https://github.com/podaac/net2cog/issues/46): Adds support for output of the SMAP L2 Gridding service, which has dimensions named "x-dim" and "y-dim". This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).
- [issues/12](https://github.com/podaac/net2cog/issues/12): Adds support to update the CRS using information from different variable references. This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).

## [0.6.0]
### Changed
- [issues/37](https://github.com/podaac/net2cog/issues/37): Migrated to use `xarray.DataTree`, in order to provide support for granules with hierarchical structure. This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).
- [issues/37](https://github.com/podaac/net2cog/issues/37): Updated output file format in UMM-S record to "GEOTIFF", to ensure file format selection can be made in Earthdata Search.

## [0.5.0]
### Changed
- [issues/32](https://github.com/podaac/net2cog/issues/32): Added capability to support multiple variables requests, both from explicitly requesting multiple variables, or requesting "all" variables. This also partially addresses [issues/35](https://github.com/podaac/net2cog/issues/35).

## [0.4.0]
### Changed
- [issues/25](https://github.com/podaac/net2cog/issues/25): Converted harmony adapter to operate on STAC catalog
- [issues/3](https://github.com/podaac/net2cog/issues/3): Improved error handling and updated test cases to use new-style harmony execution

## [0.3.0]
### Changed
- Project migrated to https://github.com/podaac/net2cog
- [issues/4](https://github.com/podaac/net2cog/issues/4): Updated UMM-S record for net2cog service

## [0.2.0-alpha.15] - 26 July 2023
### Added
- PCESA-2309 - Implemented the harmony-service-lib interface so that I can be run in the Harmony ngap account
### Changed
- PCESA-2309 - Updated Jenkins to include building and pushing to ECC_NEXUS

## [0.2.0-alpha.14] - 3 September 2020
### Changed
- PCESA-2272 - Updated to use the new SNS Baseworker, Job Service, and Staging Service

## [0.2.0-alpha.12] - 8 June 2020
### Added
- Setup process for CMR UMM-S updating when a build takes place. Added a cmr/ folder to hold umm-s.json, run_umms_updater.sh, cmr.Dockerfile, and associations.txt related to this process.

## [0.2.0-alpha.11] - 11 May 2020
### Added
- Setup process for deploying the netcdf reformatter to SIT using Terraform deployment via Jenkins.  In order to accomplish this I setup unique terraform naming conventions for the netcdf converter while maintaining the same terraform config as l2ss.  Updated the jenkins logic to allow for SIT deployment testing.


[Unreleased]: https://github.com/podaac/net2cog/compare/v1.3.0...HEAD
[1.3.0]: https://github.com/podaac/net2cog/compare/v1.3.0...HEAD
[1.2.0]: https://github.com/podaac/net2cog/compare/v1.2.0...HEAD
[1.1.1]: https://github.com/podaac/net2cog/compare/v1.1.0...HEAD
[1.1.0]: https://github.com/podaac/net2cog/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/podaac/net2cog/compare/v0.6.0...v1.0.0
[0.6.0]: https://github.com/podaac/net2cog/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/podaac/net2cog/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/podaac/net2cog/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/podaac/net2cog/compare/eabb00704a6fc693aa4d79536dc5c5354c6de4d9...v0.3.0
