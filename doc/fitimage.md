# Signing fitimages

## Prerequisites
The only tool required is `mkimage` from `u-boot-tools`. This should be on the default PATH
for the server process.

## Keyfile storage layout
The private key used for signing the fitImage is expected in the following location:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/${keyname}.key

See the descriptions of the `machine` and `keyname` parameters below.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/fitimage`

Expected parameters:
* `artifact=<body>` - binary to be signed, when `dummytype` is not specified

Optional parameters:
* `external_data_offset=<offset>` - external data offset to be used during FIT signing (`mkimage -E -p <offset>` flags)
* `mark_required=<any value>` - if this parameter exists the key will be marked as required (`mkimage -r` flag)
* `algo=<signing algorithm>` - specify the hashing and signing algorithms (`mkimage -o` flag)
* `machine=<machine name>` - customize the key path, defaults to `imx`
* `keyname=<name of the key to use or pkcs11 uri>` - specify a keyname other than `dev`; required for `backend=pkcs11`
* `comment=<text>` - add a comment to the FIT signature node (`mkimage -c` flag)
* `backend=<backend-type>` - backend can be `pkcs11` or `ssl`, defaults to `ssl` if omitted
* `dtb=<device tree blob>` - a device tree blob in which the public-key is injected. (`mkimage -K` flag)
* `dummytype=<string>` - can be `auto` or `auto-conf`, for a dummy signing to store the public key in a DTB

Response: signed FIT image when no `dtb=` argument, **or** a tarball containing the signed `fitImage` and the DTB
with the public key inserted, when the `dtb=` argument was given. Note that a tarball is returned even for
dummy signing, even though only the DTB result is meaningful for that case.

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
