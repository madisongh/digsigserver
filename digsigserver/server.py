import asyncio
import tempfile
import re
import os

from sanic import Sanic, request
from sanic.log import logger
from sanic.response import text, file_stream

from .tegrasign import TegraSigner
from .kmodsign import KernelModuleSigner
from .mendersign import MenderSigner
from . import utils


# Signing can take a loooong time, so set a more reasonable
# default response timeout
class CodesignSanicDefaults:
    RESPONSE_TIMEOUT = 180
    L4T_TOOLS_BASE = '/opt/nvidia'
    KEYFILE_URI = 'file:///please/configure/this/path'
    LOG_LEVEL = 'INFO'


app = Sanic(name='digsigserver', load_env=False)
app.config.from_object(CodesignSanicDefaults)
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


@app.post("/sign/tegra")
async def sign_handler_tegra(req: request):
    try:
        s = TegraSigner(req.form.get("machine"), req.form.get("soctype"), req.form.get("bspversion"))
    except ValueError:
        return text("Invalid parameters", status=400)

    f = validate_upload(req, "artifact")
    if not f:
        return text("Invalid artifact", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
            try:
                envvars = parse_manifest(os.path.join(workdir, 'MANIFEST'))
            except ValueError:
                return text("Invalid manifest", status=400)
            result = await asyncio.get_running_loop().run_in_executor(None, s.sign, envvars, workdir)
            if result:
                with tempfile.NamedTemporaryFile() as outfile:
                    if await asyncio.get_running_loop().run_in_executor(None, utils.repack_files,
                                                                        workdir, outfile.name):
                        return await file_stream(outfile.name,
                                                 mime_type="application/octet-stream",
                                                 filename="signed-artifact.tar.gz")
    return text("Signing error", status=500)


@app.post("/sign/modules")
async def sign_handler_modules(req: request):
    try:
        s = KernelModuleSigner(req.form.get("machine"), req.form.get("hashalg", "sha512"))
    except ValueError:
        return text("Invalid parameters", status=400)

    f = validate_upload(req, "artifact")
    if not f:
        return text("Invalid artifact", status=400)
    with tempfile.TemporaryDirectory() as workdir:
        if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
            result = await asyncio.get_running_loop().run_in_executor(None, s.sign, workdir)
            if result:
                with tempfile.NamedTemporaryFile() as outfile:
                    if await asyncio.get_running_loop().run_in_executor(None, utils.repack_files,
                                                                        workdir, outfile.name):
                        return await file_stream(outfile.name,
                                                 mime_type="application/octet-stream",
                                                 filename="signed-artifact.tar.gz")
    return text("Signing error", status=500)


@app.post("/sign/mender")
async def sign_handler_mender(req: request):
    artifact = req.form.get('artifact-uri')
    if not artifact:
        return text("Artifact URI missing", status=400)
    distro = req.form.get('distro')
    if not distro:
        return text("Distro name missing", status=400)
    try:
        s = MenderSigner(distro, artifact)
    except ValueError:
        return text("Invalid parameters", status=400)

    with tempfile.TemporaryDirectory() as workdir:
        if await asyncio.get_running_loop().run_in_executor(None, s.sign, workdir):
            return text("Signing successful")
    return text("Signing error", status=500)
