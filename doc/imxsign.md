# Bootloader signing for NXP i.MX SoCs

## Prerequisites
For signing i.MX bootloader/kernel images, you must obtain the NXP code signing tool (CST)
from the [NXP web site](https://www.nxp.com), and unpack them under `/opt/NXP`. For example,
using version 3.3.1 of CST:

    $ sudo mkdir -p /opt/NXP
	$ sudo tar -C /opt/NXP -x -f cst-3.3.1.tgz

You can use a different top-level path than `/opt/NXP` by setting the environment
variable `DIGSIGSERVER_IMX_CST_BASE`. Multiple versions of CST are supported; the client
includes the needed version in its request.

## Configuration variable
**DIGSIGSERVER_IMX_CST_BASE**: path to the directory under which the NXP CST tools
have been installed.  Defaults to `/opt/NXP`.

## Keyfile storage layout
For i.MX signing, the necessary keys and certificates are expected to be present in
a tarball named `imx-cst-keys.tar.gz`:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/imxsign/imx-cst-keys.tar.gz

where `${machine}` is the value of the `machine=` parameter included in the signing request.
The tarball is expected to include the private keys, certificates, and SRK table file used by
the `cst` tool to perform the signing. If you use the default PKI generation scripts that
NXP provides in the CST package, this would likely include:

    keys/IMG*.pem
	keys/CSF*.pem
	keys/key_pass.txt
	crts/IMG*.pem
	crts/CSF*.pem
	crts/SRK*table.bin

although the actual contents could vary depending on the number of keys/certs you decided
to create. The tarball is extracted to the server's temporary working directory during
signing.  The certificate path names must match exactly those included in the CSF description
file sent by the client, so using relative path names (or using a flat directory structure,
if desired) is recommended. Note that the `cst` tool itself assumes that the private key
assoicated with a certificate either resides in the same directory as the certificate (with
the filename stem ending with `key` instead of `crt`), or, if the certificate has `crts`
in the path, a parallel directory called `keys` (along with the `crt` -> `key` remapping
in the filename).

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/imx`

Expected parameters:
* `machine=<machine-name>` - a name for the device, used to locate the signing keys
* `soctype=<soctype>` - currently only `mx8m` recognized (but not currently used)
* `cstversion=<cst-version>` - the version of CST (e.g., `3.3.1`)
* `csf=<body>` - plain/text CSF description file
* `artifact=<body>` - binary associated with the CSF description file

Optional parameters:
* `backend=<backend-type>` - backend can be pkcs11 or ssl, defaults to ssl if ommitted

Response: binary CSF blob containing the signing commands, signature hashes, and certificates

The client is responsible for inserting/appending the CSF blob (and an IVT) at the
correct location in the binary for use on the target device.

Example client: TBD
