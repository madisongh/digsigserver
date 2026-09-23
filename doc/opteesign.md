# Signing OP-TEE Trusted Applications

This signer implements a subset of the functions in the `sign_encrypt.py` script
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

## Example client

Patch the `sign_encrypt.py`  to create the files needed for off-line signing, similar
to this example from a 4.10.0-based OP-TEE OS source base:
```diff
--- a/scripts/sign_encrypt.py
+++ b/scripts/sign_encrypt.py
@@ -840,12 +840,28 @@ def load_ta_image(args):
 
 
 def command_sign_enc(args):
+    import base64
+    import os
+    import struct
+    import uuid
+
     ta_image = load_ta_image(args)
     if args.subkey:
         ta_image.add_subkey(args.subkey, args.name)
     ta_image.sign()
     ta_image.write(args.outf)
+    outf_base, _ = os.path.splitext(args.outf)
     logger.info('Successfully signed application.')
+    # And save uuid and ta-version files to allow for
+    # off-line signing without having to make drastic
+    # changes to the build system
+    with open(outf_base + '.uuid', 'w+') as f:
+         print("{}".format(uuid.UUID(bytes=ta_image.ta_uuid)), file=f)
+    with open(outf_base + '.ta-version', 'w+') as f:
+        [ta_version] = struct.unpack('<I', ta_image.ta_version)
+        print("{}".format(ta_version), file=f)
```

Once the compilation is finished, the client can collect up the `.stripped.elf`,
`.stripped.so` (for shared library TAs), `.uuid`, and `.ta-version`
files into a tarball and send them to the signer. If signing is successful, the output tarball
contains the signed `.ta` files.

```bash
    find ta -type f '-(' -name '*.stripped.*' -o -name '*.uuid' -o -name '*.ta-version' '-)' | sort | xargs tar -c -z -f ${B}/tasign-in.tar.gz
    find ta -type f -name '*.ta' -delete
    curl ${DIGSIG_URL}/sign/optee --silent --show-error --fail -X POST -F "machine=${DIGSIG_MACHINE}" -F"artifact=@${B}/tasign-in.tar.gz" --output ${B}/tasign-out.tar.gz
    tar -x -f ${B}/tasign-out.tar.gz
```
