# Kernel module signing

This can be used for signing kernel modules with a fixed key, rather than using a
randomly-generated keypair at build time, for when a modules are built/deployed
separately.

## Prerequisites
For kernel module signing, your Linux distribution must have the `sign-file` tool
at `/usr/src/linux-headers-$(uname -r)/scripts/sign-file`, and that version of the
tool must be compatible with the kernel you are cross-building.

## Key file layout
For kernel module signing, the private and public keys for signing the kernel modules 
are expected to be at:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/kmodsign/kernel-signkey.priv
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/kmodsign/kernel-signkey.x509

where `${machine}` is the value of the `machine=` parameter included in the signing request.

## REST API Endpoint

Request type: `POST`

Endpoint: `/sign/modules`

Expected parameters:
* `machine=<machine>` - a name for the device, used to locate the signing keys
* `hashalg=<algname>` (optional) - the hash algorithm to be used, defaults to `sha512`
* `artifact=<body>` - gzip-compressed tarball containing the tree of modules to be signed

Response: gzip-compressed tarball containing the same tree of modules, signed

Example client: [kernel-module-signing.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/kernel-module-signing.bbclass)
