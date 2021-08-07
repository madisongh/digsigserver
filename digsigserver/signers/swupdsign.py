import shutil
from digsigserver.signers import Signer


class SwupdateSigner(Signer):

    keytag = 'swupdate'

    def __init__(self, workdir: str, distro: str):
        signcmd = shutil.which('openssl')
        if not signcmd:
            raise RuntimeError('no openssl command')
        self.signcmd = signcmd
        super().__init__(workdir, distro)

    def sign(self, method: str, sw_description: str, outfile: str) -> bool:
        if method == "RSA":
            privkey = self.keys.get('rsa-private.key')
            if not privkey:
                raise RuntimeError('RSA private key missing for swupdate signing')
            cmd = [self.signcmd, 'dgst', '-sha256', '-sign', privkey, '-out', outfile, sw_description]
        elif method == "CMS":
            cms_cert = self.keys.get('cms.cert')
            cms_key = self.keys.get('cms-private.key')
            if not cms_cert or not cms_key:
                raise RuntimeError('CMS cert or private key missing for swupdate signing')
            cmd = [self.signcmd, 'cms', '-sign', '-in', sw_description, '-out', outfile,
                   '-signer', cms_cert, '-inkey', cms_key, '-outform', 'DER',
                   '-nosmimecap', '-binary']
        else:
            raise RuntimeError('Unrecognized signing method {} - must be RSA or CMS'.format(method))

        return self.run_command(cmd)
