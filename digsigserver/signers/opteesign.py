import os
import pathlib
from digsigserver.signers import Signer
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import utils
from uuid import UUID
import struct
import math

from sanic import Sanic
from sanic.log import logger

SHDR_BOOTSTRAP_TA = 1
SHDR_ENCRYPTED_TA = 2
SHDR_MAGIC = 0x4f545348
SHDR_SIZE = 20
algorithms = {'TEE_ALG_RSASSA_PKCS1_PSS_MGF1_SHA256': 0x70414930,
              'TEE_ALG_RSASSA_PKCS1_V1_5_SHA256': 0x70004830}


def _sign_ta(img: bytes, dirpath: str, uuid: str,
             ta_version: str, key: rsa.RSAPrivateKey) -> bool:
    chosen_hash = hashes.SHA256()
    h = hashes.Hash(chosen_hash)

    digest_len = chosen_hash.digest_size
    sig_len = math.ceil(key.key_size / 8)
    algo = algorithms['TEE_ALG_RSASSA_PKCS1_PSS_MGF1_SHA256']
    shdr = struct.pack('<IIIIHH',
                       SHDR_MAGIC, SHDR_BOOTSTRAP_TA, len(img),
                       algo, digest_len, sig_len)
    shdr_uuid = UUID(uuid).bytes
    shdr_version = struct.pack('<I', int(ta_version, 0))
    h.update(shdr)
    h.update(shdr_uuid)
    h.update(shdr_version)
    h.update(img)
    img_digest = h.finalize()
    sig = key.sign(
        img_digest,
        padding.PSS(
            mgf=padding.MGF1(chosen_hash),
            salt_length=digest_len
        ),
        utils.Prehashed(chosen_hash)
    )
    with open(os.path.join(dirpath, uuid + ".ta"), 'wb') as f:
        f.write(shdr)
        f.write(img_digest)
        f.write(sig)
        f.write(shdr_uuid)
        f.write(shdr_version)
        f.write(img)
    return True

def find_signing_inputs(filenames: list) -> tuple:
    img_file_name = img_file_base = uuid_file = taversion_file = None
    for f in filenames:
        p = pathlib.Path(f)
        p_ext = "".join(p.suffixes)
        if p_ext in [".stripped.elf", ".stripped.so"]:
            img_file_name = f
        elif p_ext == ".uuid":
            uuid_file = f
        elif p_ext == ".ta-version":
            taversion_file = f
        else:
            logger.warning("unrecognized input file: {}".format(f))
    return img_file_name, img_file_base, uuid_file, taversion_file


class OPTEESigner (Signer):

    keytag = 'opteesign'

    def __init__(self, app: Sanic, workdir: str, machine: str):
        logger.debug("machine: {}".format(machine))
        self.machine = machine
        super().__init__(app, workdir, machine)

    def sign(self) -> bool:
        keyfile = self.keys.get('optee-signing-key.pem')
        with open(keyfile, 'rb') as f:
            data = f.read()
            try:
                key = serialization.load_pem_private_key(data, password=None)
            except ValueError:
                logger.error("could not parse RSA private key")
                self.keys.cleanup()
                return False
            if not isinstance(key, rsa.RSAPrivateKey):
                logger.error("signing key is not an RSA private key")
                self.keys.cleanup()
                return False
        for dirpath, _, filenames in os.walk(self.workdir):
            img_file, img_basename, uuid_file, ta_version_file = find_signing_inputs(filenames)
            if img_file is None:
                logger.info("nothing to sign in {}".format(dirpath))
                continue
            to_remove = filenames
            with open(os.path.join(dirpath, img_file), 'rb') as f:
                img = f.read()
            if uuid_file is None:
                logger.warning("uuid file missing, using {}".format(img_basename))
                uuid = img_basename
            else:
                with open(os.path.join(dirpath, uuid_file), "r") as f:
                    uuid = f.readline().rstrip()
            if ta_version_file is None:
                logger.warning("ta-version file missing, using 0")
                ta_version = "0"
            else:
                with open(os.path.join(dirpath, ta_version_file), "r") as f:
                    ta_version = f.readline().rstrip()
            if not _sign_ta(img, dirpath, uuid, ta_version, key):
                logger.warning("Failed to sign TA for UUID {}".format(uuid))
                self.keys.cleanup()
                return False
            logger.debug("Removing: {}".format(to_remove))
            for fname in to_remove:
                os.remove(os.path.join(dirpath, fname))
            if os.path.exists(os.path.join(dirpath, uuid + ".ta")):
                logger.info("Signed: {} -> {}.ta".format(img_file, uuid))
            else:
                logger.warning("TA signing for {} successful, but {}.ta file is missing".format(img_file, uuid))
        self.keys.cleanup()
        return True
