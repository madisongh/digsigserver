import os
import shutil
import subprocess
from urllib.parse import urlparse
from sanic import request
from sanic.log import logger


def extract_files(workdir: str, f: request.File) -> bool:
    try:
        subprocess.run(['tar', '-x', '-z', '-f-'],
                       input=f.body, check=True,
                       cwd=workdir)
    except subprocess.CalledProcessError as e:
        logger.warning("tar failure: {}\n".format(e.stderr))
        return False
    return True


def repack_files(workdir: str, outfile: str) -> bool:
    try:
        subprocess.run(['tar', '-c', '-z', '-v', '-f', outfile, '.'],
                       stdin=subprocess.DEVNULL, check=True,
                       capture_output=True, cwd=workdir)
    except subprocess.CalledProcessError as e:
        logger.warning("tar failure on repack: {}\n".format(e.stderr))
        return False
    return True


def uri_exists(uri: str, is_dir=False) -> bool:
    u = urlparse(uri)
    if u.scheme == 'file' or u.scheme == '':
        return os.path.isdir(u.path) if is_dir else os.path.exists(u.path)
    if u.scheme == 's3':
        if is_dir and not uri.endswith('/'):
            uri += '/'
        cmd = ['aws', 's3', 'ls', uri]
        try:
            subprocess.run(cmd, check=True, encoding='utf-8',
                           stdin=subprocess.DEVNULL, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.warning('cmd: {}\nstderr: {}'.format(' '.join(cmd), e.stderr))
            return False
    logger.error('unrecognized URI: {}'.format(uri))
    return False


def uri_fetch(uri: str, dest: str, is_dir=False):
    u = urlparse(uri)
    if u.scheme == 'file' or u.scheme == '':
        if is_dir:
            for f in os.listdir(u.path):
                shutil.copyfile(os.path.join(u.path, f), os.path.join(dest, f))
        else:
            shutil.copyfile(u.path, dest)
        return
    if u.scheme == 's3':
        cmd = ['aws', 's3', 'cp', uri, dest]
        if is_dir:
            cmd.append('--recursive')
        try:
            proc = subprocess.run(cmd,
                                  check=True, encoding='utf-8',
                                  stdin=subprocess.DEVNULL, capture_output=True)
            logger.debug("cmd: {}\noutput: {}\n".format(' '.join(cmd), proc.stdout))
        except subprocess.CalledProcessError as e:
            raise RuntimeError('cmd: {}\nstderr: {}'.format(' '.join(cmd), e.stderr))
        return
    raise RuntimeError('unrecognized URI: {}'.format(uri))


def upload_file(filename: str, uri: str):
    u = urlparse(uri)
    if u.scheme == 'file' or u.scheme == '':
        shutil.copyfile(filename, u.path)
        return
    if u.scheme == 's3':
        cmd = ['aws', 's3', 'cp', filename, uri]
        logger.info("Running: {}".format(cmd))
        try:
            subprocess.run(cmd,
                           check=True, encoding='utf-8',
                           stdin=subprocess.DEVNULL, capture_output=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError('cmd:{}\nstderr: {}'.format(' '.join(cmd), e.stderr))
        return
    raise RuntimeError('unrecognized URI: {}'.format(uri))
