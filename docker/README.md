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

Your private key should be located in the home directory of the account used to run the containerized signing server.  Modify the mount point(s) to mount the PKC private key per the [Key file storage layout](../doc/tegrasign.md#Key-file-storage-layout).

```
docker run -d \
--restart unless-stopped \
--mount type=bind,source=$HOME/rsa_priv.pem,target=/work/{machine}/tegrasign/rsa_priv.pem,readonly \
-p 9999:9999 \
digsigserver:latest
```
