# Overview

The [Dockerfile](Dockerfile) uses docker's multi-stage builds to support one or more L4T releases and Jetson modules.  It captures the requirements as documented [here](../doc/tegrasign.md).  There is a `Dockerfile` for each supported L4T release.  Add additional `Dockerfile`s for L4T releases and modules you need (PRs welcome).  Locally comment out the L4T releases and modules not needed by your signing server.

# Building

From the top-level of the `digsigserver` repo build the L4T release container images for the releases you want to support.  Example:

    $ docker build . -f docker/Dockerfile.l4t-32.7.4 -t l4t-release:32.7.4
    $ docker build . -f docker/Dockerfile.l4t-35.4.1 -t l4t-release:35.4.1

Include the approriate `FROM` and `COPY` statements in your `Dockerfile`.  Example:

```
FROM l4t-release:32.7.4 AS l4t-32.7.4
FROM l4t-release:35.4.1 AS l4t-35.4.1
```

```
COPY --from=l4t-32.7.4 /opt/nvidia /opt/nvidia
COPY --from=l4t-35.4.1 /opt/nvidia /opt/nvidia
```

Then build the signing server container image:

    $ docker build . -f docker/Dockerfile -t digsigserver:latest

# Running

The following script fragment is helpful to setup the mount points to the keys according to the following key file storage layouts:

* [tegra signing](../doc/tegrasign.md#Key-file-storage-layout)
* [tegra uefi signing](../doc/uefisign.md#key-file-storage-layout)
* [tegra uefi capsule signing](../doc/ueficapsulesign.md#key-file-storage-layout)

```
export SIGNING_KEYS=/path/to/signing-keys
export MACHINE=[jetson-xavier-nx-devkit-emmc|jetson-agx-orin-devkit|etc.]

docker run -d \
--restart unless-stopped \
--mount type=bind,source=$HOME/$SIGNING_KEYS/rsa_priv.pem,target=/digsigserver/$MACHINE/tegrasign/rsa_priv.pem,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/db_1.key,target=/digsigserver/$MACHINE/uefisign/db.key,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/db_1.crt,target=/digsigserver/$MACHINE/uefisign/db.crt,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/NewRoot.pub.pem,target=/digsigserver/$MACHINE/ueficapsulesign/trusted_public_cert.pem,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/NewSub.pub.pem,target=/digsigserver/$MACHINE/ueficapsulesign/other_public_cert.pem,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/NewCert.pem,target=/digsigserver/$MACHINE/ueficapsulesign/signer_private_cert.pem,readonly \
-p 9999:9999 \
digsigserver:latest
```
