import tempfile
import os

from sanic import Sanic
from . import utils


class KeyFiles:
    signing_types = [
        'tegrasign',
        'imxsign',
        'kmodsign',
        'mender',
        'swupdate',
        'opteesign',
        'rksign',
        'rkopteesign',
        'uefisign',
        'ueficapsulesign'
    ]

    def __init__(self, app: Sanic, signtype: str, machine_or_distro: str):
        if signtype not in self.signing_types:
            raise RuntimeError('unrecognized signing type: {}'.format(signtype))
        self.keyfileuri = '{}/{}/{}/'.format(app.config.get('KEYFILE_URI'),
                                             machine_or_distro, signtype)
        self.tmpdir = None
        if not utils.uri_exists(self.keyfileuri, is_dir=True):
            raise RuntimeError('no key files found for {}/{}'.format(signtype, machine_or_distro))

    def get(self, keyname: str) -> str:
        if not self.tmpdir:
            self.tmpdir = tempfile.TemporaryDirectory()
        path = os.path.join(self.tmpdir.name, keyname)
        if os.path.exists(path):
            return path
        try:
            utils.uri_fetch(os.path.join(self.keyfileuri, keyname), path)
        except RuntimeError:
            pass
        if os.path.exists(path):
            return path
        raise FileNotFoundError('No key file named {}'.format(keyname))

    def cleanup(self):
        if self.tmpdir:
            try:
                self.tmpdir.cleanup()
            except FileNotFoundError:
                pass
        self.tmpdir = None
