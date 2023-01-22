# Mender artifact signing

## Prerequisites
For Mender artifact signing, you must have the `mender-artifact` tool available
in the PATH.  Visit [the Mender documentation pages](https://docs.mender.io) and
go to the "Downloads" section to find a download of a pre-built copy of this tool,
or follow the instructions there for building it from source.  Installing it in
`/usr/local/bin` should make it available.

## Key file storage layout
For Mender artifacts, the signing key is expected to be at

    ${DIGSIGSERVER_KEYFILE_URI}/${distro}/mender/private.key

where `${distro}` is the value of the `distro=` parameter included in the signing request.

## REST API endpoint

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
