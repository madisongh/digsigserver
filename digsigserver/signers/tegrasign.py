import os
import copy
import shutil
from typing import Optional
from digsigserver.signers import Signer
from digsigserver import server

from sanic.log import logger


def bsp_tools_path(soctype: str, bspversion: str) -> str:
    suffix = ""
    majver = bspversion.split(".")[0]
    try:
        if majver and int(majver) < 34:
            suffix = '-tegra186' if soctype == 'tegra194' else "-" + soctype
    except ValueError:
        pass
    toolspath = os.path.join(server.config_get('L4T_TOOLS_BASE'),
                             'L4T-{}{}'.format(bspversion, suffix),
                             'Linux_for_Tegra')
    return toolspath if os.path.exists(toolspath) else None


class TegraSigner (Signer):

    keytag = 'tegrasign'

    signing_scripts = [os.path.join('bootloader', 'tegraflash.py'),
                       os.path.join('bootloader', 'tegraflash_internal.py'),
                       os.path.join('bootloader', 'BUP_generator.py'),
                       os.path.join('bootloader', 'odmsign.func'),
                       os.path.join('bootloader', 'l4t_bup_gen.func')]

    tegrasign_v3_scripts = ['tegra-signimage-helper',
                            'l4t_sign_image.sh']

    tegrasign_v3_support = [os.path.join('bootloader', 'tegrasign_v3.py'),
                            os.path.join('bootloader', 'tegrasign_v3_internal.py'),
                            os.path.join('bootloader', 'tegrasign_v3_util.py')]

    def __init__(self, workdir: str, machine: str, soctype: str, bspversion: str):
        logger.debug("machine: {}, soctype: {}, bspversion: {}".format(machine, soctype, bspversion))
        if soctype not in ['tegra186', 'tegra194', 'tegra210']:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.toolspath = bsp_tools_path(soctype, bspversion)
        if self.toolspath is None:
            raise ValueError("no tools available for soctype={} bspversion={}".format(soctype, bspversion))
        bspmajor, bspminor = tuple([int(v) for v in bspversion.split('.')[0:2]])
        if soctype == 'tegra210':
            self.tegrasign_v3 = False
            self.encrypted_kernel = False
        else:
            self.tegrasign_v3 = (bspmajor > 32 or (bspmajor == 32 and bspminor >= 5))
            if soctype == 'tegra194':
                self.encrypted_kernel = True
            else:
                self.encrypted_kernel = (bspmajor > 32 or (bspmajor == 32 and bspminor >= 6))
        self.scripts = copy.copy(self.signing_scripts)
        self.scripts.append(os.path.join('bootloader', '{}-flash-helper'.format(soctype)))
        if soctype == 'tegra210':
            if bspmajor > 32 or (bspmajor == 32 and bspminor >= 6):
                self.scripts.append(os.path.join('bootloader', 'nvflashxmlparse'))
        else:
            self.scripts.append(os.path.join('bootloader', 'rollback', 'rollback_parser.py'))
        if self.tegrasign_v3:
            self.scripts += self.tegrasign_v3_scripts + self.tegrasign_v3_support
        elif bspmajor > 32 or (bspmajor == 32 and bspminor >= 6):
            self.scripts += self.tegrasign_v3_support
        self.soctype = soctype
        self.machine = machine
        super().__init__(workdir, machine)
        self.local_toolsdir = os.path.join(self.workdir, '_tools')
        logger.debug("scripts: {}".format(self.scripts))

    def _prepare_symlinks(self, files: list):
        for s in files:
            if os.path.exists(os.path.join(self.workdir, s)):
                os.unlink(os.path.join(self.workdir, s))
            os.symlink(os.path.join(self.local_toolsdir, 'bootloader', s),
                       os.path.join(self.workdir, s))

    def _prepare_scripts(self):
        if os.path.exists(self.local_toolsdir):
            shutil.rmtree(self.local_toolsdir)
        os.mkdir(self.local_toolsdir)
        for script in self.scripts:
            subdir = os.path.dirname(script)
            if subdir:
                os.makedirs(os.path.join(self.local_toolsdir, subdir), exist_ok=True)
            src = os.path.join(self.toolspath, script)
            dest = os.path.join(self.local_toolsdir, script)
            if script.endswith('.py') and not ('tegraflash' in script or
                                               'tegrasign_v3' in script):
                shutil.copyfile(src, dest + '.real')
                shutil.copymode(src, dest + '.real')
                with open(dest, 'w') as f:
                    f.write('#!/bin/sh\npython2 {} "$@"\n'.format(dest + '.real'))
                os.chmod(dest, 0o755)
                logger.debug("Copy-wrapped {} -> {}".format(src, dest))
            else:
                shutil.copyfile(src, dest)
                shutil.copymode(src, dest)
                logger.debug("Copied {} -> {}".format(src, dest))
        # Finally, we need some symlinks in the working directory to point to
        # some of the tools
        self._prepare_symlinks(['tegraflash.py', 'BUP_generator.py'])
        if self.soctype == "tegra210":
            # XXX
            # Older versions of tegra210-flash-helper directly write the
            # full path of the script into the flashcmd.txt file, so
            # symlink it into the working directory to work around that.
            # We also have to add the '.func' scripts that it assumes
            # reside in the same directory.
            # XXX
            self._prepare_symlinks(['tegra210-flash-helper', 'odmsign.func', 'l4t_bup_gen.func'])
        else:
            os.makedirs(os.path.join(self.workdir, 'rollback'), exist_ok=True)
            if os.path.exists(os.path.join(self.workdir, 'rollback', 'rollback_parser.py')):
                os.unlink(os.path.join(self.workdir, 'rollback', 'rollback_parser.py'))
            os.symlink(os.path.join(self.local_toolsdir, 'bootloader', 'rollback', 'rollback_parser.py'),
                       os.path.join(self.workdir, 'rollback', 'rollback_parser.py'))

    def _prepare_path(self, envvars: dict) -> dict:
        env = copy.deepcopy(envvars)
        curpath = os.getenv('PATH')
        env['PATH'] = ':'.join([self.local_toolsdir, os.path.join(self.local_toolsdir, 'bootloader'),
                                self.toolspath, os.path.join(self.toolspath, 'bootloader')])
        if curpath:
            env['PATH'] += ':' + curpath
        env['MACHINE'] = self.machine
        return env

    def _prepare_cmd(self, env: dict, to_remove: Optional[list]) -> list:
        pkc = self.keys.get('rsa_priv.pem')
        sbk = None
        user_key = None
        # XXX
        # The tegra210-flash-helper script prior to L4T R32.6
        # integration erroneously put the full path name in
        # the generated flashing script, so work around that
        # here by directly referencing the symlink created above
        # in the working directory
        # XXX
        path_workaround = ""
        if self.soctype == 'tegra210':
            path_workaround = "./"
        else:
            if to_remove:
                to_remove.append('flash.xml')
            if not self.encrypted_kernel:
                kernelname, kernelext = os.path.splitext(env['LNXFILE'])
                if to_remove:
                    to_remove.append(kernelname + '_sigheader' + kernelext + '.encrypt.signed')
            try:
                sbk = self.keys.get('sbk.txt')
            except FileNotFoundError:
                sbk = None
            try:
                user_key = self.keys.get('user_key.txt')
            except FileNotFoundError:
                user_key = None

        cmd = ["{}{}-flash-helper".format(path_workaround, self.soctype),
               '--bup' if 'BUPGENSPECS' in env else '--no-flash', '-u', pkc]
        if sbk:
            cmd += ['-v', sbk]
        if user_key:
            cmd += ['--user_key', user_key]
        cfg_args = '{0}.cfg,{0}-override.cfg' if self.soctype == 'tegra194' else '{0}.cfg'
        cmd += ['flash.xml.in', env['DTBFILE'], cfg_args.format(self.machine), env['ODMDATA']]

        if self.soctype == 'tegra210':
            cmd.append(env['boardcfg'])

        cmd.append(env['LNXFILE'])

        return cmd

    def _remove_files(self, filenames: list):
        for name in filenames:
            path = os.path.join(self.workdir, name)
            if os.path.isdir(path):
                shutil.rmtree(path, ignore_errors=True)
            else:
                try:
                    os.unlink(path)
                except FileNotFoundError:
                    pass

    def sign(self, envvars: dict) -> bool:
        env = self._prepare_path(envvars)
        bupgen = 'BUPGEN' in env

        # Set this up first, so the local tools dir is present
        # when we set up the list of things to remove
        self._prepare_scripts()

        # We want to return the minimal set of artifacts possible, so
        # make sure we remove:
        # - the files that were sent over
        # - files generated that are not needed:
        #     - tegraflash will sign and encrypt the 'kernel', but cboot does
        #       not boot the encrypted+signed copy, just the signed one (pre-R32.5)
        #     - the subdirectories generated by the signing program
        #     - other housekeeping files
        to_remove = os.listdir(self.workdir) + ['signed', 'encrypted_signed', 'flash.xml.tmp']

        if self.run_command(self._prepare_cmd(env, to_remove), env=env):
            # For BUP generation, just return the payloads.
            # For flashing, we return all the signed/encrypted files
            if bupgen:
                self._remove_files([fname for fname in os.listdir(self.workdir) if not fname.startswith('payloads')])
            else:
                self._remove_files([fname for fname in to_remove])
            return True

        return False

    def signfiles(self, envvars: dict) -> bool:
        env = self._prepare_path(envvars)
        # We want to return the minimal set of artifacts possible.
        # For this method, it's just the '.sig' files generated for the
        # files that were sent over
        files_to_sign = os.listdir(self.workdir)
        keep_files = [f + ".sig" for f in files_to_sign]
        pkc = self.keys.get('rsa_priv.pem')
        self._prepare_scripts()
        cmd = ["tegra-signimage-helper", "--chip 0x{}".format(self.soctype[5:7]), "-u", pkc] + files_to_sign
        if self.run_command(cmd, env=env):
            self._remove_files([fname for fname in os.listdir(self.workdir) if fname not in keep_files])
            return True
        return False

    def multisign(self, envvars: dict) -> bool:
        env = self._prepare_path(envvars)
        self._prepare_scripts()
        cmd = self._prepare_cmd(env, None)
        for spec in env['BUPGENSPECS'].split():
            localenv = copy.deepcopy(env)
            for setting in spec.split(';'):
                var, val = setting.split('=')
                logger.debug('Setting: {}={}'.format(var.upper(), val))
                localenv[var.upper()] = val
            if not self.run_command(cmd, cleanup=False, env=localenv):
                self.keys.cleanup()
                return False

        self.keys.cleanup()
        self._remove_files([fname for fname in os.listdir(self.workdir) if not fname.startswith('payloads')])

        return True
