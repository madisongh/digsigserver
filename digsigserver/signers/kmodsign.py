import os
import re
from digsigserver.signers import Signer


class KernelModuleSigner(Signer):

    keytag = 'kmodsign'

    def __init__(self, workdir: str, machine: str, hashalg: str):
        signcmd = os.path.join('/usr', 'src', 'linux-headers-{}'.format(os.uname().release),
                               'scripts', 'sign-file')
        if not os.path.exists(signcmd):
            raise RuntimeError('cannot find {} for module signing'.format(signcmd))
        self.signcmd = signcmd
        if not re.match(r'sha(256|384|512)$', hashalg):
            raise ValueError('unrecognized hash algorithm: {}'.format(hashalg))
        self.hashalg = hashalg
        super().__init__(workdir, machine)

    def sign(self) -> bool:
        privkey = self.keys.get('kernel-signkey.priv')
        pubkey = self.keys.get('kernel-signkey.x509')
        if not privkey or not pubkey:
            raise RuntimeError('key missing for module signing')

        for dirpath, _, filenames in os.walk(self.workdir):
            for file in filenames:
                if file.endswith('.ko'):
                    cmd = [self.signcmd, self.hashalg, privkey, pubkey, os.path.join(dirpath, file)]
                    if not self.run_command(cmd, cleanup=False):
                        self.keys.cleanup()
                        return False
        self.keys.cleanup()
        return True
