"""Bounded validation and immutable publication of untrusted staging objects.

Signature/container checks are format sanity checks, not malware scanning.
No archives are extracted. The exact validated bytes are written to a fresh
server-only key so a reusable staging PUT cannot change a published file.
"""
import io
import socket
import uuid
import zipfile
from PIL import Image, UnidentifiedImageError

from app.core.config import settings


def _reencode_image(data: bytes, extension: str) -> bytes:
    format_by_extension = {
        ".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG",
        ".webp": "WEBP", ".gif": "GIF",
    }
    try:
        with Image.open(io.BytesIO(data)) as image:
            image.load()
            output = io.BytesIO()
            image.save(output, format=format_by_extension[extension], exif=b"", icc_profile=None, xmp=None)
            return output.getvalue()
    except (KeyError, OSError, UnidentifiedImageError) as exc:
        raise ValueError("Image could not be safely decoded and re-encoded.") from exc


def _scan_with_clamav(data: bytes) -> None:
    if not settings.CLAMAV_HOST:
        return
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=5) as connection:
            connection.sendall(b"zINSTREAM\0")
            for offset in range(0, len(data), 1024 * 1024):
                chunk = data[offset:offset + 1024 * 1024]
                connection.sendall(len(chunk).to_bytes(4, "big") + chunk)
            connection.sendall(b"\x00\x00\x00\x00")
            result = connection.recv(4096).decode("utf-8", errors="replace")
    except OSError as exc:
        raise ValueError("Malware scanner is unavailable.") from exc
    if not result.startswith("stream: OK"):
        raise ValueError("Uploaded file failed malware scanning.")


def valid_file_bytes(data: bytes, extension: str) -> bool:
    if extension in {".jpg", ".jpeg"}:
        return data.startswith(b"\xff\xd8\xff")
    if extension == ".png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if extension == ".gif":
        return data.startswith((b"GIF87a", b"GIF89a"))
    if extension == ".webp":
        return data.startswith(b"RIFF") and data[8:12] == b"WEBP"
    if extension == ".pdf":
        return data.startswith(b"%PDF-")
    if extension in {".doc", ".ppt"}:
        return data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if extension in {".zip", ".docx", ".pptx"}:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                names = set(archive.namelist())
                if extension == ".zip":
                    return True
                main = "word/document.xml" if extension == ".docx" else "ppt/presentation.xml"
                return "[Content_Types].xml" in names and main in names
        except (ValueError, zipfile.BadZipFile):
            return False
    return False


def publish_upload(client, staging_key: str, extension: str, content_type: str, maximum: int, destination_prefix: str):
    response = client.get_object(Bucket=settings.S3_BUCKET_NAME, Key=staging_key)
    stream = response["Body"]
    try:
        if response.get("ContentType") != content_type:
            raise ValueError("Stored content type does not match the file extension.")
        if not 0 < int(response.get("ContentLength", 0)) <= maximum:
            raise ValueError("Uploaded file is empty or exceeds the size limit.")
        data = stream.read(maximum + 1)
    finally:
        stream.close()
    if not 0 < len(data) <= maximum:
        raise ValueError("Uploaded file is empty or exceeds the size limit.")
    if not valid_file_bytes(data, extension):
        raise ValueError("File contents do not match the allowed format.")
    if extension in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        data = _reencode_image(data, extension)
    _scan_with_clamav(data)
    published_key = f"{destination_prefix}published-{uuid.uuid4().hex}{extension}"
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME, Key=published_key, Body=data,
        ContentType=content_type, ContentDisposition="attachment",
    )
    return published_key, len(data)
