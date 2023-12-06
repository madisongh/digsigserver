# i.MX Signing Using a YubiHSM 2 Hardware Token

This document describes the steps required to configure a build and remote
signing server such that local builds can be signed with a remote YubiHSM 2
key. The document also describes how the fuses of the FB5 should be flashed.


## HAB4 PKI

It is assumed that the HAB4 PKI tree has already been generated.

For signing imx firmware images, the signing server expects a file
called imx-cst-keys.tar.gz to be present in directory
/digsigserver/{machine}/imxsign of the container's filesystem. When the YubiHSM
is used for signing, the only file required to be in imx-cst-keys.tar.gz is
crts/SRK_1_2_3_4_table.bin
.
Then assuming that we are only using SRK1 for secure boot, the YubiHSM is used to
store the CSF1_1 and IMG1_1 certificates and private keys (instructions follow).

## Run the Docker Image to Set Up the YubiHSM

Since the docker image contains all the support for the YubiHSM already, the
easiest way to prepare the YubiHSM is from a container running this image. The
required keys and certificates must be made avaiable to the container, so assuming
they are in a directory imx_keys below your home directory, then the container
would be started as follows :
```
docker run \
--rm \
-it \
--privileged -v /dev/bus/usb:/dev/bus/usb \
-v ~/imx_keys:/opt/imx_keys \
digsigserver-nxp-hsm:latest /bin/bash
```

The line '-v ~/imx_keys:/opt/imx_keys' shares your directory ~/imx_keys with the
container and it will be at /opt/imx_keys from within the container.

The --rm option means that the container is removed after exiting. Without this
option, an image of the running container is saved every time you exit from it and
so if you run the docker image many times this can use up a great deal of disk space.
With the --rm option, any changes that you make to the container's filesystem (except
for directories shared with the host) are lost when you exit.

The line '--privileged -v /dev/bus/usb:/dev/bus/usb' gives the docker container access
to the host USB bus which is required in order for the container to be able to use the
YubiHSM.


## Set the YubiHSM password

The YubiHSM 2 stores everything as an Object which has an Object ID. Objects may also
be assigned text labels by which to refer to them. Objects can be things like private
keys and certificates. There are also authentication objects which are used to grant
access to other objects. When new, or after a factory reset, the YubiHSM contains a
single authentication object with Object ID 0001 which allows you to access the YubiHSM,
and this is set to a default password of "password". So to access sensitive objects on
the token such as private keys, you need to authenticate with object 0001 first using
the password.

When the container is started with the command /bin/bash, the "yubihsm connector"
software needs to be started manually to enable the yubihasm utilities to access the
YubiHSM, this is done by running "yubihsm-connector start" from the command line.

The yubihsm-shell utility can be used to change the password. Say you want to change
the password from the default "password" to "newpassword" :
```
root@acb68063238f:/opt/imx_keys# yubihsm-connector start
root@acb68063238f:/opt/imx_keys# yubihsm-shell
Using default connector URL: http://localhost:12345
yubihsm> connect
Session keepalive set up to run every 15 seconds
yubihsm> session open 0001 password
Created session 0
yubihsm> change authkey 0 0001 newpassword
Changed Authentication key 0x0001
yubihsm> session close 0
yubihsm> exit
root@acb68063238f:/opt/imx_keys#
```

In the above sequence, "connect" opens a connection to the YubiHSM via the
yubihsm-connector. In the "session open" command, 0001 (or you use just 1 instead) is the
object id of the authentication object to use and password is the password for that object,
and the session id 0 is returned which is used in subsequent commands.

## Store keys and certificates on the YubiHSM

As well as the yubihsm utilities provided by Yubico, the docker image also contains various
OpenSC utilities such as pkcs11-tool which can be used to access the YubiHSM. In this case
we will use pkcs11-tool in order to store the required certificates and keys on the YubiHSM.

### Decrypt the private keys

In the container, the private keys are in the directory /opt/imx_keys/keys which is shared
with the host (see the 'docker run' command above), and since the keys are stored encrypted,
we need to decrypt them first before writing them to the YubiHSM. The password for the
encryption is in the keys/key_pass.txt file (two copies of the password on two lines). Run
the following commands from the keys directory to decrypt the CSF1_1 and IMG1_1 private keys:

```
openssl rsa -in IMG1_1_sha256_4096_65537_v3_usr_key.der -out IMG1_1_key.der
openssl rsa -in CSF1_1_sha256_4096_65537_v3_usr_key.der -out CSF1_1_key.der
```

Each time you will be prompted for the password.

### Store keys and certificates on the YubiHSM

From the /opt/imx_keys directory, export the following environment variables for use with
the pkcs11-tool commands that will be used afterwards:
```
export USR_PIN=0001password
export IMG1_KEY=IMG1_1_sha256_4096_usr
export CSF1_KEY=CSF1_1_sha256_4096_usr
```

For USR_PIN, "0001password" should be replaced with "0001" followed immediately by
the password you set to access the YubiHSM. The "0001" prefix is the object id of the
authenication object used, and this prefix is required by pkcs11-tool.

IMG1_KEY and CSF1_KEY are labels that are used to access the keys or certificates rather
than using explicit object ids. Note that whatever labels you actually use need to be
specified in the CSF files used in the signing process.

Now write the keys and certificates to the YubiHSM from the /opt/imx_keys directory as followss :

