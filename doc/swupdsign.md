# Signing swupdate packages

Provides a signer for the `sw-description` used in swupdate packages.

## Prerequisites
For signing `sw-description` files for swupdate packages, `openssl` is required.
RSA and CMS signing methods are supported.

## Key file storage layout
For SWUpdate, the signing key is expected to be at

for RSA:

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/rsa-private.key

For CMS:

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/cms.cert
    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/swupdate/cms-private.key

where `${distro}` is the value of the `distro=` parameter included in the signing request.

## REST API endpoint

Request type: `POST`

Endpoint: `/sign/swupdate`

Expected parameters:
* `distro=<distro>` - a name for the "distro", used to locate the signing keys
* `sw-description=<body>` - the contents of the `sw-description` file to have signatures included

Optional parameters:
* `method=<method>` - may be `RSA` or `CMS` defults to `RSA` if ommited
* `backend=<backend-type>` - backend can be pkcs11 or ssl, defaults to ssl if ommitted
* `key-uri=<pkcs11 key uri>` - key uri required for `backend=pkcs11`
* `cert-uri=<pkcs11 key uri>` - key uri required for `backend=pkcs11` & `method=CMS`

Response: a `sw-description` file with signatures inserted

Example client: [swupdatesign.bbclass](https://github.com/madisongh/tegra-test-distro/blob/master/layers/meta-testdistro/classes/swupdatesign.bbclass)
