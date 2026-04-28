import shutil
from digsigserver.signers import Signer
from sanic import Sanic


class SwupdateSigner(Signer):
    keytag = 'swupdate'

    def __init__(self, app: Sanic, workdir: str, distro: str, backend: str):
        signcmd = shutil.which('openssl')
        if not signcmd:
            raise RuntimeError('no openssl command')
        self.signcmd = signcmd
        super().__init__(app, workdir, distro, backend)

    def sign(self, method: str, sw_description: str, outfile: str, key_uri: str = None) -> bool:
        match (method, self.backend):
            case ("RSA", "ssl"):
                privkey = self.keys.get('rsa-private.key')
                if not privkey:
                    raise RuntimeError('RSA private key missing for swupdate signing')
                cmd = [self.signcmd, 'dgst', '-sha256', '-sign', privkey, '-out', outfile, sw_description]
            case ("CMS", "ssl"):
                cms_cert = self.keys.get('cms.cert')
                cms_key = self.keys.get('cms-private.key')
                if not cms_cert or not cms_key:
                    raise RuntimeError('CMS cert or private key missing for swupdate signing')
                cmd = [self.signcmd, 'cms', '-sign', '-in', sw_description, '-out', outfile,
                       '-signer', cms_cert, '-inkey', cms_key, '-outform', 'DER',
                       '-nosmimecap', '-binary']
            case ("RSA", "pkcs11"):
                if not key_uri:
                    raise RuntimeError('Key URI missing for RSA signing with PKCS#11 backend')
                key_uri = key_uri.replace('pin-value=password', 'pin-value=' + self.app.config.get('YUBIHSM_PASSWORD'))
                cmd = [self.signcmd, 'dgst', '-sha256', '-engine', 'pkcs11',
                       '-keyform', 'ENGINE', '-sign', key_uri, '-out', outfile, sw_description]
            case ("CMS", "pkcs11"):
                if not key_uri:
                    raise RuntimeError('Key URI missing for CMS signing with PKCS#11 backend')
                key_uri = key_uri.replace('pin-value=password', 'pin-value=' + self.app.config.get('YUBIHSM_PASSWORD'))
                cert_uri = self.keys.get("cms.cert")
                cmd = [self.signcmd, 'cms', '-sign', '-engine', 'pkcs11',
                       '-keyform', 'engine', '-in', sw_description, '-out', outfile,
                       '-signer', cert_uri, '-inkey', key_uri, '-outform', 'DER',
                       '-nosmimecap', '-binary']
            case _:
              raise RuntimeError('Unrecognized signing method {} or backend {} allowed: RSA, CMS with ssl or pkcs11'.format(method, self.backend))

        return self.run_command(cmd)
