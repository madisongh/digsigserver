import asyncio
import tempfile
from typing import Optional
import re
import os

from sanic import Sanic, request
from sanic.log import logger
from sanic.response import text

from digsigserver.signers.tegrasign import TegraSigner
from digsigserver.signers.imxsign import IMXSigner
from digsigserver.signers.kmodsign import KernelModuleSigner
from digsigserver.signers.opteesign import OPTEESigner
from digsigserver.signers.mendersign import MenderSigner
from digsigserver.signers.swupdsign import SwupdateSigner
from digsigserver.signers.rksign import RockchipSigner
from digsigserver.signers.rkopteesign import RockchipOpteeSigner
from digsigserver.signers.uefisign import UefiSigner
from digsigserver.signers.ueficapsulesign import UefiCapsuleSigner
from digsigserver.signers.ekbsign import EKBSigner
from digsigserver.signers.fitimagesign import FitImageSigner
from . import utils

# Signing can take a loooong time, so set a more reasonable
# default response timeout
CodesignSanicDefaults = {
    'RESPONSE_TIMEOUT': 600,
    'REQUEST_MAX_SIZE': 600000000,
    'L4T_TOOLS_BASE': '/opt/nvidia',
    'IMX_CST_BASE': '/opt/NXP',
    'KEYFILE_URI': 'file:///please/configure/this/path',
    'LOG_LEVEL': 'DEBUG'
}

"""
Actual initialization happens here
"""


def create_app() -> Sanic:
    app = Sanic(name='digsigserver', env_prefix='DIGSIGSERVER_')
    app.config.update_config(CodesignSanicDefaults)
    app.config.load_environment_vars(prefix='DIGSIGSERVER_')
    logger.setLevel(app.config.get("LOG_LEVEL"))
    attach_endpoints(app)
    return app


def config_get(item: str, default_value=None) -> str:
    return Sanic.get_app('digsigserver').config.get(item, default_value)


def validate_upload(req: request, name: str, ok_types: Optional[list] = None) -> request.File:
    if not ok_types:
        ok_types = ["application/octet-stream"]
    f = req.files.get(name)
    return f if f and f.type in ok_types else None


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


async def return_tarball(req: request, workdir: str, return_filename: str = "signed-artifact.tar.gz",
                         files_to_return: Optional[list] = None):
    outfile = tempfile.NamedTemporaryFile(delete=False)
    outfile.close()
    if utils.repack_files(workdir, outfile.name, file_list=files_to_return):
        await return_file(req, outfile.name, return_filename)
        response = None
    else:
        response = text("Signing error", status=500)
    os.unlink(outfile.name)
    return response


