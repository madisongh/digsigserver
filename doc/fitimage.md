# Signing fitimages

## Prerequisites
The only tool required is `mkimage` from `u-boot-tools`.

## Keyfile storage layout
The private key used for signing the fitImage is expected in the following location:

    ${DIGSIGSERVER_KEYFILE_URI}/imx/dev.key

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
* `keyname=<name of the key to use>` - specify a keyname other than `dev`

Response: signed binary

Example usage:
    curl --connect-timeout 30 --max-time 1800 --retry 1 --fail -X POST \
        -F external_data_offset=2000 -F "artifact=@fitImage" \
        -F mark_required=true -F keyname=devkey \
        --output fitImage.signed http://$DIGSIG_SERVER_IP:$DIGSIG_SERVER_PORT/sign/fitimage


## Future improvements
* Enable including a device tree blob in which the public key is injected.
* Change the `imx` "machine" to something more logical, this is not machine dependent

