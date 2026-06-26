# Signing fitimages

## Prerequisites
The only tool required is `mkimage` from `u-boot-tools`.

## Keyfile storage layout
The private key used for signing the fitImage is expected in the following location:

    ${DIGSIGSERVER_KEYFILE_URI}/imx/dev.key

The `imx` path is the default but can be customized with REST API parameter.
The name of the key can be customized with a REST API parameter, otherwise `dev` is default.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/fitimage`

Expected parameters:
* `artifact=<body>` - binary to be signed

Optional parameters:
* `external_data_offset=<offset>` - external data offset to be used during FIT signing
* `mark_required=<any value>` - if this parameter exists the key will be marked as required
* `algo=<signing algorithm>` - customize the signing algorithm
* `machine=<machine name>` - customize the key path
* `keyname=<name of the key to use or pkcs11 uri>` - specify a keyname other than `dev`; required for `backend=pkcs11`
* `comment=<text>` - add a comment to the FIT signature node
* `backend=<backend-type>` - backend can be `pkcs11` or `ssl`, defaults to `ssl` if omitted
* `dtb=<device tree blob>` - a device tree blob in which the public-key is injected.

Response: signed binary

Example usage:
```bash
curl --connect-timeout 30 --max-time 1800 --retry 1 --fail -X POST \
    -F external_data_offset=2000 -F "artifact=@fitImage" \
    -F mark_required=true -F machine=tegra -F keyname=devkey \
    --output fitImage.signed http://$DIGSIG_SERVER_IP:$DIGSIG_SERVER_PORT/sign/fitimage
``` 

If the `dtb` parameter is specified, a tarball is returned containing the signed binary and the dtb containing the public-key

Example usage:
```bash
curl --connect-timeout 30 --max-time 1800 --retry 1 --fail -X POST \
    -F external_data_offset=2000 -F "artifact=@fitImage" -F "dtb=@u-boot.dtb \
    -F mark_required=true -F machine=tegra -F keyname=devkey \
    --output artifacts.tar.gz http://$DIGSIG_SERVER_IP:$DIGSIG_SERVER_PORT/sign/fitimage
```
