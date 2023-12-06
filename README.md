# digsigserver
A simple server for processing signing requests via a REST interface, intended for
use with a cross-build system for embedded Linux. It currently handles signing
requests for:
* [NVIDIA Jetson bootloader signing](doc/tegrasign.md)
* [Kernel module signing](doc/kmodsign.md)
* [Mender artifact signing](doc/mendersign.md)
* [Swupdate sw-description signing](doc/swupdsign.md)
* [NXP i.MX SoC family bootloader signing](doc/imxsign.md)
* [OPTEE trusted application signing](doc/opteesign.md)

## Prerequisites
Requires Python 3.7 or later and a reasonably modern Linux distro to host
the server.  (Tested with Ubuntu 18.04 and later.)  See [setup.cfg](setup.cfg) for
specific Python packages required.

The different signers have additional prerequisites, typically involving installation
of the vendor-supplied tools for generating and applying signatures.  Follow the
documentation links above for more information.

## Installing
Use `pip install` (or `pip3 install` in some cases, to ensure that you are using
Python 3) to install this package and its dependencies.  You can do this system-wide,
for a single user (with the `--user` option), or in a Python 3 virtual environment.

## Configuring
Configuration is handled through environment variables.

**DIGSIGSERVER_KEYFILE_URI**: this should be set to the location of the signing-key files used
for signing operations.  The server only retrieves the files when needed and never retains
them after a signing operation is complete.  Currently, `file://` and `s3://` URIs are
supported.

Other settings for configuring the underlying Sanic framework can also be provided.

See the documentation pages on the different signers for their specific configuration
settings (if any)/

**DIGSIGSERVER_L4T_TOOLS_BASE**: path to the directory under which the L4T BSP package(s)
have been installed.  Defaults to `/opt/nvidia`.

### Timeouts

Some signing operations (particularly for Jetson bootloader update payloads and Mender
artifacts) can take several minutes to complete, so the server configuration
sets a default `RESPONSE_TIMEOUT` of five minutes. You may need to increase this
setting, depending on your server hardware and expected service load. You should
also configure client-side timeouts and retries to guard against signing failures
caused by service timeouts under load.

## Running
Once installed, use the `digsigserver` command to start the server:

    $ digsigserver [--address <ipaddr>] [--port <port>] [--debug]

By default, the server listens on address `0.0.0.0` (i.e, all interfaces) and port
9999 (TCP).

## Signing key storage layout
The signing key files are expected to be organized under `$DIGSIGSERVER_KEYFILE_URI` based
on the type of signing operation and the parameters passed in for signing.  See the
documentation for the specific signers you plan to use for details on the expected
location of signing keys under `$DIGSIGSERVER_KEYFILE_URI`.

## REST API endpoints
`digsigserver` exposes one or more REST API endpoints under `/sign/` for each of
the types of signers.  See the [documentation](doc) on each signer for details.

## Securing signing keys
Signing keys should obviously be kept as secure as possible, but the specifics of doing
that will depend on your specific workflows and facilities.  `digsigserver` does not
manage the storage of signing keys, but expects to be able to retrieve them via the
URI that you configure when they are needed.

If you run `digsigserver` on a locked-down server, storing the key files in the local
filesystem on that server may be adequate.  An AWS S3 bucket, combined with, for example,
bucket-level AWS KMS encryption, may be a viable alternative.

## i.MX signing using a YubHSM 2 hardware token
See [i.MX Signing Using a YubiHSM 2 Hardware Token](./doc/imxsign-yubihsm.md) for details on how to set up 
the YubiHSM 2 and invoke the server.

## Securing the signing service
By default, `digsigserver` runs as an unsecured HTTP-based service, and is not intended
to be run as-is on an Internet-connected server.  If you need to control access to it,
you may want to run it behind a reverse proxy server that can perform the necessary
authentication and authorization checks on incoming requests.

# PLEASE NOTE
This code comes with no warranties or assurances as to its security or suitability
for any particular purpose. **Use at your own risk.**
