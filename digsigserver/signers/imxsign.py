import os
import copy
from digsigserver.signers import Signer
from digsigserver import server

from sanic.log import logger


def bsp_tools_path(cstversion: str) -> str:
    toolspath = os.path.join(server.config_get('IMX_CST_BASE'),
                             'cst-{}'.format(cstversion),
                             'linux64', 'bin')
    return toolspath if os.path.exists(toolspath) else None


class IMXSigner (Signer):

    keytag = 'imxsign'
    supported_soctypes = ['mx8m']

    def __init__(self, workdir: str, machine: str, soctype: str, cstversion: str):
        logger.debug("machine: {}, soctype: {}, bspversion: {}".format(machine, soctype, cstversion))
        if soctype not in self.supported_soctypes:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = bsp_tools_path(cstversion)
        if self.toolspath is None:
            raise ValueError("no tools available for cstversion={}".format(cstversion))
        self.soctype = soctype
        self.machine = machine
        super().__init__(workdir, machine)

    def _prepare_path(self) -> dict:
        env = dict(copy.deepcopy(os.environ))
        curpath = env.get('PATH')
        env['PATH'] = self.toolspath
        if curpath:
            env['PATH'] += ':' + curpath
        return env

    def sign(self, outfile: str) -> bool:
        tarball = self.keys.get('imx-cst-keys.tar.gz')
        # Unpack the keys/certs, CSFs sent to us will have relative paths for the names
        if self.run_command(['tar', '-C', self.workdir, '-x', '-f', tarball]):
            env = self._prepare_path()
            # Generate the binary CSF with signatures
            if self.run_command(['cst', '-i', 'csf-input.txt', '-o', outfile], env=env):
                self.keys.cleanup()
                return True
        self.keys.cleanup()
        return False
