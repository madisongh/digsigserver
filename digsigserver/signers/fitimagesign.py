import os
import copy
from typing import Optional
from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class FitImageSigner (Signer):

    keytag = 'fitimagesign'

    def __init__(self, app: Sanic, workdir: str):
        super().__init__(app, workdir, "imx")

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
             keyname: str = "dev.key") -> bool:
        private_key = self.keys.get("{}.key".format(keyname))
        env = self._prepare_path()
        cmd = [ 'mkimage', '-F', '-k', os.path.dirname(private_key) ]
        if external_data_offset != None:
            cmd += [ '-p', external_data_offset ]
        if mark_required != None:
            cmd += [ '-r' ]
        if dtb != None:
            cmd += [ '-K', dtb ]
        if algo != None:
            cmd +=[ '-o', algo ]

        cmd += [ fitimage ]
        result = self.run_command(cmd, env=env)
        self.keys.cleanup()
        return result
