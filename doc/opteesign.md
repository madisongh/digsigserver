# Signing OP-TEE Trusted Applications

This signer implements a subset of the functions in the `sign-encrypt.py` script
from the OP-TEE OS build environment.  Only signing is supported (no encryption),
and only a single signing algorithm is supported.

## Prerequisites
The OP-TEE TA signer directly calls on functions in the Python `cryptography`
package - in particular, functions in the "Hazardous Materials" section of
that package. The `cryptography` package has changed frequently over its history
and has complicated dependencies on underlying crypto library packages, so
be careful.

## Key file storage layout
For signing OP-TEE trusted applications, the private key for signing TAs is expected
to be at:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/opteesign/optee-signing-key.pem

where `${machine}` is the value of the `machine=` parameter included in the signing request.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/optee`

Expected parameters:
* `machine=<machine>` - a name for the device, used to locate the signing keys
* `artifact=<body>` - gzip-compressed tarball containing a tree of `<uuid>.stripped-elf` and `<uuid>.ta-version` files

Response: gzip-compressed tarball containing the signed `<uuid>.ta` files

Example client: TBD
