# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
### Changed
- Project migrated to https://github.com/podaac/net2cog

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
