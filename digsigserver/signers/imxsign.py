import os
import copy
from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class IMXSigner (Signer):

    keytag = 'imxsign'
    supported_soctypes = ['mx8m']

    def __init__(self, app: Sanic, workdir: str, machine: str, soctype: str, cstversion: str, backend: str):
        logger.debug("machine: {}, soctype: {}, bspversion: {}, backend: {}".format(machine, soctype, cstversion, backend))
        if soctype not in self.supported_soctypes:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = os.path.join(app.config.get('IMX_CST_BASE'),
                                      'cst-{}'.format(cstversion),
                                      'linux64', 'bin')
        if not os.path.exists(self.toolspath):
            raise ValueError("no tools available for cstversion={}".format(cstversion))
        self.soctype = soctype
        self.machine = machine
        self.backend = backend
        super().__init__(app, workdir, machine)

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
            command = ['cst', '-i', 'csf-input.txt', '-o', outfile]
            if self.backend == "pkcs11":
                command.extend(['-b', 'pkcs11'])
                cst_path = os.path.join(self.workdir, "csf-input.txt")
                content = ""
                with open(cst_path, "r") as f:
                    content = f.read()
                with open(cst_path, "w") as f:
                    new_content = content.replace("pin-value=password", "pin-value=" + os.environ.get('YUBIHSM_PASSWORD'))
                    f.write(new_content)
            if self.run_command(command, env=env):
                self.keys.cleanup()
                return True
        self.keys.cleanup()
        return False
