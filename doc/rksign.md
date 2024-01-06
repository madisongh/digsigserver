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

Example client:

    # Signing initial loader
    $ curl --silent --fail -X POST -F "machine=idea3588" -F "soctype=rk3588" -F "artifact=@idblock.img" -F "artifact_type=idblock" --output idblock.img.signed http://127.0.0.1:9999/sign/rk
	# Signing U-Boot or kernel FIT image
	$ curl --silent --fail -X POST -F "machine=idea3588" -F "soctype=rk3588" -F "artifact=@data2sign.bin" -F "artfiact_type=fit-data" --output fit.sig http://127.0.0.1:9999/sign/rk

The Rockchip FIT generation tools compose the `data2sign.bin` file from the contents of the FIT image that need signing. The generated `fit.sig` file (from the example above) can then be inserted into the FIT image, replacing signature inserted during the FIT image creation, which uses a dynamically-generated key.  Sample bitbake code for the signature replacement:

    RKSIGN_FIT_IMAGE ??= "fitImage"
    RKSIGN_SIG_FILE ??= "${RKSIGN_FIT_IMAGE}.sig"
    RKSIGN_SIG_NODE ??= "/configurations/conf/signature"

    python do_rk_update_signature() {
        import subprocess

        fit_file = d.getVar('RKSIGN_FIT_IMAGE')
        new_sig_file = d.getVar('RKSIGN_SIG_FILE')
        output = subprocess.check_output(['fit_info', '-f', fit_file,
                                          '-n', d.getVar('RKSIGN_SIG_NODE'),
                                          '-p', 'value']).decode('UTF-8')
        sig_len = sig_offset = sig_end = None
        for line in output.split('\n'):
            words = line.split()
            if len(words) != 2:
                continue
            if words[0].upper() == "LEN:":
                sig_len = int(words[1])
            elif words[0].upper() == "OFF:":
                sig_offset = int(words[1])
            elif words[0].upper() == "END:":
                sig_end = int(words[1])
        if sig_len is None or sig_offset is None or sig_end is None:
            bb.error("Could not extract signature location info from %s" % fit_file)
        with open(new_sig_file, "rb") as f:
            new_sig = f.read()
        if len(new_sig) != sig_len:
            bb.error("New signature length (%d) does not match existing signature length (%d)" % (len(new_sig), sig_len))
        with open(fit_file, "r+b") as f:
            f.seek(sig_offset)
            f.write(new_sig)
        os.unlink(new_sig_file)
    }
    do_rk_update_signature[depends] += "rk-u-boot-tools-native:do_populate_sysroot"
    do_rk_update_signature[dirs] = "${B}"

Using the above code, the task sequence should be FIT generation -> call to digsigserver to generate replacement signature -> `do_rk_update_signature`.  The same sequence
applies to both the U-Boot FIT and the kernel FIT.