```
pkcs11-tool --module $PKCS11_MODULE -l --write-object keys/CSF1_1_key.der --type privkey --usage-sign --label $CSF1_KEY --id 1002 --pin $USR_PIN
pkcs11-tool --module $PKCS11_MODULE -l --write-object keys/IMG1_1_key.der --type privkey --usage-sign --label $IMG1_KEY --id 1003 --pin $USR_PIN
pkcs11-tool --module $PKCS11_MODULE -l --write-object crts/CSF1_1_sha256_4096_65537_v3_usr_crt.der --type cert --label $CSF1_KEY --id 1002 --pin $USR_PIN
pkcs11-tool --module $PKCS11_MODULE -l --write-object crts/IMG1_1_sha256_4096_65537_v3_usr_crt.der --type cert --label $IMG1_KEY --id 1003 --pin $USR_PIN
```

Note that the CSF1_1 key and certificate are given the same label and object id which is
ok as they are different object types. Similarly for the IMG1_1 key and certificate.

Note that when a private key is written to the YubiHSM, it automatically extracts the
public key and creates a public key object with the same object id and label.

### List objects stored on the YubiHSM

Check that everything looks good by running the pkcs11-tool --list-objects command:

```
pkcs11-tool --module $PKCS11_MODULE -l --pin $USR_PIN --list-objects
```
The output should look similar to this :
```

Using slot 0 with a present token (0x10)
Private Key Object; RSA
  label:      IMG1_1_sha256_4096_usr
  ID:         1003
  Usage:      sign
Public Key Object; RSA 4096 bits
  label:      IMG1_1_sha256_4096_usr
  ID:         1003
  Usage:      verify
Private Key Object; RSA
  label:      CSF1_1_sha256_4096_usr
  ID:         1002
  Usage:      sign
Public Key Object; RSA 4096 bits
  label:      CSF1_1_sha256_4096_usr
  ID:         1002
  Usage:      verify
Certificate Object; type = X.509 cert
  label:      IMG1_1_sha256_4096_usr
  ID:         1003
Certificate Object; type = X.509 cert
  label:      CSF1_1_sha256_4096_usr
  ID:         1002
```

### Exit from the container

Now that the YubiHSM has been prepared, exit from the container wirh 'exit'.
The container is run using a different 'docker run' command when it is used to
run the signing server.

## Prepare the imx-cst-keys.tar.gz file

As mentioned previously, this file is used by the signing server, and with the
'docker run' command used to start the signing server, it is expected to be in
the user's home directory. When the signing server is using the YubiHSM, only
the crts/SRK_1_2_3_4_table.bin is required to be present in file. One way to 
create this file in your home directory might be as follows, assuming that your 
HAB4 PKI files are in directory ~/imx_keys :
```
cd ~
mkdir -p ~/tmp/imx_keys/crts
cp ./imx_keys/crts/SRK_1_2_3_4_table.bin ./imx_keys/crts/SRK_1_2_3_4_fuse.bin ./tmp/imx_keys/crts/
tar czf imx-cst-keys.tar.gz -C tmp/imx_keys .
```

Note the '.' at the end of the tar command.

## Run the Signing Server

The signing server can be run using the following command :
```
docker run \
  --restart unless-stopped \
  --privileged -v /dev/bus/usb:/dev/bus/usb \
  --env "YUBIHSM_PASSWORD=0001password" \
  -p 9999:9999 \
  --mount type=bind,source=$HOME/imx-cst-keys.tar.gz,target=/digsigserver/{machine}/imxsign/imx-cst-keys.tar.gz,readonly \
  digsigserver-nxp-hsm:latest
```
Note the {machine} placeholder identifies your hardware, for example it would normally be 
set to the MACHINE variable in a yocto build.

The environment variable YUBIHSM_PASSWORD is used by the signing server to login to
the YubiHSM. As mentioned before, the 0001 prefix is required by pkcs11, and this is
immediately followed by the actual password.

Also, when there is no command at the end of the 'docker run' command, the default
command given in the dockerfile is run, in this case
'yubihsm-connector start && digsigserver --debug'.

## Required Changes to CSF Files

In this case the Code Signing Tool running on the server will use the pkcs11 backend to
use the keys which are kept on the token and the csf files should be modified to indicate
that the keys are on the token rather than on the filesystem. So replace the following :
```
File = "crts/CSF1_1_sha256_4096_65537_v3_usr_crt.pem"
```
with
```
File = "pkcs11:token=YubiHSM;object=CSF1_1_sha256_4096_usr;type=cert;pin-value=password"
```
And similarly, replace the following :
```
File = "crts/IMG1_1_sha256_4096_65537_v3_usr_crt.pem"
```
with
```
File = "pkcs11:token=YubiHSM;object=IMG1_1_sha256_4096_usr;type=cert;pin-value=password"
```
Note that "password" in the "pin-value=password" field is just a placeholder as this will be
replaced with the actual password on the server, the server searches for this string so setting
this field to anything else will fail.

The names CSF1_1_sha256_4096_usr and IMG1_1_sha256_4096_usr are the labels used to access the
CSF1_1 and IMG1_1 keys on the token.

## Manual Signing

Normally the signing server would be called during the image creation phase of some kind 
of build system, e.g. yocto. So for example, in a yocto build, the recipe responsible for 
signing the image might use curl to invoke the server's /sign/imx endpoint, and assuming 
the recipe might make a call like this including the "backend=pkcs11" parameter :
```
curl --connect-timeout 30 --max-time 1800 --retry 4 --silent --fail \
     -X POST -F machine=imx -F soctype=mx8m -F cstversion=3.3.2 -F backend=pkcs11 \
     -F "csf=@${HOME}/imx-cst-keys/flash_evk-csf-fit.csf;type=text/plain" \
     -F "artifact=@${HOME}/imx-cst-keys/imx-boot-${MACHINE}-sd.bin-flash_evk" \
     --output ${HOME}/imx-cst-keys/flash_evk-csf-fit.bin \
     http://172.17.0.1:9999/sign/imx
```


