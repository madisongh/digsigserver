import asyncio
import tempfile
import re
import os
from functools import partial, update_wrapper

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


"""
If a temporary file is being streamed back in response,
we need a way to remove that file once the response is
complete.  Sanic provides no built-in way to do this,
so borrow the following wrapping technique from the
Sanic Plugins Framework project to wrap the normal
request handler function.
"""


async def my_handle_request(real_handler, req, write_cb, stream_cb):
    """
    Wraps the normal handle_request function so we can check
    if a filename has been set at req.ctx; if so, that's a
    temporary file that needs to be deleted when we're done.
    :param real_handler: normal handle_request function
    :param req: request object
    :param write_cb: write callback
    :param stream_cb: stream callback
    :return:
    """
    cancelled = False
    req.ctx = None
    try:
        _ = await real_handler(req, write_cb, stream_cb)
    except asyncio.CancelledError as ce:
        cancelled = ce
    except BaseException as be:
        raise
    finally:
        if req.ctx:
            os.unlink(req.ctx)
            logger.info("Removed {}".format(req.ctx))
        if cancelled:
            raise cancelled


def wrap_handle_request(app_):
    """
    Uses functools to wrap the handle_request method
    in the app object.
    :param app_: Sanic app
    :return: callable
    """
    orig_handle_request = app_.handle_request
    return update_wrapper(partial(my_handle_request, orig_handle_request), my_handle_request)


"""
Actual initialization happens here
"""
app = Sanic(name='digsigserver', load_env=False)
app.config.from_object(CodesignSanicDefaults)
app.config.load_environment_vars(prefix='DIGSIGSERVER_')
logger.setLevel(app.config.get("LOG_LEVEL"))
app.handle_request = wrap_handle_request(app)


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
            if 'BUPGENSPECS' in envvars:
                result = await asyncio.get_running_loop().run_in_executor(None, s.multisign, envvars, workdir)
            else:
                result = await asyncio.get_running_loop().run_in_executor(None, s.sign, envvars, workdir)
            if result:
                # Since file streaming happens asynchronously, the temp file we create here
                # could (will) get deleted when closed in this function unless we use delete=False.
                # We want the file to get removed after the response has been sent, so set req.ctx
                # to the temp file's path name so our request handler wrapper deletes it after
                # processing the response.
                outfile = tempfile.NamedTemporaryFile(delete=False)
                req.ctx = outfile.name
                outfile.close()
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
                # See the sign_handler_tegra function for an explanation of what's going on
                # with temp file handling here.
                outfile = tempfile.NamedTemporaryFile(delete=False)
                req.ctx = outfile.name
                outfile.close()
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
