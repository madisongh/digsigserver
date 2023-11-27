# UEFI signing

Supports signing of the following artifacts that UEFI verifies during boot:

* kernel
* kernel dtb
* L4TLauncher (BOOTAA64.efi)
* extlinux.conf
* initrd

## Prerequisites

    $ apt-get install sbsigntool

## Key file storage layout

For UEFI signing, the following files are expected to be present:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/uefisign/db.key
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/uefisign/db.crt

where `${machine}` is the value of the `machine=` parameter included in the signing request.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/tegra/uefi`

Expected parameters:
* `machine=<machine-name>` - a name for the device, used to locate the signing keys
* `signing_type=<sbsign|signature|attach_signature>` - the type of signing to perform
* `artifact=<body>` - the binary to be signed

Response: the signed binary or signature

Example usage:

    $ curl --silent --fail -X POST -F "machine=jetson-xavier-nx-devkit-emmc" -F "signing_type=sbsign" -F "artifact=@$1" --output $1 "http://127.0.0.1:9999/sign/tegra/uefi"

    $ curl --silent --fail -X POST -F "machine=jetson-xavier-nx-devkit-emmc" -F "signing_type=signature" -F "artifact=@$1" --output $1.sig "http://127.0.0.1:9999/sign/tegra/uefi"

    $ curl --silent --fail -X POST -F "machine=jetson-xavier-nx-devkit-emmc" -F "signing_type=attach_signature" -F "artifact=@$1" --output $1.signed "http://127.0.0.1:9999/sign/tegra/uefi"

where `$1` is one of the UEFI payloads described [here](https://docs.nvidia.com/jetson/archives/r35.4.1/DeveloperGuide/text/SD/Security/SecureBoot.html#generate-signed-uefi-payloads).
