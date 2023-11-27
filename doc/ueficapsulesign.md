# UEFI capsule signing

Supports encapsulating kernel and bup payloads into a signed UEFI capsule.

## Prerequisites

    $ apt-get install liblz4-tool
    $ pip3 install PyYAML

## Key file storage layout

For UEFI capsule signing, the following files are expected to be present:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/ueficapsulesign/trusted_public_cert.pem
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/ueficapsulesign/other_public_cert.pem
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/ueficapsulesign/signer_private_cert.pem

where `${machine}` is the value of the `machine=` parameter included in the signing request.

See [here](https://github.com/tianocore/tianocore.github.io/wiki/Capsule-Based-System-Firmware-Update-Generate-Keys) for instructions on how to provision these keys.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/tegra/ueficapsule`

Expected parameters:
* `machine=<machine-name>` - a name for the device, used to locate the signing keys
* `soctype=<soctype>` - one of `tegra194`, `tegra234`
* `bspversion=<l4t-version>` - the L4T BSP version, e.g. `35.4.1`
* `guid=<guid>` - a unique identifier for the target soc type
* `artifact=<body>` - the binary to be signed

Response: the signed capsule

Example usage:

    $ curl --silent --fail -X POST -F "machine=jetson-xavier-nx-devkit-emmc" -F "soctype=tegra194" -F "bspversion=35.4.1" -F "guid=be3f5d68-7654-4ed2-838c-2a2faf901a78" -F "artifact=@tegra-minimal-initramfs-jetson-xavier-nx-devkit-emmc.bl_only.bup-payload" --output ./tegra-bl.cap "http://127.0.0.1:9999/sign/tegra/ueficapsule"

    $ curl --silent --fail -X POST -F "machine=jetson-xavier-nx-devkit-emmc" -F "soctype=tegra194" -F "bspversion=35.4.1" -F "guid=be3f5d68-7654-4ed2-838c-2a2faf901a78" -F "artifact=@tegra-minimal-initramfs-jetson-xavier-nx-devkit-emmc.kernel_only.bup-payload" --output ./tegra-kernel.capa "http://127.0.0.1:9999/sign/tegra/ueficapsule"
