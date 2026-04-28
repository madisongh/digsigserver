import os
import subprocess
from typing import Optional
from digsigserver.keyfiles import KeyFiles
from sanic import Sanic
from sanic.log import logger


class Signer:

    keytag = 'Unknown'

    def __init__(self, app: Sanic, workdir: str, key_selector: Optional[str] = None,
                 backend: Optional[str] = None, load_keys: bool = True):
        self.app = app
        self.workdir = workdir
        self.backend = backend or 'ssl'
        self.keys = None
        if load_keys:
            self.keys = KeyFiles(app, self.keytag, key_selector)

    def sign(self, *args) -> bool:
        raise RuntimeError("unimplemented sign method")

    def run_command(self, cmd: list, cleanup: bool = True, env: Optional[dict] = None) -> bool:
        if not env:
            env = os.environ
        try:
            logger.info("PATH={}".format(env.get('PATH')))
            logger.info("Running: {}".format(cmd))
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=self.workdir,
                                  env=env, check=True, capture_output=True,
                                  encoding='utf-8')
            logger.debug("stdout: {}".format(proc.stdout))
            logger.debug("stderr: {}".format(proc.stderr))
        except subprocess.CalledProcessError as e:
            if cleanup and self.keys:
                self.keys.cleanup()
            logger.warning("signing error: {}".format(e.stderr))
            logger.warning("stdout: {}".format(e.stdout))
            logger.warning("return code: {}".format(e.returncode))
            return False
        if cleanup and self.keys:
            self.keys.cleanup()
        return True
