# Bootloader signing for Rockchip RK3566/68/88 SoCs

## Prerequisites
For signing Rockchip bootloader/kernel images, you need the `openssl` tools
and the Rockchip signing tool (`rk_sign_tool`) from the Rockchip "rkbin"
repository.  If using the [meta-rk3588](https://github.com/madisongh/meta-rk3588)
BSP layer for your builds, you can generate an SDK with the Rockchip-specific
tools you need using the `rk-signing-tools` recipe in that layer, then install
that SDK to a directory on your signing server.

Alternatively, you can locate the following files in your vendor's distribution
of the Rockchip `rkbin` repository and install them manually on your signing
server:

    `rkbin/tools/rk_sign_tool`
    `rkbin/tools/setting.ini`
    `rkbin/tools/boot_merger`

They must be installed in a directory called `${DIGSIGSERVER_RK_TOOLS_PATH}/rkbin-tools`.

## Configuration variable
**DIGSIGSERVER_RK_TOOLS_PATH**: path to a directory containing a subdirectory
called `rkbin-tools` that contain the Rockchip-specific tools from the `rkbin`
repository.

## Keyfile storage layout
For Rockchip signing, the RSA keypair and associated certificate that you generate
for securing your boot chain (per the Rockchip documentation) are expected to be
at the following locations:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/rksign/dev.key
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/rksign/dev.pubkey
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/rksign/dev.crt

where `${machine}` is the value of the `machine=` parameter included in the signing request.
The `.key` file is the private key, the `.pubkey` file is the public key, and the `.crt`
file is the X.509 certificate.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/rk`

Expected parameters:
* `machine=<machine-name>` - a name for the device, used to locate the signing keys
* `soctype=<soctype>` - one of `3566`, `3568`, or `3588`
* `artifact_type=<type-name>` - one of `fit-data`, `idblock`, or `usbloader`
* `artifact=<body>` - binary to be signed, see below

Response: signed binary.

For `fit-data` signing, the input data is expected to be just the
bits of the kernel or u-boot FIT image that require signing, and the output is
the signature to be inserted into the output FIT image.

For `idblock` signing, the input is the `idblock.img` generated as part of the
bootloader build, and the ouput is an updated copy of that file with the signature
inserted.

For `usbloader` signing, the input is the USB loader binary (the SPL loader for RK3588,
or the "download" binary for RK3566/68), and the output is an updated copy of that
file with signatures inserted.

Example client: TBD
