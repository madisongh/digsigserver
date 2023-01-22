import os
import subprocess
from typing import Optional
from digsigserver.keyfiles import KeyFiles
from sanic import Sanic
from sanic.log import logger


class Signer:

    keytag = 'Unknown'

    def __init__(self, app: Sanic, workdir: str, key_selector: str):
        self.app = app
        self.workdir = workdir
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
            if cleanup:
                self.keys.cleanup()
            logger.warning("signing error: {}".format(e.stderr))
            return False
        if cleanup:
            self.keys.cleanup()
        return True
