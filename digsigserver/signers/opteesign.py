import os
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


# Abridged version of scripts/sign_encrypt.py in optee-os
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
            for file in filenames:
                if file.endswith(".stripped.elf"):
                    with open(os.path.join(dirpath, file), 'rb') as f:
                        img = f.read()
                    uuid = file[:-len(".stripped.elf")]
                    try:
                        with open(os.path.join(dirpath, uuid + ".ta-version"), "r") as f:
                            ta_version = f.readline().rstrip()
                    except FileNotFoundError:
                        logger.warning("ta-version file missing for {}".format(uuid))
                        ta_version = "0"
                    if not _sign_ta(img, dirpath, uuid, ta_version, key):
                        self.keys.cleanup()
                        return False
                    os.remove(os.path.join(dirpath, file))
                    os.remove(os.path.join(dirpath, uuid + ".ta-version"))
                    if not os.path.exists(os.path.join(dirpath, uuid + ".ta")):
                        logger.warning("TA signing succesful, but {}.ta file is missing".format(uuid))
        self.keys.cleanup()
        return True
