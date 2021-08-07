import os
import shutil
from digsigserver.signers import Signer
from digsigserver import utils


class MenderSigner(Signer):

    keytag = 'mender'

    def __init__(self, workdir: str, distro: str, artifact_uri: str):
        signcmd = shutil.which('mender-artifact')
        if not signcmd:
            raise RuntimeError('no mender-artifact command')
        self.signcmd = signcmd
        if not utils.uri_exists(artifact_uri):
            raise RuntimeError('cannot access artifact {}'.format(artifact_uri))
        self.artifact_uri = artifact_uri
        super().__init__(workdir, distro)

    def sign(self) -> bool:
        privkey = self.keys.get('private.key')
        if not privkey:
            raise RuntimeError('key missing for mender signing')
        file = os.path.join(self.workdir, 'unsigned.mender')
        utils.uri_fetch(self.artifact_uri, file)
        cmd = [self.signcmd, 'sign', file, '-k', privkey,
               '-o', os.path.join(self.workdir, 'signed.mender')]
        if self.run_command(cmd):
            utils.upload_file(os.path.join(self.workdir, 'signed.mender'), self.artifact_uri)
            return True
        return False
