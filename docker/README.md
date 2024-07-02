# Overview

The [Dockerfile](Dockerfile) uses docker's multi-stage builds to support one or more L4T releases and Jetson modules.  It captures the requirements as documented [here](../doc/tegrasign.md).  There is a `Dockerfile` for each supported L4T release.  Add additional `Dockerfile`s for L4T releases and modules you need (PRs welcome).  Locally comment out the L4T releases and modules not needed by your signing server.

# Building

From the top-level of the `digsigserver` repo build the L4T release container images for the releases you want to support.  Example:

```
docker build . -f docker/Dockerfile.l4t-32.7.4 -t l4t-release:32.7.4
docker build . -f docker/Dockerfile.l4t-35.4.1 -t l4t-release:35.4.1
```

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

```
docker build . -f docker/Dockerfile -t digsigserver:latest
```

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
--mount type=bind,source=$HOME/$SIGNING_KEYS/oemk1.key,target=/digsigserver/$MACHINE/ekbsign/oemk1.key,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/fixed-vector,target=/digsigserver/$MACHINE/ekbsign/fixed-vector,readonly \
--mount type=bind,source=$HOME/$SIGNING_KEYS/uefi-variable-authentication.key,target=/digsigserver/$MACHINE/ekbsign/uefi-variable-authentication.key,readonly \
-p 9999:9999 \
digsigserver:latest
```
For NXP i.MX, the file containing your keys should be located in the home directory of the account used to run the containerized signing server.  
Modify the mount point(s) to mount the keys as per the [Key file storage layout](../doc/imxsign.md#Keyfile-storage-layout), for example 
if MACHINE=imx8mp and you are only doing i.MX signing :
```
docker run \
--restart unless-stopped \
-p 9999:9999 \
--mount type=bind,source=$HOME/imx-cst-keys.tar.gz,target=/digsigserver/imx8mp/imxsign/imx-cst-keys.tar.gz,readonly \
digsigserver:latest
```

For Rockchip, the machine-specific key directory should be mounted to `/digsigserver/${machine}` per the [Key file storage layout](../doc/rksign.md#Keyfile-storage-layout), for example :
```
$HOME/mymachine/
└── rksign
    ├── dev.crt
    ├── dev.key
    └── dev.pubkey
```
```
docker run \
--restart unless-stopped \
-p 9999:9999 \
--mount type=bind,source=$HOME/mymachine,target=/digsigserver/mymachine,readonly \
digsigserver:latest
```

# i.MX Signing with YubiHSM 2 hardware token

See [i.MX Signing Using a YubiHSM 2 Hardware Token](../doc/imxsign-yubihsm.md) for details on how to set up the YubiHSM 2 
and invoke the server.

## Building

A separate dockerfile called Dockerfile.nxp-hsm is included here as it adds a lot of stuff to support pkcs11 and the YubiHSM 2 which 
is not required if you are only doing Tegra signing, or i.MX signing using the keys/certs on the filesystem.

The dockerfile pulls in any archives placed in nxp_tools and set these up. For example the archives *nxp_tools/cst-3.3.1.tgz* 
and *nxp_tools/IMX_CST_TOOL_NEW.tgz* will result in version 3.3.1 and 3.3.2 of cst being made available for the imx signing endpoint.

To build the image :

    docker build . -f docker/Dockerfile.nxp-hsm -t digsigserver-nxp-hsm:latest

## Running

For i.MX signing with the YubiHSM 2, the imx-cst-keys.tar.gz file only needs to contain the crts/SRK_table_1_2_3_4.bin file. The USB bus 
must be shared with the host. Also the YUBIHSM_PASSWORD environment variable is set to the password set for the YubiHSM 2 with the prefix "0001" 
as this is the object id of the authentication object that pkcs11 uses to authenticate whith the token. So if the YubiHSM 2 password is 
"password" and MACHINE is imx8mp, then the signing server would be started as follows :

docker run -d \
  --restart unless-stopped \
  --privileged -v /dev/bus/usb:/dev/bus/usb \
  --env "YUBIHSM_PASSWORD=0001password" \
  -p 9999:9999 \
  --mount type=bind,source=$HOME/imx-cst-keys.tar.gz,target=/digsigserver/imx8mp/imxsign/imx-cst-keys.tar.gz,readonly \
  digsigserver-nxp-hsm:latest


