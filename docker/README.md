# Overview

The [Dockerfile](Dockerfile) currently has support for a limited number of L4T releases and Jetson modules.  It captures the requirements as documented [here](../doc/tegrasign.md).  Modify it to include the L4T releases and modules you need (PRs welcome).  Locally comment out the L4T releases and modules not needed by your signing server.

# Building

From the top-level of the `digsigserver` repo:

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
