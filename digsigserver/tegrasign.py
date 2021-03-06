import os
import copy
import subprocess
from .keyfiles import KeyFiles
from . import utils
from . import server

from sanic.log import logger


def bsp_tools_path(soctype: str, bspversion: str) -> str:
    suffix = 'tegra186' if soctype == 'tegra194' else soctype
    toolspath = os.path.join(server.config_get('L4T_TOOLS_BASE'),
                             'L4T-{}-{}'.format(bspversion, suffix),
                             'Linux_for_Tegra', 'bootloader')
    return toolspath if os.path.exists(toolspath) else None


class TegraSigner:
    script_symlinks = ['tegraflash.py', 'tegraflash_internal.py', 'BUP_generator.py',
                       os.path.join('rollback', 'rollback_parser.py')]

    def __init__(self, machine: str, soctype: str, bspversion: str):
        if soctype not in ['tegra186', 'tegra194', 'tegra210']:
            raise ValueError("soctype '{}' invalid".format(soctype))
        self.soctype = soctype
        self.machine = machine
        self.toolspath = bsp_tools_path(soctype, bspversion)
        if self.toolspath is None:
            raise ValueError("no tools available for soctype={} bspversion={}".format(soctype, bspversion))
        self.keys = KeyFiles('tegrasign', machine)

    def _symlink_scripts(self, workdir: str):
        self._remove_scripts(workdir)
        for script in self.script_symlinks:
            subdir = os.path.dirname(script)
            if subdir:
                os.makedirs(os.path.join(workdir, subdir), exist_ok=True)
            src = os.path.join(self.toolspath, script)
            dest = os.path.join(workdir, script)
            if script.endswith('.py') and not script.startswith('tegraflash'):
                with open(os.path.join(workdir, script), 'w') as f:
                    f.write('#!/bin/sh\npython2 {} "$@"\n'.format(src))
                os.chmod(dest, 0o755)
            else:
                os.symlink(src, dest)

    def _remove_scripts(self, workdir: str):
        utils.remove_files([os.path.join(workdir, script) for script in self.script_symlinks])

    def sign(self, envvars: dict, workdir: str) -> bool:
        env = copy.deepcopy(envvars)
        curpath = os.getenv('PATH')
        env['PATH'] = self.toolspath
        if curpath:
            env['PATH'] += ':' + curpath
        env['MACHINE'] = self.machine
        bupgen = 'BUPGEN' in env
        self._symlink_scripts(workdir)
        # We want to return the minimal set of artifacts possible, so
        # make sure we remove:
        # - the files that were sent over
        # - files generated that are not needed:
        #     - tegraflash will sign and encrypt the 'kernel', but cboot does
        #       not boot the encrypted+signed copy, just the signed one
        #     - the subdirectories generated by the signing program
        #     - other housekeeping files
        to_remove = os.listdir(workdir) + ['signed', 'encrypted_signed', 'flash.xml.tmp']
        pkc = self.keys.get('rsa_priv.pem')
        if self.soctype == 'tegra210':
            sbk = None
        else:
            to_remove.append('flash.xml')
            kernelname, kernelext = os.path.splitext(env['LNXFILE'])
            to_remove.append(kernelname + '_sigheader' + kernelext + '.encrypt.signed')
            try:
                sbk = self.keys.get('sbk.txt')
            except FileNotFoundError:
                sbk = None
        cmd = ["{}-flash-helper".format(self.soctype),
               '--bup' if bupgen else '--no-flash', '-u', pkc]
        if sbk:
            cmd += ['-v', sbk]
        if self.soctype == 'tegra194':
            cmd += ['flash.xml.in', env['DTBFILE'], '{0}.cfg,{0}-override.cfg'.format(self.machine),
                env['ODMDATA']]
        else:
            cmd += ['flash.xml.in', env['DTBFILE'], '{}.cfg'.format(self.machine),
                env['ODMDATA']]

        if self.soctype == 'tegra210':
            cmd.append(env['boardcfg'])
        cmd.append(env['LNXFILE'])
        try:
            logger.info("Running: {}".format(cmd))
            proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=workdir,
                                  env=env, check=True, capture_output=True,
                                  encoding='utf-8')
            self.keys.cleanup()
            logger.debug("stdout: {}".format(proc.stdout))
            logger.debug("stderr: {}".format(proc.stderr))
            # For BUP generation, just return the payloads.
            # For flashing, we return all the signed/encrypted files
            if bupgen:
                utils.remove_files([os.path.join(workdir, fname)
                                    for fname in os.listdir(workdir) if not fname.startswith('payloads')])
            else:
                utils.remove_files([os.path.join(workdir, fname) for fname in to_remove])
            return True
        except subprocess.CalledProcessError as e:
            self.keys.cleanup()
            logger.warning("signing error, stdout: {}\nstderr: {}".format(e.stdout, e.stderr))
        return False

    def multisign(self, envvars: dict, workdir: str) -> bool:
        env = copy.deepcopy(envvars)
        curpath = os.getenv('PATH')
        env['PATH'] = self.toolspath
        if curpath:
            env['PATH'] += ':' + curpath
        env['MACHINE'] = self.machine
        self._symlink_scripts(workdir)
        pkc = self.keys.get('rsa_priv.pem')
        if self.soctype == 'tegra210':
            sbk = None
        else:
            try:
                sbk = self.keys.get('sbk.txt')
            except FileNotFoundError:
                sbk = None
        cmd = ["{}-flash-helper".format(self.soctype), '--bup', '-u', pkc]
        if sbk:
            cmd += ['-v', sbk]
        if self.soctype == 'tegra194':
            cmd += ['flash.xml.in', env['DTBFILE'], '{0}.cfg,{0}-override.cfg'.format(self.machine),
                env['ODMDATA']]
        else:
            cmd += ['flash.xml.in', env['DTBFILE'], '{}.cfg'.format(self.machine),
                env['ODMDATA']]
        if self.soctype == 'tegra210':
            cmd.append(env['boardcfg'])
        cmd.append(env['LNXFILE'])
        for spec in env['BUPGENSPECS'].split():
            localenv = copy.deepcopy(env)
            for setting in spec.split(';'):
                var, val = setting.split('=')
                logger.debug('Setting: {}={}'.format(var.upper(), val))
                localenv[var.upper()] = val
            try:
                logger.info("Running: {}".format(cmd))
                proc = subprocess.run(cmd, stdin=subprocess.DEVNULL, cwd=workdir,
                                      env=localenv, check=True, capture_output=True,
                                      encoding='utf-8')
                logger.debug("stdout: {}".format(proc.stdout))
                logger.debug("stderr: {}".format(proc.stderr))
            except subprocess.CalledProcessError as e:
                self.keys.cleanup()
                logger.warning("signing error, stdout: {}\nstderr: {}".format(e.stdout, e.stderr))
                return False

        self.keys.cleanup()
        utils.remove_files([os.path.join(workdir, fname)
                            for fname in os.listdir(workdir) if not fname.startswith('payloads')])
        return True
