import os
import copy
import shutil

from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class RockchipOpteeSigner (Signer):

    keytag = 'rkopteesign'
    tools = ['change_puk', 'resign_ta.py']

    def __init__(self, app: Sanic, workdir: str, machine: str):
        logger.debug("{}: machine: {}".format(self.__class__.__name__, machine))
        self.toolspath = app.config.get('RK_TOOLS_PATH')
        if not os.path.exists(self.toolspath):
            logger.error("RK_TOOLS_PATH({}) not found".format(self.toolspath))
            raise ValueError("no tools available")
        for tool in self.tools:
            if not os.path.exists(os.path.join(self.toolspath, tool)):
                logger.error("{} not found in RK_TOOLS_PATH".format(tool))
                raise ValueError("missing required tool '{}' in ".format(tool, self.toolspath))
        self.machine = machine
        super().__init__(app, workdir, machine)

    def _prepare_path(self) -> dict:
        env = dict(copy.deepcopy(os.environ))
        curpath = env.get('PATH')
        env['PATH'] = self.toolspath
        if curpath:
            env['PATH'] += ':' + curpath
        return env

    def resign_tee(self, infile: str, outfile: str) -> bool:
        public_key = self.keys.get('optee-signing-pubkey.pem')
        env = self._prepare_path()
        result = self.run_command(['change_puk', '--teebin', infile, '--key', public_key], env=env)
        if result:
            shutil.copyfile(infile, outfile)
        return result

    def resign_tas(self) -> bool:
        private_key = self.keys.get('optee-signing-key.pem')
        env = self._prepare_path()
        result = True
        for dirpath, _, filenames in os.walk(self.workdir):
            for file in filenames:
                if file.endswith(".ta"):
                    if not self.run_command(['resign_ta.py', '--key', private_key, '--in',
                                             os.path.join(dirpath, file)], cleanup=False, env=env):
                        result = False
                        break
        self.keys.cleanup()
        return result
