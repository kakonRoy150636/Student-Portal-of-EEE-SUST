"""Bounded validation and immutable publication of untrusted staging objects.

Signature/container checks are format sanity checks, not malware scanning.
No archives are extracted. The exact validated bytes are written to a fresh
server-only key so a reusable staging PUT cannot change a published file.
"""
import io
import uuid
import zipfile

from app.core.config import settings


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
    published_key = f"{destination_prefix}published-{uuid.uuid4().hex}{extension}"
    client.put_object(
        Bucket=settings.S3_BUCKET_NAME, Key=published_key, Body=data,
        ContentType=content_type, ContentDisposition="attachment",
    )
    return published_key, len(data)
