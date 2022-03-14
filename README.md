# digsigserver
A simple server for processing signing requests via a REST interface, intended for
use with a cross-build system for embedded Linux. It currently handles signing
requests for:
* NVIDIA Jetson bootloader signing
* Kernel module signing
* Mender artifact signing
* Swupdate sw-description signing

## Prerequisites
Requires Python 3.7 or later and a reasonably modern Linux distro to host
the server.  (Tested with Ubuntu 18.04 and later.)  See `setup.py` for
specific Python packages required. 

### Prerequsities: Jetson bootloader signing
For Jetson bootloader signing, you must download the Linux4Tegra BSP and
secure boot packages from [NVIDIA's L4T download site](https://developer.nvidia.com/embedded/linux-tegra).
You must unpack the two tarballs into a specific location in the filesystem
based on the version and target architecture of the BSP, so they can be found
by the server.  For example, for L4T R32.4.3 for Jetson TX2/Xavier, you would enter:

    $ sudo mkdir -p /opt/nvidia/L4T-32.4.3-tegra186
    $ sudo tar -C /opt/nvidia/L4T-32.4.3-tegra186 -xf Tegra186_Linux_R32.4.3_aarch64.tbz2
    $ sudo tar -C /opt/nvidia/L4T-32.4.3-tegra186 -xf secureboot_R32.4.3_aarch64.tbz2

You can use a different top-level path than `/opt/nvidia` by setting the environment
variable DIGSIGSERVER_L4T_TOOLS_BASE. The top-level directory under that base path
must, however, always be `L4T-<version>-<tegraXXX>`, where `version` is the BSP
version (without the "R" prefix) and `tegraXXX` is either `tegra186` for TX2/Xavier or
`tegra210` for TX1/Nano. The server supports having multiple versions of the BSP
installed.

For each BSP version/architecture, you also need a helper script (and possibly one or more
patches to apply to NVIDIA's scripts), available from the
[meta-tegra repository](https://github.com/madisongh/meta-tegra).

For L4T R32.4.3, checkout the **dunfell-l4t-r32.4.3** branch of that repository. The helper scripts
are at `recipes-bsp/tegra-binaries/tegra-helper-scripts/tegraXXX-flash-helper.sh`. The
needed script(s) should get installed without the `.sh` suffix into the `bootloader`
directory for the BSP.  For example (for R32.4.3, TX2/Xavier):

    $ cd /path/to/meta-tegra/recipes-bsp/tegra-binaries/tegra-helper-scripts
    $ sudo install -m 0755 tegra186-flash-helper.sh \
      /opt/nvidia/L4T-32.4.3-tegra186/Linux_for_Tegra/bootloader/tegra186-flash-helper
    $ sudo install -m 0755 tegra194-flash-helper.sh \
      /opt/nvidia/L4T-32.4.3-tegra186/Linux_for_Tegra/bootloader/tegra194-flash-helper

If you are supporting Jetson TX2 or Jetson AGX Xavier devices that use both PKC
signing and SBK encryption of bootloader files, you will also need to apply at
least this patch from meta-tegra:

    $ P=/path/to/meta-tegra/recipes-bsp/tegra-binaries/files
    $ cd /opt/nvidia/L4T-32.4.3-tegra186/Linux_for_Tegra
    $ sudo patch -p1 < $P/0002-Fix-typo-in-l4t_bup_gen.func.patch

Check the `tegraXXX-flashtools-native` recipes in meta-tegra to see if
other patches might also be needed.

### Prerequisites: Kernel module signing
For kernel module signing, your Linux distribution must have the `sign-file` tool
at `/usr/src/linux-headers-$(uname -r)/scripts/sign-file`, and that version of the
tool must be compatible with the kernel you are cross-building.

### Prerequisites: Mender artifact signing
For Mender artifact signing, you must have the `mender-artifact` tool available
in the PATH.  Visit [the Mender documentation pages](https://docs.mender.io) and
go to the "Downloads" section to find a download of a pre-built copy of this tool,
or follow the instructions there for building it from source.  Installing it in
`/usr/local/bin` should make it available.

### Prerequisites: Swupdate signing
For signing `sw-description` files for swupdate packages, `openssl` is required.
RSA and CMS signing methods are supported.

## Installing
Use `pip install` (or `pip3 install` in some cases, to ensure that you are using
Python 3) to install this package and its dependencies.  You can do this system-wide,
for a single user (with the `--user` option), or in a Python 3 virtual environment.

## Configuring
Configuration is handled through environment variables:

**DIGSIGSERVER_KEYFILE_URI**: this should be set to the location of the signing-key files used
for signing operations.  The server only retrieves the files when needed and never retains
them after a signing operation is complete.  Currently, `file://` and `s3://` URIs are
supported.

**DIGSIGSERVER_L4T_TOOLS_BASE**: path to the directory under which the L4T BSP package(s)
have been installed.  Defaults to `/opt/nvidia`.

Other settings for configuring the underlying Sanic framework can also be provided.

### Timeouts

Some signing operations (particularly for bootloader update payloads and Mender
artifacts) can take several minutes to complete, so the server configuration
sets a default `RESPONSE_TIMEOUT` of five minutes. You may need to increase this
setting, depending on your server hardware and expected service load. You should
also configure  client-side timeouts and retries to guard against signing failures
caused by  service timeouts under load.

## Running
Once installed, use the `digsigserver` command to start the server:

    $ digsigserver [--address <ipaddr>] [--port <port>] [--debug]

By default, the server listens on address `0.0.0.0` (i.e, all interfaces) and port
9999 (TCP).

## Signing key storage layout
The signing key files are expected to be organized under `$DIGSIGSERVER_KEYFILE_URI` based
on the type of signing operation and the parameters passed in for signing.

### Jetson bootloader signing
For Jetson bootloader signing, the following files are expected to be present:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/tegrasign/rsa_priv.pem
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/tegrasign/sbk.txt

where `${machine}` is the value of the `machine=` parameter included in the signing request.
The `rsa_priv.pem` file is the PKC private key for signing. It **must** be present.
The `sbk.txt` file is the SBK encryption key.  It is optional, and only need be included
if your device has had an SBK burned into its secure boot fuses.

### Kernel module signing
For kernel module signing, the private and public keys for signing the kernel modules 
are expected to be at:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/kmodsign/kernel-signkey.priv
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/kmodsign/kernel-signkey.x509

where `${machine}` is the value of the `machine=` parameter included in the signing request.

### Mender artifact signing
For Mender artifacts, the signing key is expected to be at

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/mender/private.key

where `${distro}` is the value of the `distro=` parameter included in the signing request.

### SWUpdate sw-description signing
For SWUpdate, the signing key is expected to be at

for RSA:

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/rsa-private.key

For CMS:

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/cms.cert
    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/cms-private.key

where `${distro}` is the value of the `distro=` parameter included in the signing request.

## REST API endpoints
`digsigserver` exposes the following API endpoints:

### Jetson bootloader signing

Request type: `POST`

Endpoint: `/sign/tegra`

Expected parameters:
* `machine=<machine-name>` - a name for the device, used to locate the signing keys
* `soctype=<soctype>` - one of `tegra186`, `tegra194`, `tegra210`
* `bspversion=<l4t-version>` - the L4T BSP version, e.g. `32.4.3`
* `artifact=<body>` - gzip-compressed tarball containing the binaries to be signed

The artifact tarball must also include a `MANIFEST` file with additional
information about the hardware and contents of the tarball.

Response: gzip-compressed tarball containing the signed binaries

Example client: [tegrasign.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/tegrasign.bbclass)

### Kernel module signing

Request type: `POST`

Endpoint: `/sign/modules`

Expected parameters:
* `machine=<machine>` - a name for the device, used to locate the signing keys
* `hashalg=<algname>` (optional) - the hash algorithm to be used, defaults to `sha512`
* `artifact=<body>` - gzip-compressed tarball containing the tree of modules to be signed

Response: gzip-compressed tarball containing the same tree of modules, signed

Example client: [kernel-module-signing.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/kernel-module-signing.bbclass)

### Mender artifact signing

Request type: `POST`

Endpoint: `/sign/mender`

Expected parameters:
* `distro=<distro>` - a name for the "distro", used to locate the signing keys
* `artifact-uri=<url>` - a URL that `digsigserver` can use to download the Mender artifact

Because Mender full-image artifacts are often hundreds of megabytes or larger, the artifact
itself is **not** posted in the body of the request.  Instead, a URL is provided (currently
only supporting `file://` and `s3://` URLs).  The client must upload the artifact to the
specified location. `digsigserver` will download it, apply the signature, then upload
the signed copy back to the same location.

Response: no body, just a status code

Example client: [mendersign.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/mendersign.bbclass)

### SWUpdate sw-description signing

Request type: `POST`

Endpoint: `/sign/swupdate`

Expected parameters:
* `distro=<distro>` - a name for the "distro", used to locate the signing keys
* `sw-description=<body>` - the contents of the `sw-description` file to have signatures included

Response: a `sw-description` file with signatures inserted

Example client: [swupdatesign.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/swupdatesign.bbclass)
 
## Securing signing keys
Signing keys should obviously be kept as secure as possible, but the specifics of doing
that will depend on your specific workflows and facilities.  `digsigserver` does not
manage the storage of signing keys, but expects to be able to retrieve them via the
URI that you configure when they are needed.

If you run `digsigserver` on a locked-down server, storing the key files in the local
filesystem on that server may be adequate.  An AWS S3 bucket, combined with, for example,
bucket-level AWS KMS encryption, may be a viable alternative.

## Securing the signing service
By default, `digsigserver` runs as an unsecured HTTP-based service, and is not intended
to be run as-is on an Internet-connected server.  If you need to control access to it,
you may want to run it behind a reverse proxy server that can perform the necessary
authentication and authorization checks on incoming requests.

# PLEASE NOTE
This code comes with no warranties or assurances as to its security or suitability
for any particular purpose. **Use at your own risk.**
