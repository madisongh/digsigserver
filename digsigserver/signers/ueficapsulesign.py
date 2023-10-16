import os
import copy
import shutil

from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class UefiCapsuleSigner (Signer):

    keytag = 'ueficapsulesign'

    def __init__(self, app: Sanic, workdir: str, machine: str, soctype: str, bspversion: str, guid: str):
        logger.debug('machine: {}, soctype: {}, bspversion: {}, guid: {}'.format(machine, soctype, bspversion, guid))
        if soctype not in ['tegra194', 'tegra234']:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = os.path.join(app.config.get('L4T_TOOLS_BASE'),
                                      'L4T-{}-{}'.format(bspversion, 'tegra186' if soctype == 'tegra194' else soctype),
                                      'Linux_for_Tegra')
        if not os.path.exists(self.toolspath):
            raise ValueError('no tools available for soctype={} bspversion={}'.format(soctype, bspversion))
        verparts = bspversion.split('.')
        self.bsp_version32 = hex(int(verparts[0])<<16 | int(verparts[1])<<8 | int(verparts[2]))
        logger.debug('bsp_version32 = {}'.format(self.bsp_version32))
        self.machine = machine
        self.guid = guid
        super().__init__(app, workdir, machine)

    def generate_signed_capsule(self, infile: str, outfile: str) -> bool:
        result = False
        signer_private_cert = self.keys.get('signer_private_cert.pem')
        other_public_cert = self.keys.get('other_public_cert.pem')
        trusted_public_cert = self.keys.get('trusted_public_cert.pem')
        cmd = [
            'python3',
            self.toolspath + '/generate_capsule/Capsule/GenerateCapsule.py',
            '-v',
            '--encode',
            '--monotonic-count',
            '1',
            '--fw-version',
            self.bsp_version32,
            '--lsv',
            self.bsp_version32,
            '--guid',
            self.guid,
            '--signer-private-cert',
            signer_private_cert,
            '--other-public-cert',
            other_public_cert,
            '--trusted-public-cert',
            trusted_public_cert,
            '-o',
            outfile,
            infile
        ]
        result = self.run_command(cmd)

        return result
