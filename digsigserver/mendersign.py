import os
import shutil
import subprocess
from .keyfiles import KeyFiles
from . import utils

from sanic.log import logger


class MenderSigner:
    def __init__(self, distro: str, artifact_uri: str):
        signcmd = shutil.which('mender-artifact')
        if not signcmd:
            raise RuntimeError('no mender-artifact command')
        self.signcmd = signcmd
        if not utils.uri_exists(artifact_uri):
            raise RuntimeError('cannot access artifact {}'.format(artifact_uri))
        self.artifact_uri = artifact_uri
        self.keys = KeyFiles('mender', distro)

    def sign(self, workdir: str) -> bool:
        privkey = self.keys.get('private.key')
        if not privkey:
            raise RuntimeError('key missing for mender signing')
        file = os.path.join(workdir, 'unsigned.mender')
        utils.uri_fetch(self.artifact_uri, file)
        cmd = [self.signcmd, 'sign', file, '-k', privkey,
               '-o', os.path.join(workdir, 'signed.mender')]
        try:
            logger.info("Running: {}".format(cmd))
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=workdir,
                                  check=True, capture_output=True,
                                  encoding='utf-8')
            logger.debug("stdout: {}".format(proc.stdout))
            logger.debug("stderr: {}".format(proc.stderr))
        except subprocess.CalledProcessError as e:
            self.keys.cleanup()
            logger.warning("signing error: {}".format(e.stderr))
            return False
        utils.upload_file(os.path.join(workdir, 'signed.mender'), self.artifact_uri)
        self.keys.cleanup()
        return True
