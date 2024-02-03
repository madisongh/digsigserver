import os
import copy
import shutil
from typing import Optional

from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class RockchipSigner (Signer):

    keytag = 'rksign'
    supported_soctypes = ['rk3588', 'rk3566', 'rk3568']
    fit_image_output_files = ['fitImage', 'uboot.dtb']
    # These tools must be copied into the local working directory.  The setting.ini
    # file gets modified by rk_sign_tool.
    rkbin_tools_files = ['boot_merger', 'rk_sign_tool', 'setting.ini']

    def __init__(self, app: Sanic, workdir: str, machine: str, soctype: str):
        logger.debug("machine: {}, soctype: {}".format(machine, soctype))
        if soctype not in self.supported_soctypes:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = app.config.get('RK_TOOLS_PATH')
        if not os.path.exists(self.toolspath):
            raise ValueError("no tools available")
        if not os.path.exists(os.path.join(self.toolspath, 'rkbin-tools')):
            raise ValueError("no rkbin-tools subdirectory under {}".format(self.toolspath))
        self.soctype = soctype
        if soctype.lower().startswith("rk"):
            self.chip = soctype[2:]
        else:
            self.chip = soctype
        self.machine = machine
        self.local_toolsdir = os.path.join(workdir, "_tools")
        super().__init__(app, workdir, machine)

    def _prepare_path(self) -> dict:
        env = dict(copy.deepcopy(os.environ))
        curpath = env.get('PATH')
        env['PATH'] = self.local_toolsdir + ':' + self.toolspath
        if curpath:
            env['PATH'] += ':' + curpath
        return env

    def _prepare_local_toolsdir(self):
        if os.path.exists(self.local_toolsdir):
            shutil.rmtree(self.local_toolsdir)
        os.mkdir(self.local_toolsdir)
        for f in self.rkbin_tools_files:
            src = os.path.join(self.toolspath, 'rkbin-tools', f)
            dest = os.path.join(self.local_toolsdir, f)
            shutil.copyfile(src, dest)
            shutil.copymode(src, dest)

    def sign(self, artifact_type: str, burn_key_hash: bool, infile: Optional[str], outfile: Optional[str],
             external_data_offset: Optional[str]) -> bool:
        private_key = self.keys.get('dev.key')
        # mkimage requires this, even if not used
        cert = self.keys.get('dev.crt')
        result = False
        if artifact_type == "fit-image":
            env = self._prepare_path()
            cmd = ['mkimage', '-f', 'fit.its', '-E']
            if external_data_offset:
                cmd += ['-p', external_data_offset]
            cmd += ['-k', os.path.dirname(private_key), '-K', 'uboot.dtb', '-r', 'fitImage']
            result = self.run_command(cmd , env=env)
        elif artifact_type in ["idblock", "usbloader"]:
            public_key = self.keys.get('dev.pubkey')
            self._prepare_local_toolsdir()
            env = self._prepare_path()
            # rk_sign_tool fails if there is no dot in the file name
            os.rename(infile, infile + ".bin")
            infile += ".bin"
            result = self.run_command(['rk_sign_tool', 'cc', '--chip', self.chip], cleanup=False, env=env)
            if result:
                result = self.run_command(['rk_sign_tool', 'lk', '--key', private_key,
                                           '--pubkey', public_key], cleanup=False, env=env)
            if result and burn_key_hash:
                result = self.run_command(['rk_sign_tool', 'ss', '--flag', '0x20'], cleanup=False, env=env)
            if result:
                if artifact_type == "idblock":
                    result = self.run_command(['rk_sign_tool', 'sb', '--idb', infile], env=env)
                else:
                    result = self.run_command(['rk_sign_tool', 'sl', '--loader', infile], env=env)
            if result:
                shutil.copyfile(infile, outfile)
        self.keys.cleanup()
        return result
