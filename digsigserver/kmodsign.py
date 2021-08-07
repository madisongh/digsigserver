import os
import re
import subprocess
from .keyfiles import KeyFiles

from sanic.log import logger


class KernelModuleSigner:
    def __init__(self, machine: str, hashalg: str, workdir: str):
        self.workdir = workdir
        # noinspection PyUnresolvedReferences
        signcmd = os.path.join('/usr', 'src', 'linux-headers-{}'.format(os.uname().release),
                               'scripts', 'sign-file')
        if not os.path.exists(signcmd):
            raise RuntimeError('cannot find {} for module signing'.format(signcmd))
        self.signcmd = signcmd
        self.keys = KeyFiles('kmodsign', machine)
        if not re.match(r'sha(256|384|512)$', hashalg):
            raise ValueError('unrecognized hash algorithm: {}'.format(hashalg))
        self.hashalg = hashalg

    def sign(self) -> bool:
        privkey = self.keys.get('kernel-signkey.priv')
        pubkey = self.keys.get('kernel-signkey.x509')
        if not privkey or not pubkey:
            raise RuntimeError('key missing for module signing')

        for dirpath, _, filenames in os.walk(self.workdir):
            for file in filenames:
                if file.endswith('.ko'):
                    cmd = [self.signcmd, self.hashalg, privkey, pubkey, os.path.join(dirpath, file)]
                    try:
                        logger.info("Running: {}".format(cmd))
                        proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=self.workdir,
                                              check=True, capture_output=True,
                                              encoding='utf-8')
                        logger.debug("stdout: {}".format(proc.stdout))
                        logger.debug("stderr: {}".format(proc.stderr))
                    except subprocess.CalledProcessError as e:
                        self.keys.cleanup()
                        logger.warning("signing error: {}".format(e.stderr))
                        return False
        self.keys.cleanup()
        return True
