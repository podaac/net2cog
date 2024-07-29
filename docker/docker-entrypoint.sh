#!/bin/bash
set -e

if [ "$1" = 'net2cog' ]; then
  echo "Not implemented"
  exit 3
elif [ "$1" = 'net2cog_harmony' ]; then
  exec net2cog_harmony "$@"
else
  exec net2cog_harmony "$@"
fi
