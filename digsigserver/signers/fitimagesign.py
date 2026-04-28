import os
import copy
from typing import Optional
from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger

class FitImageSigner (Signer):

    keytag = 'fitimagesign'

    def __init__(self, app: Sanic, workdir: str, backend: str):
        super().__init__(app, workdir, 'imx', backend, load_keys=backend != 'pkcs11')

    def _prepare_path(self) -> dict:
        env = dict(copy.deepcopy(os.environ))
        curpath = env.get('PATH')
        if curpath:
            env['PATH'] += ':' + curpath
        return env

    def sign(self, fitimage: str,
             dtb: Optional[str],
             external_data_offset: Optional[str],
             mark_required: Optional[bool],
             algo: Optional[str],
             keyname: str = "dev",
             comment: Optional[str] = None) -> bool:
        env = self._prepare_path()
        if self.backend == "pkcs11":
            keyname = keyname.replace('pin-value=password', 'pin-value=' + self.app.config.get('YUBIHSM_PASSWORD'))
            cmd = ['mkimage', '-E', '-F', '-N', 'pkcs11', '-k', keyname, '-v']
        else:
            private_key = self.keys.get("{}.key".format(keyname))
            cmd = ['mkimage', '-F', '-k', os.path.dirname(private_key)]

        if comment:
            cmd += ['-c', comment]
        if external_data_offset:
            cmd += ['-p', external_data_offset]
        if mark_required:
            cmd += ['-r']
        if dtb:
            cmd += ['-K', dtb]
        if algo:
            cmd += ['-o', algo]

        cmd += [fitimage]
        result = self.run_command(cmd, env=env)
        return result
