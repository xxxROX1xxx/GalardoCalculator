from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QIODevice, QObject, QTemporaryFile, QUrl, Signal
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from . import __version__

REPOSITORY = "xxxROX1xxx/GalardoCalculator"
RELEASES_URL = f"https://github.com/{REPOSITORY}/releases"
LATEST_RELEASE_URL = f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
UPDATE_FAILED_ARG = "--update-failed"
MAX_METADATA_SIZE = 1_000_000
MAX_DOWNLOAD_SIZE = 256 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class Release:
    tag: str
    size: int
    sha256: str

    @property
    def page(self) -> str:
        return f"{RELEASES_URL}/tag/{self.tag}"

    @property
    def download_url(self) -> str:
        return f"{RELEASES_URL}/download/{self.tag}/Galardo.exe"


def _version(value: object) -> tuple[int, int, int]:
    match = re.fullmatch(r"v?([0-9]{1,9})\.([0-9]{1,9})\.([0-9]{1,9})", str(value))
    if match is None:
        raise ValueError("Не удалось прочитать номер версии")
    major, minor, patch = match.groups()
    return int(major), int(minor), int(patch)


def newer_release(payload: object, current_version: str) -> Release | None:
    if not isinstance(payload, dict):
        raise ValueError("Не удалось прочитать данные релиза")
    tag = str(payload.get("tag_name", ""))
    if payload.get("draft") or payload.get("prerelease"):
        return None
    if _version(tag) <= _version(current_version):
        return None

    assets = payload.get("assets")
    for asset in assets if isinstance(assets, list) else ():
        if not isinstance(asset, dict) or asset.get("name") != "Galardo.exe":
            continue
        digest = re.fullmatch(r"sha256:([a-fA-F0-9]{64})", str(asset.get("digest", "")))
        size = asset.get("size")
        if digest is not None and type(size) is int and 0 < size <= MAX_DOWNLOAD_SIZE:
            release = Release(tag, size, digest[1].lower())
            if asset.get("browser_download_url") == release.download_url:
                return release
    raise ValueError("В релизе нет проверяемого Galardo.exe")


_INSTALL_UPDATE = r"""
$ErrorActionPreference = 'Stop'
$target = $env:GALARDO_UPDATE_TARGET
$staged = $env:GALARDO_UPDATE_STAGED
$backup = $staged + '.bak'
$directory = [IO.Path]::GetDirectoryName($target)
try {
    $app = Get-Process -Id $env:GALARDO_UPDATE_PID -ErrorAction SilentlyContinue
    if ($null -ne $app -and -not $app.WaitForExit(15000)) {
        throw 'The application did not exit'
    }
    if ((Get-FileHash -LiteralPath $staged -Algorithm SHA256).Hash -ne $env:GALARDO_UPDATE_SHA256) {
        throw 'The downloaded file changed'
    }
    # The PyInstaller bootloader can still hold the file briefly.
    $deadline = [DateTime]::UtcNow.AddSeconds(10)
    while ($true) {
        try {
            [IO.File]::Replace($staged, $target, $backup)
            break
        } catch [IO.IOException] {
            if ([DateTime]::UtcNow -ge $deadline) { throw }
            Start-Sleep -Milliseconds 250
        }
    }
    try {
        Start-Process -FilePath $target -WorkingDirectory $directory
    } catch {
        [IO.File]::Replace($backup, $target, [NullString]::Value)
        throw
    }
} catch {
    if (-not [IO.File]::Exists($target) -and [IO.File]::Exists($backup)) {
        [IO.File]::Move($backup, $target)
    }
    Start-Process -FilePath $target -WorkingDirectory $directory -ArgumentList '--update-failed'
} finally {
    [IO.File]::Delete($staged)
}
[IO.File]::Delete($backup)
"""


