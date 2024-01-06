# Re-signing Rockchip OP-TEE Trusted Applications

Since Rockchip supplies OP-TEE in binary form only in its downstream implementation,
they also provide tools for replacing their signing keypair with your own:

* The `change_puk` tool replaces the embedded public key in the TEE.
* The `resign_ta.py` tool replaces the signature on `.ta` files (trusted applications).

These are supplied by Rockchip in the `rk_tee_user` repository. If you are using the
[meta-rk3588](https://github.com/madisongh/meta-rk3588) BSP layer in your builds, the
`rk-signing-tools` recipe in that layer supplies these tools as part of the SDK
it builds.

## Configuration variable
**DIGSIGSERVER_RK_TOOLS_PATH**: path to a directory containing the above-mentioned
tools.  This is the same variable used by the [Rockchip bootloader signer](rksign.md).


## Key file storage layout
The private and public keys are expected to be at:

    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/rkopteesign/optee-signing-key.pem
    ${DIGSIGSERVER_KEYFILE_URI}/${machine}/rkopteesign/optee-signing-pubkey.pem

where `${machine}` is the value of the `machine=` parameter included in the signing request.

## REST API endpoints

### TEE re-signing

Request type: `POST`

Endpoint: `/sign/rkoptee-tee`

Expected parameters:
* `machine=<machine>` - a name for the device, used to locate the signing keys
* `artifact=<body>` - the contents of the TEE (typically the `<chip>_bl32_<version>.bin` file from rkbin)

Response: TEE with the updated public key

Example client:

    $ curl --silent --fail -X POST -F "machine=idea3588" -F "artifact=@rk3588_bl32_v1.14.bin" --output bl32.signed http://127.0.0.1:9999/sign/rkoptee-tee

### TA re-signing

Request type: `POST`

Endpoint: `/sign/rkoptee-ta`

Expected parameters:
* `machine=<machine>` - a name for the device, used to locate the signing keys
* `artifact=<body>` - gzip-compressed tarball containing a tree of `<uuid>.ta` files

Response: gzip-compressed tarball containing the re-signed `<uuid>.ta` files

Example client:

    $ find . -type f -name '*.ta' | xargs tar -czf ta-files.tar.gz
	$ curl --silent --fail -X POST -F "machine=idea3588" -F "artifact=@ta-files.tar.gz" --output ta-files-resigned.tar.gz http://127.0.0.1:9999/sign/rkoptee-ta
