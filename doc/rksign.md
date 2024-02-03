# Bootloader signing for Rockchip RK3566/68/88 SoCs

## Prerequisites
For signing Rockchip bootloader/kernel images, you need a patched version
of the `mkimage` tool -- Rockchip's downstream patches plus additional fixes --
which can be built from [this fork](https://github.com/madisongh/u-boot-rockchip-downstream).
You also need the Rockchip signing tool (`rk_sign_tool`) from the Rockchip "rkbin"
repository.  If using the [meta-rk3588](https://github.com/madisongh/meta-rk3588)
BSP layer for your builds, you can generate an SDK with the Rockchip-specific
tools you need using the `rk-signing-tools` recipe in that layer, then install
that SDK to a directory on your signing server.

Alternatively, you can locate the following files in your vendor's distribution
of the Rockchip `rkbin` repository and install them manually on your signing
server:

    rkbin/tools/rk_sign_tool
    rkbin/tools/setting.ini
    rkbin/tools/boot_merger

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
* `artifact_type=<type-name>` - one of `fit-image`, `idblock`, or `usbloader`
* `artifact=<body>` - binary to be signed, see below
* `external_data_offset=<hex-number>` - external data offset to be used during FIT signing

Response: signed binary/binaries

For the `fit-image` signing, the input data is expected to be a gzip-compressed tarball
containing two files: the FIT image to be re-signed, called `fitImage`, and the
device tree binary file where the public key information should be replaced, called
`uboot.dtb`.  Note that this is a re-signing operation: you should enable signing
during the build using a randomly-generated RSA keypair, then send the already-signed
FIT and DTB over to have them re-signed with the production key.  The `external_data_offset`
parameter should be included only for kernel FIT signing.

Output from `fit-image` signing is a gzip-compressed tarball containing the updated
`fitImage` and `uboot.dtb` files.

For `idblock` signing, the input is the `idblock.img` generated as part of the
bootloader build, and the ouput is an updated copy of that file with the signature
inserted.

For `usbloader` signing, the input is the USB loader binary (the SPL loader for RK3588,
or the "download" binary for RK3566/68), and the output is an updated copy of that
file with signatures inserted.

Example client:

    # Signing initial loader
    $ curl --silent --fail -X POST -F "machine=idea3588" -F "soctype=rk3588" -F "artifact=@idblock.img" -F "artifact_type=idblock" --output idblock.img.signed http://127.0.0.1:9999/sign/rk
    # Signing kernel FIT image
    $ cp <fitImage from kernel build tree> ./fitImage
    $ cp <u-boot DTB from u-boot compilation> ./uboot.dtb
    $ tar -czf input.tar.gz fitImage uboot.dtb
    $ curl --silent --fail -X POST -F "machine=idea3588" -F "soctype=rk3588" -F "artifact=@input.tar.gz" -F "artifact_type=fit-image" external_data_offset=0x1000 --output output.tar.gz http://127.0.0.1:9999/sign/rk
    # ... then replace the FIT image and DTB with the copies in the output tarball
    # Signing U-Boot FIT image
    $ cp <u-boot build path>/u-boot.itb ./fitImage
    $ cp <u-boot build path>/spl/u-boot-spl.dtb ./uboot.dtb
    $ tar -czf input.tar.gz fitImage u-boot.dtb
    $ curl --silent --fail -X POST -F "machine=idea3588" -F "soctype=rk3588" -F "artifact=@input.tar.gz" -F "artfiact_type=fit-image" --output output.tar.gz http://127.0.0.1:9999/sign/rk
    # ... then replace the FIT image and DTB with the copies in the output tarball