def attach_endpoints(app: Sanic):
    @app.post("/sign/tegra")
    async def sign_handler_tegra(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = TegraSigner(app, workdir, req.form.get("machine"), req.form.get("soctype"),
                                req.form.get("bspversion"))
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

    @app.post("/sign/rk")
    async def sign_handler_rk_kernel_fit(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = RockchipSigner(app, workdir, req.form.get("machine"), req.form.get("soctype"))
            except ValueError:
                return text("Invalid parameters", status=400)

            artifact_type = req.form.get("artifact_type").lower()
            burn_key_hash = utils.to_boolean(req.form.get("burn_key_hash", "no"))
            if artifact_type not in ["fit-image", "idblock", "usbloader"]:
                return text("Invalid artifact type", status=400)
            if artifact_type == "fit-image":
                external_data_offset = req.form.get("external_data_offset", "")
                if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files,
                                                                    workdir, f):
                    if await asyncio.get_running_loop().run_in_executor(None, s.sign, artifact_type,
                                                                        burn_key_hash, None, None, external_data_offset):
                        await return_tarball(req, workdir, s.fit_image_output_files)
                        response = None
                    else:
                        response = text("Signing error", status=500)
            else:
                with open(os.path.join(workdir, "artifact"), "wb") as artifact:
                    artifact.write(f.body)
                outfile = tempfile.NamedTemporaryFile(delete=False)
                outfile.close()
                if await asyncio.get_running_loop().run_in_executor(None, s.sign, artifact_type,
                                                                burn_key_hash, artifact.name, outfile.name, None):
                    await return_file(req, outfile.name, "artifact.signed")
                    response = None
                else:
                    response = text("Signing error", status=500)
        return response

    @app.post("/sign/imx")
    async def sign_handler_imx(req: request):
        csf = validate_upload(req, "csf", ok_types=["text/plain"])
        if not csf:
            return text("Invalid CSF", status=400)
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = IMXSigner(app, workdir, req.form.get("machine"), req.form.get("soctype"),
                              req.form.get("cstversion"), req.form.get("backend"))
            except ValueError:
                return text("Invalid parameters", status=400)

            with open(os.path.join(workdir, "csf-input.txt"), "w") as csfinput:
                csfinput.write(csf.body.decode('UTF-8'))
            with open(os.path.join(workdir, f.name), "wb") as artifact:
                artifact.write(f.body)

            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()

            if await asyncio.get_running_loop().run_in_executor(None, s.sign, outfile.name):
                await return_file(req, outfile.name, "artifact.signed")
                response = None
            else:
                response = text("Signing error", status=500)
        return response

    @app.post("/sign/fitimage")
    async def sign_handler_fitimage(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = FitImageSigner(app, workdir)
            except ValueError:
                return text("Invalid parameters", status=400)

            with open(os.path.join(workdir, "artifact"), "wb") as artifact:
                artifact.write(f.body)

            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()
            if await asyncio.get_running_loop().run_in_executor(None, s.sign,
                                   artifact.name,
                                   None,
                                   req.form.get("external_data_offset"),
                                   req.form.get("mark_required"),
                                   req.form.get("algo"),
                                   req.form.get("keyname")):
                await return_file(req, artifact.name, "artifact.signed")
                response = None
            else:
                response = text("Signing error", status=500)
        return response

    @app.post("/sign/modules")
    async def sign_handler_modules(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = KernelModuleSigner(app, workdir, req.form.get("machine"), req.form.get("hashalg", "sha512"))
            except ValueError:
                return text("Invalid parameters", status=400)

            if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
                result = await asyncio.get_running_loop().run_in_executor(None, s.sign)
                if result:
                    return await return_tarball(req, workdir)
        return text("Signing error", status=500)

    @app.post("/sign/tegra/uefi")
    async def sign_handler_uefi(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = UefiSigner(app,
                               workdir,
                               req.form.get("machine"),
                               req.form.get("signing_type"))
            except ValueError:
                return text("Invalid parameters", status=400)

            signing_type = req.form.get("signing_type").lower()
            if signing_type not in ["sbsign", "signature", "attach_signature"]:
                return text("Invalid signing type", status=400)
            with open(os.path.join(workdir, "artifact"), "wb") as artifact:
                artifact.write(f.body)
            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()
            if await asyncio.get_running_loop().run_in_executor(None,
                                                                s.sign,
                                                                artifact.name,
                                                                outfile.name):
                await return_file(req, outfile.name, "artifact.signed")
                response = None
            else:
                response = text("Signing error", status=500)
        os.unlink(outfile.name)
        return response

    @app.post("/sign/tegra/ueficapsule")
    async def sign_handler_uefi_capsule(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = UefiCapsuleSigner(
                    app,
                    workdir,
                    req.form.get("machine"),
                    req.form.get("soctype"),
                    req.form.get("bspversion"),
                    req.form.get("guid"))
            except ValueError:
                return text("Invalid parameters", status=400)

            with open(os.path.join(workdir, "artifact"), "wb") as artifact:
                artifact.write(f.body)
            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()
            if await asyncio.get_running_loop().run_in_executor(None,
                                                                s.generate_signed_capsule,
                                                                artifact.name,
                                                                outfile.name):
                await return_file(req, outfile.name, "artifact.cap")
                response = None
            else:
                response = text("Signing error", status=500)
        os.unlink(outfile.name)
        return response

    @app.post("/sign/optee")
    async def sign_handler_optee(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = OPTEESigner(app, workdir, req.form.get("machine"))
            except ValueError:
                return text("Invalid parameters", status=400)

            if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
                result = await asyncio.get_running_loop().run_in_executor(None, s.sign)
                if result:
                    return await return_tarball(req, workdir)
        return text("Signing error", status=500)

    @app.post("/sign/rkoptee-tee")
    async def sign_handler_rk_optee_tee(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = RockchipOpteeSigner(app, workdir, req.form.get("machine"))
            except ValueError:
                return text("Invalid parameters", status=400)
            with open(os.path.join(workdir, "tee.bin"), "wb") as artifact:
                artifact.write(f.body)
            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()
            if await asyncio.get_running_loop().run_in_executor(None, s.resign_tee,
                                                                os.path.join(workdir, "tee.bin"),
                                                                outfile.name):
                await return_file(req, outfile.name, "tee.bin.signed")
                response = None
            else:
                response = text("Signing error", status=500)
        os.unlink(outfile.name)
        return response

    @app.post("/sign/rkoptee-ta")
    async def sign_handler_rk_optee_ta(req: request):
        f = validate_upload(req, "artifact")
        if not f:
            return text("Invalid artifact", status=400)
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = RockchipOpteeSigner(app, workdir, req.form.get("machine"))
            except ValueError:
                return text("Invalid parameters", status=400)

            if await asyncio.get_running_loop().run_in_executor(None, utils.extract_files, workdir, f):
                result = await asyncio.get_running_loop().run_in_executor(None, s.resign_tas)
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
                s = SwupdateSigner(app, workdir, distro)
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
                s = MenderSigner(app, workdir, distro, artifact)
            except ValueError:
                return text("Invalid parameters", status=400)
            if await asyncio.get_running_loop().run_in_executor(None, s.sign):
                return text("Signing successful")
        return text("Signing error", status=500)


    @app.post("/sign/tegra/ekb")
    async def get_handler_ekb(req: request):
        with tempfile.TemporaryDirectory() as workdir:
            try:
                s = EKBSigner(
                    app,
                    workdir,
                    req.form.get("machine"),
                    req.form.get("soctype"),
                    req.form.get("bspversion"))
            except ValueError:
                return text("Invalid parameters", status=400)

            outfile = tempfile.NamedTemporaryFile(delete=False)
            outfile.close()
            if await asyncio.get_running_loop().run_in_executor(None,
                                                                s.generate_ekb,
                                                                outfile.name):
                await return_file(req, outfile.name, "ekb.img")
                response = None
            else:
                response = text("Signing error", status=500)
        os.unlink(outfile.name)
        return response
