# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
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


[Unreleased]: https://github.com/podaac/net2cog/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/podaac/net2cog/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/podaac/net2cog/compare/eabb00704a6fc693aa4d79536dc5c5354c6de4d9...v0.3.0
