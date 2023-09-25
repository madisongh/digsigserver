import os
import copy
import shutil

from digsigserver.signers import Signer

from sanic import Sanic
from sanic.log import logger


class UefiSigner (Signer):

    keytag = 'uefisign'

    def __init__(self, app: Sanic, workdir: str, machine: str, signing_type: str):
        logger.debug('machine: {}, signing type: {}'.format(machine, signing_type))
        if signing_type not in ['sbsign', 'signature', 'attach_signature']:
            raise ValueError("signing_type '{}' invalid".format(signing_type))
        self.signing_type = signing_type
        super().__init__(app, workdir, machine)

    def sign(self, infile: str, outfile: str) -> bool:
        result = False
        db_key = self.keys.get('db.key')
        db_cert = self.keys.get('db.crt')
        if self.signing_type == 'sbsign':
            cmd = [
                'sbsign',
                '--key',
                db_key,
                '--cert',
                db_cert,
                '--output',
                outfile,
                infile
            ]
            result = self.run_command(cmd)
        elif self.signing_type == 'signature':
            cmd = [
                'openssl',
                'cms',
                '-sign',
                '-signer',
                db_cert,
                '-inkey',
                db_key,
                '-binary',
                '-in',
                infile,
                '-outform',
                'der',
                '-out',
                outfile
            ]
            result = self.run_command(cmd)
        elif self.signing_type == 'attach_signature':
            sig_tmp = infile + '.sig.tmp'
            sign_cmd = [
                'openssl',
                'cms',
                '-sign',
                '-signer',
                db_cert,
                '-inkey',
                db_key,
                '-binary',
                '-in',
                infile,
                '-outform',
                'der',
                '-out',
                sig_tmp
            ]
            result = self.run_command(sign_cmd)
            shutil.copyfile(infile, outfile)
            if result:
                truncate_cmd = [
                    'truncate',
                    '--size=%2048',
                    outfile,
                ]
                result = self.run_command(truncate_cmd)
            if result:
                with open(sig_tmp, 'rb') as file1:
                    with open(outfile, 'ab') as file2:
                        shutil.copyfileobj(file1, file2)

        return result
