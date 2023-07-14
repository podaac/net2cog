#!/usr/bin/env bash
set -Eexo pipefail

tf_venue=$1

cmr_user=$(aws ssm get-parameter --profile "ngap-service-${tf_venue}" --with-decryption --name "urs_user" --output text --query Parameter.Value)
cmr_pass=$(aws ssm get-parameter --profile "ngap-service-${tf_venue}" --with-decryption --name "urs_password" --output text --query Parameter.Value)

umms_updater -f cmr/netcdf_cmr_umm_s.json -a cmr/associations.txt -p POCLOUD -e ${tf_venue} -cu "$cmr_user" -cp "$cmr_pass"