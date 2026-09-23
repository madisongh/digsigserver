import base64
import os
import subprocess
from typing import Optional
from digsigserver.keyfiles import KeyFiles
from sanic import Sanic
from sanic.log import logger


class Signer:

    keytag = 'Unknown'

    def __init__(self, app: Sanic, parentdir: str, key_selector: str,
                 backend: Optional[str] = None, load_keys: bool = True):
        self.app = app
        self.workdir = os.path.join(parentdir, 'work')
        os.mkdir(self.workdir)
        self.parentdir = parentdir
        self.key_selector = key_selector
        self.backend = backend or 'ssl'
        self.keys = None
        if load_keys:
            self.keys = KeyFiles(app, self.keytag, key_selector, parent_dir=parentdir)

    def ensure_keys_loaded(self) -> KeyFiles:
        if not self.keys:
            self.keys = KeyFiles(self.app, self.keytag, self.key_selector, parent_dir=self.parentdir)
        return self.keys

    def sign(self, *args, **kwargs) -> bool:
        raise RuntimeError("unimplemented sign method")

    def run_command(self, cmd: list, cleanup: bool = True,
                    env: Optional[dict] = None, input_bytes: Optional[bytes] = None,
                    output_file: Optional[str] = None, b64encode_output: bool = False) -> bool:
        if not env:
            env = os.environ
        try:
            logger.info("PATH={}".format(env.get('PATH')))
            logger.info("Running: {}".format(cmd))
            if input_bytes is not None:
                proc = subprocess.run(cmd, input=input_bytes, cwd=self.workdir,
                                      env=env, check=True, capture_output=True)
            else:
                proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=self.workdir,
                                      env=env, check=True, capture_output=True)
            if output_file is not None:
                if b64encode_output:
                    with open(output_file, 'w+b') as f:
                        f.write(base64.b64encode(proc.stdout))
                else:
                    with open(output_file, 'w+') as f:
                        f.write(proc.stdout.decode('utf-8'))
                logger.debug("stdout sent to {}{}".format(output_file, ' (base64 encoded)' if b64encode_output else ''))
            else:
                logger.debug("stdout: {}".format(proc.stdout.decode('utf-8')))
            logger.debug("stderr: {}".format(proc.stderr.decode('utf-8')))
        except subprocess.CalledProcessError as e:
            if cleanup and self.keys:
                self.keys.cleanup()
            logger.warning("signing error: {}".format(e.stderr.decode('utf-8')))
            logger.warning("stdout: {}".format(e.stdout.decode('utf-8')))
            logger.warning("return code: {}".format(e.returncode))
            return False
        if cleanup and self.keys:
            self.keys.cleanup()
        return True
