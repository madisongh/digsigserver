# Tegra signing

Supports signing of the bootloader, kernel, DTB, firmware, etc. needed for supporting
secure boot on NVIDIA Jetson modules.

**NOTE:** The signer currently supports the R32.x series of Jetson Linux (L4T) releases.
Support for later versions (R35.x and above) and Orin (Tegra234) modules is pending.

## Prerequsities
For Jetson bootloader signing, you must download the BSP and
secure boot packages for the specific version of Jetson Linux you are using
from [NVIDIA's L4T download site](https://developer.nvidia.com/embedded/jetson-linux-archive).
Unpack the two tarballs into a specific location in the filesystem
based on the version and target architecture of the BSP, so they can be found
by the server.  For example, for L4T R32.4.3 for Jetson TX2/Xavier, you would enter:

    $ sudo mkdir -p /opt/nvidia/L4T-32.4.3-tegra186
    $ sudo tar -C /opt/nvidia/L4T-32.4.3-tegra186 -xf Tegra186_Linux_R32.4.3_aarch64.tbz2
    $ sudo tar -C /opt/nvidia/L4T-32.4.3-tegra186 -xf secureboot_R32.4.3_aarch64.tbz2

You can use a different top-level path than `/opt/nvidia` by setting the environment
variable `DIGSIGSERVER_L4T_TOOLS_BASE`. The top-level directory under that base path
must, however, always be `L4T-<version>-<tegraXXX>`, where `version` is the BSP
version (without the "R" prefix) and `tegraXXX` is either `tegra186` for TX2/Xavier or
`tegra210` for TX1/Nano. The server supports having multiple versions of the BSP
installed.

For each BSP version/architecture, you also need a helper script (and possibly one or more
patches to apply to NVIDIA's scripts), available from the
[meta-tegra repository](https://github.com/OE4T/meta-tegra).

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

### Python version requirements and installation paths
Some of the Python scripts included in the L4T BSP are written in Python 2, and assume
that `/usr/bin/python` invokes the Python 2 interpreter.  The signer attempts to work around
that assumption (which can be problematic for more modern distros) by wrapping such
scripts to invoke the Python 2 interpreter through the `python2` command. You **must** still
have Python 2 installed, however, for Tegra signing.

Depending on the BSP version you are using, some of the Python 3 scripts in the BSP package
may not be compatible with more recent versions of Python 3 (such as 3.9 or later).  You should
find patches for those scripts in the [meta-tegra repository](https://github.com/OE4T/meta-tegra)
repository.  (Do **not**, however, apply any patches that convert the Python 2 scripts to
Python 3.)

## Configuration variable

**DIGSIGSERVER_L4T_TOOLS_BASE**: path to the directory under which the L4T BSP package(s)
have been installed.  Defaults to `/opt/nvidia`.

## Key file storage layout
For Jetson bootloader signing, the following files are expected to be present:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/tegrasign/rsa_priv.pem
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/tegrasign/sbk.txt

where `${machine}` is the value of the `machine=` parameter included in the signing request.
The `rsa_priv.pem` file is the PKC private key for signing. It **must** be present.
The `sbk.txt` file is the SBK encryption key.  It is optional, and only need be included
if your device has had an SBK burned into its secure boot fuses.

For later versions of L4T that support encryption of the kernel, kernel DTB, and XUSB firmware
when using  NVIDIA's `hwkey-sample` trusted application on T186/T194 platforms, you should
also provide  the "user key" that you created at:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/tegrasign/user_key.txt

This file is not required, and if you are not using NVIDIA's trusted applications, and/or
you have modified the bootloader to perform only signature checks (as opposed to signature
checks and decryption), you should omit this particular key file.

## REST API endpoint

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
