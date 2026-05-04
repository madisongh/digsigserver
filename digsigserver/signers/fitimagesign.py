import os
import copy
import re
import subprocess
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

    @staticmethod
    def _normalize_keyname(keyname: Optional[str]) -> Optional[str]:
        if not keyname:
            return None
        resolved = keyname.strip()
        if not resolved:
            return None
        if resolved.endswith('.key'):
            resolved = resolved[:-4]
        return resolved or None

    def _keyname_from_dtb(self, dtb: Optional[str]) -> Optional[str]:
        if not dtb or not os.path.exists(dtb):
            return None
        try:
            with open(dtb, 'rb') as f:
                content = f.read().decode('latin-1', errors='ignore')
        except OSError:
            return None

        # U-Boot signature keys are typically named key-<name>.
        match = re.search(r'key-([A-Za-z0-9_.-]+)', content)
        if match:
            return match.group(1)
        return None

    def _keyname_from_fitimage(self, fitimage: str, env: dict) -> Optional[str]:
        try:
            proc = subprocess.run(
                ['mkimage', '-l', fitimage],
                stdin=subprocess.DEVNULL,
                cwd=self.workdir,
                env=env,
                check=True,
                capture_output=True,
                encoding='utf-8'
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        # Example: "Sign algo:    sha256,rsa2048:dev_vb"
        match = re.search(r'Sign algo:\s+[^:\n]+:([A-Za-z0-9_.-]+)', proc.stdout)
        if match:
            return match.group(1)
        return None

    def _resolve_keyname(self, keyname: Optional[str], dtb: Optional[str], fitimage: str, env: dict) -> str:
        resolved = self._normalize_keyname(keyname)
        if resolved:
            return resolved
        resolved = self._keyname_from_dtb(dtb)
        if resolved:
            logger.info("Resolved fitImage keyname from dtb: %s", resolved)
            return resolved
        resolved = self._keyname_from_fitimage(fitimage, env)
        if resolved:
            logger.info("Resolved fitImage keyname from fitImage metadata: %s", resolved)
            return resolved
        logger.info("Using default fitImage keyname: dev")
        return 'dev'

    def sign(self, fitimage: str,
             dtb: Optional[str],
             external_data_offset: Optional[str],
             mark_required: Optional[bool],
             algo: Optional[str],
             keyname: Optional[str] = None,
             comment: Optional[str] = None) -> bool:
        env = self._prepare_path()
        selected_keyname = self._resolve_keyname(keyname, dtb, fitimage, env)
        if self.backend == "pkcs11":
            keyname = keyname.replace('pin-value=password', 'pin-value=' + self.app.config.get('YUBIHSM_PASSWORD'))
            cmd = ['mkimage', '-E', '-F', '-N', 'pkcs11', '-k', selected_keyname, '-v']
        else:
            private_key = self.keys.get("{}.key".format(selected_keyname))
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