def _start_installer(target: Path, staged: Path, digest: str) -> None:
    powershell = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    env = os.environ.copy()
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        bundle_path = os.path.normcase(os.path.normpath(bundle))
        env["PATH"] = os.pathsep.join(
            entry for entry in env.get("PATH", "").split(os.pathsep)
            if os.path.normcase(os.path.normpath(entry)) != bundle_path
        )
    env.update(
        GALARDO_UPDATE_TARGET=str(target),
        GALARDO_UPDATE_STAGED=str(staged),
        GALARDO_UPDATE_SHA256=digest,
        GALARDO_UPDATE_PID=str(os.getpid()),
        PYINSTALLER_RESET_ENVIRONMENT="1",
    )
    command = base64.b64encode(_INSTALL_UPDATE.encode("utf-16-le")).decode("ascii")
    # System PowerShell must load its own DLLs outside the bundled directory.
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    set_dll_directory = kernel.SetDllDirectoryW
    set_dll_directory.argtypes = (ctypes.c_wchar_p,)
    set_dll_directory.restype = ctypes.c_int
    if bundle and not set_dll_directory(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        subprocess.Popen(
            [str(powershell), "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", command],
            cwd=powershell.parent,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
    finally:
        if bundle:
            set_dll_directory(bundle)


class AppUpdater(QObject):
    statusChanged = Signal(str, bool)
    available = Signal(object)
    downloaded = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.target = (
            Path(sys.executable).resolve()
            if sys.platform == "win32" and getattr(sys, "frozen", False)
            else None
        )
        self._network = QNetworkAccessManager(self)
        self._reply: QNetworkReply | None = None
        self._file: QTemporaryFile | None = None

    def check(self) -> None:
        if self._reply is not None or self._file is not None:
            return
        self.statusChanged.emit("Проверяем обновления…", True)
        reply = self._get(LATEST_RELEASE_URL, b"application/vnd.github+json")
        reply.readyRead.connect(
            lambda: reply.abort() if reply.bytesAvailable() > MAX_METADATA_SIZE else None
        )
        reply.finished.connect(lambda: self._checked(reply))

    def _get(self, url: str, accept: bytes) -> QNetworkReply:
        request = QNetworkRequest(QUrl(url))
        request.setTransferTimeout(30000)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        request.setRawHeader(b"Accept", accept)
        request.setRawHeader(b"User-Agent", f"Galardo/{__version__}".encode("ascii"))
        self._reply = self._network.get(request)
        return self._reply

    def _checked(self, reply: QNetworkReply) -> None:
        if reply is not self._reply:
            return
        self._reply = None
        reply.deleteLater()
        if reply.error() != QNetworkReply.NetworkError.NoError:
            self.statusChanged.emit("Не удалось проверить обновления", False)
            return
        try:
            payload = json.loads(bytes(reply.readAll()))
        except (json.JSONDecodeError, UnicodeError):
            self.statusChanged.emit("Не удалось прочитать данные релиза", False)
            return
        try:
            release = newer_release(payload, __version__)
        except ValueError as error:
            self.statusChanged.emit(str(error), False)
            return
        if release is None:
            self.statusChanged.emit(f"Версия {__version__} актуальна", False)
        else:
            self.available.emit(release)

    def download(self, release: Release) -> None:
        if self.target is None or self._reply is not None or self._file is not None:
            return
        staged = QTemporaryFile(str(self.target.parent / ".Galardo-XXXXXX.download"), self)
        if not staged.open(QIODevice.OpenModeFlag.WriteOnly):
            staged.deleteLater()
            self.statusChanged.emit("Нет доступа для записи в папку приложения", False)
            return
        self._file = staged
        self.statusChanged.emit("Загружаем обновление…", True)
        reply = self._get(release.download_url, b"application/octet-stream")
        reply.setReadBufferSize(1024 * 1024)
        digest = hashlib.sha256()
        written = 0
        failure = ""

        def drain() -> None:
            nonlocal written, failure
            if reply is not self._reply or failure:
                return
            chunk = bytes(reply.readAll())
            if written + len(chunk) > release.size:
                failure = "Размер обновления не совпадает с релизом"
            elif staged.write(chunk) != len(chunk):
                failure = "Не удалось сохранить обновление"
            else:
                written += len(chunk)
                digest.update(chunk)

        def read_chunk() -> None:
            drain()
            if failure:
                reply.abort()

        def finish() -> None:
            if reply is not self._reply:
                return
            drain()
            self._reply = None
            reply.deleteLater()
            if not failure and reply.error() != QNetworkReply.NetworkError.NoError:
                self.discard("Не удалось скачать обновление")
            elif failure:
                self.discard(failure)
            elif written != release.size or digest.hexdigest() != release.sha256:
                self.discard("Не удалось проверить скачанный файл")
            elif not staged.flush():
                self.discard("Не удалось сохранить обновление")
            else:
                staged.close()
                self.downloaded.emit(release)

        reply.readyRead.connect(read_chunk)
        reply.finished.connect(finish)

    def install(self, release: Release) -> bool:
        staged = self._file
        if staged is None or self.target is None:
            return False
        try:
            _start_installer(self.target, Path(staged.fileName()), release.sha256)
        except OSError:
            self.discard("Не удалось запустить установку обновления")
            return False
        staged.setAutoRemove(False)
        staged.deleteLater()
        self._file = None
        return True

    def discard(self, message: str = "") -> None:
        staged, self._file = self._file, None
        if staged is not None:
            staged.close()
            staged.remove()
            staged.deleteLater()
        if message:
            self.statusChanged.emit(message, False)

    def cancel(self) -> None:
        reply, self._reply = self._reply, None
        if reply is not None:
            reply.abort()
            reply.deleteLater()
        self.discard()
