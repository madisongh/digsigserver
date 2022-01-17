import asyncio
import tempfile
import re
import os

from sanic import Sanic, request
from sanic.log import logger
from sanic.response import text

from digsigserver.signers.tegrasign import TegraSigner
from digsigserver.signers.kmodsign import KernelModuleSigner
from digsigserver.signers.mendersign import MenderSigner
from digsigserver.signers.swupdsign import SwupdateSigner
from . import utils

# Signing can take a loooong time, so set a more reasonable
# default response timeout
CodesignSanicDefaults = {
    'RESPONSE_TIMEOUT': 600,
    'L4T_TOOLS_BASE': '/opt/nvidia',
    'KEYFILE_URI': 'file:///please/configure/this/path',
    'LOG_LEVEL': 'INFO'
}


"""
Actual initialization happens here
"""
app = Sanic(name='digsigserver', env_prefix='DIGSIGSERVER_')
app.config.update_config(CodesignSanicDefaults)
app.config.load_environment_vars(prefix='DIGSIGSERVER_')
logger.setLevel(app.config.get("LOG_LEVEL"))


def config_get(item: str, default_value=None) -> str:
    return app.config.get(item, default_value)


def validate_upload(req: request, name: str) -> request.File:
    f = req.files.get(name)
    return f if f and f.type == "application/octet-stream" else None


def parse_manifest(manifest_file: str) -> dict:
    result = {}
    if not os.path.exists(manifest_file):
        return result
    with open(manifest_file, mode='r', encoding='utf-8') as f:
        for line in f:
            logger.info("manifest line: {}".format(line.rstrip()))
            m = re.match(r'([^=]+)=(.*)', line.rstrip())
            if m is None:
                raise ValueError('invalid syntax in manifest file')
            result[m.group(1)] = m.group(2)
    return result


async def return_file(req: request, filename: str, return_filename: str):
    response = await req.respond(content_type="application/octet-stream",
                                 headers={"Content-Disposition": f'Attachment; filename="{return_filename}"'})
    with open(filename, "rb") as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            await response.send(data, False)
    await response.eof()


async def return_tarball(req: request, workdir: str, return_filename: str = "signed-artifact.tar.gz"):
    outfile = tempfile.NamedTemporaryFile(delete=False)
    outfile.close()
    if utils.repack_files(workdir, outfile.name):
        await return_file(req, outfile.name, return_filename)
        response = None
    else:
        response = text("Signing error", status=500)
    os.unlink(outfile.name)
    return response


@app.post("/sign/tegra")
async def sign_handler_tegra(req: request):
    f = validate_upload(req, "artifact")
    if not f:
        return text("Invalid artifact", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        try:
            s = TegraSigner(workdir, req.form.get("machine"), req.form.get("soctype"), req.form.get("bspversion"))
        except ValueError:
            return text("Invalid parameters", status=400)

        if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
            try:
                envvars = parse_manifest(os.path.join(workdir, 'MANIFEST'))
            except ValueError:
                return text("Invalid manifest", status=400)
            if 'BUPGENSPECS' in envvars:
                result = await asyncio.get_running_loop().run_in_executor(None, s.multisign, envvars)
            elif 'SIGNFILES' in envvars:
                result = await asyncio.get_running_loop().run_in_executor(None, s.signfiles, envvars)
            else:
                result = await asyncio.get_running_loop().run_in_executor(None, s.sign, envvars)
            if result:
                return await return_tarball(req, workdir)
    return text("Signing error", status=500)


@app.post("/sign/modules")
async def sign_handler_modules(req: request):
    f = validate_upload(req, "artifact")
    if not f:
        return text("Invalid artifact", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        try:
            s = KernelModuleSigner(workdir, req.form.get("machine"), req.form.get("hashalg", "sha512"))
        except ValueError:
            return text("Invalid parameters", status=400)

        if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
            result = await asyncio.get_running_loop().run_in_executor(None, s.sign)
            if result:
                return await return_tarball(req, workdir)
    return text("Signing error", status=500)


@app.post("/sign/swupdate")
async def sign_handler_swupdate(req: request):
    distro = req.form.get("distro")
    if not distro:
        return text("Distro name missing", status=400)
    method = req.form.get("method")
    if not method:
        method = "RSA"
    f = validate_upload(req, "sw-description")
    if not f:
        return text("Invalid sw-description", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        try:
            s = SwupdateSigner(workdir, distro)
        except ValueError:
            logger.info("could not init signer")
            return text("Invalid parameters", status=400)
        outfile = tempfile.NamedTemporaryFile(delete=False)
        outfile.close()
        with open(os.path.join(workdir, "sw-description"), "w") as infile:
            infile.write(f.body.decode('UTF-8'))
        if await asyncio.get_running_loop().run_in_executor(None, s.sign,
                                                            method, "sw-description",
                                                            outfile.name):
            await return_file(req, outfile.name, "sw-description.sig")
            response = None
        else:
            response = text("Signing error", status=500)
    os.unlink(outfile.name)
    return response


@app.post("/sign/mender")
async def sign_handler_mender(req: request):
    artifact = req.form.get('artifact-uri')
    if not artifact:
        return text("Artifact URI missing", status=400)
    distro = req.form.get('distro')
    if not distro:
        return text("Distro name missing", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        try:
            s = MenderSigner(workdir, distro, artifact)
        except ValueError:
            return text("Invalid parameters", status=400)
        if await asyncio.get_running_loop().run_in_executor(None, s.sign):
            return text("Signing successful")
    return text("Signing error", status=500)
