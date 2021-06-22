import shutil
import subprocess
from .keyfiles import KeyFiles

from sanic.log import logger


class SwupdateSigner:
    def __init__(self, distro: str):
        signcmd = shutil.which('openssl')
        if not signcmd:
            raise RuntimeError('no openssl command')
        self.signcmd = signcmd
        self.keys = KeyFiles('swupdate', distro)

    def sign(self, workdir: str, method: str, sw_description: str, outfile: str) -> bool:
        if method == "RSA":
            privkey = self.keys.get('rsa-private.key')
            if not privkey:
                raise RuntimeError('RSA private key missing for swupdate signing')
            cmd = ['openssl', 'dgst', '-sha256', '-sign', privkey, '-out', outfile, sw_description]
        elif method == "CMS":
            cms_cert = self.keys.get('cms.cert')
            cms_key = self.keys.get('cms-private.key')
            if not cms_cert or not cms_key:
                raise RuntimeError('CMS cert or private key missing for swupdate signing')
            cmd = ['openssl', 'cms', '-sign', '-in', sw_description, '-out', outfile,
                   '-signer', cms_cert, '-inkey', cms_key, '-outform', 'DER',
                   '-nosmimecap', '-binary']
        else:
            raise RuntimeError('Unrecognized signing method {} - must be RSA or CMS'.format(method))

        try:
            logger.info("Running: {}".format(cmd))
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=workdir,
                                  check=True, capture_output=True,
                                  encoding='utf-8')
            logger.debug("stdout: {}".format(proc.stdout))
            logger.debug("stderr: {}".format(proc.stderr))
        except subprocess.CalledProcessError as e:
            self.keys.cleanup()
            logger.warning("signing error: {}".format(e.stderr))
            return False
        self.keys.cleanup()
        return True
