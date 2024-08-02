import os

from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class EKBSigner (Signer):

    keytag = 'ekbsign'

    def __init__(self, app: Sanic, workdir: str, machine: str, soctype: str, bspversion: str):
        logger.debug('machine: {}, soctype: {}, bspversion: {}'.format(machine, soctype, bspversion))
        if soctype not in ['tegra194', 'tegra234']:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = os.path.join(app.config.get('L4T_TOOLS_BASE'),
                                      'L4T-{}-{}'.format(bspversion, 'tegra186' if soctype == 'tegra194' else soctype),
                                      'Linux_for_Tegra')
        if not os.path.exists(self.toolspath):
            raise ValueError('no tools available for soctype={} bspversion={}'.format(soctype, bspversion))
        self.soctype = soctype
        super().__init__(app, workdir, machine)

    def generate_ekb(self, outfile: str) -> bool:
        oem_k1_key = self.keys.get('oem_k1.key')
        fixed_vector = self.keys.get('fixed-vector')
        uefi_variable_authentication_key = self.keys.get('uefi-variable-authentication.key')
        cmd = [
            'python3', self.toolspath + '/source/public/optee/samples/hwkey-agent/host/tool/gen_ekb/gen_ekb.py',
            '-chip', 't234' if self.soctype == 'tegra234' else 't194',
            '-oem_k1_key', oem_k1_key,
            '-fv', fixed_vector,
            '-in_auth_key', uefi_variable_authentication_key,
            '-out', outfile
        ]
        result = self.run_command(cmd)

        return result
