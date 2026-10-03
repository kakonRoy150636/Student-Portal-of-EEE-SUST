from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock
import uuid

import pytest

from app.core.uploads import publish_upload, valid_file_bytes
from app.services.resource_service import ResourceService
from tests.conftest import auth_header


@pytest.mark.parametrize("data,ext", [(b'<script>alert(1)</script>', '.pdf'), (b'RIFFxxxxAVI ', '.webp'), (b'fake', '.zip'), (b'%PDF-1.7', '.png')])
def test_reject_mislabeled_bytes(data, ext):
    assert not valid_file_bytes(data, ext)


@pytest.mark.parametrize("size,type_,data", [(26*1024*1024, 'application/pdf', b'%PDF-'), (0, 'application/pdf', b''), (5, 'text/html', b'%PDF-'), (5, 'application/pdf', b'bad!!')])
def test_publication_rejects_untrusted_objects(size, type_, data):
    client = MagicMock()
    stream = BytesIO(data)
    client.get_object.return_value = {"ContentLength": size, "ContentType": type_, "Body": stream}
    with pytest.raises(ValueError):
        publish_upload(client, 'staging.pdf', '.pdf', 'application/pdf', 25*1024*1024, 'resources/user/')
    assert stream.closed
    client.put_object.assert_not_called()


def test_publish_exact_validated_bytes_to_unwritable_key():
    client = MagicMock()
    data = b'%PDF-1.7\nExample'
    client.get_object.return_value = {"ContentLength": len(data), "ContentType": 'application/pdf', "Body": BytesIO(data)}
    key, size = publish_upload(client, 'staging.pdf', '.pdf', 'application/pdf', 100, 'resources/user/')
    assert key.startswith('resources/user/published-')
    assert size == len(data)
    assert client.put_object.call_args.kwargs['Body'] == data
    assert client.put_object.call_args.kwargs['Key'] != 'staging.pdf'


@pytest.mark.asyncio
async def test_presign_rejects_mismatched_mime():
    with pytest.raises(ValueError):
        await ResourceService(MagicMock()).create_presigned_upload(SimpleNamespace(file_name='notes.pdf', mime_type='text/html'), SimpleNamespace(id=uuid.uuid4()))


@pytest.mark.asyncio
async def test_published_avatar_cannot_be_finalized_or_deleted(client, student):
    result = await client.post('/api/v1/auth/avatar-upload/finalize', json={'file_key': f'avatars/{student.id}-published-{uuid.uuid4().hex}.jpg'}, headers=auth_header(student))
    assert result.status_code == 422


def test_real_minio_staging_replay_cannot_change_published_object(monkeypatch):
    import os
    import boto3
    import urllib.request
    from app.core.config import settings
    endpoint = os.environ.get('SECURITY_TEST_S3_ENDPOINT')
    if not endpoint:
        pytest.skip('Requires isolated test MinIO')
    client = boto3.client('s3', endpoint_url=endpoint, aws_access_key_id=settings.S3_ACCESS_KEY, aws_secret_access_key=settings.S3_SECRET_KEY)
    bucket = 'security-test-' + uuid.uuid4().hex
    monkeypatch.setattr(settings, 'S3_BUCKET_NAME', bucket)
    client.create_bucket(Bucket=bucket)
    key = 'resources/test/' + uuid.uuid4().hex + '.pdf'
    try:
        url = client.generate_presigned_url('put_object', Params={'Bucket': bucket, 'Key': key, 'ContentType': 'application/pdf'}, ExpiresIn=300)
        data = b'%PDF-1.7\nvalidated bytes'
        def upload(body):
            req = urllib.request.Request(url, data=body, headers={'Content-Type': 'application/pdf'}, method='PUT')
            with urllib.request.urlopen(req) as response:
                assert response.status == 200
        upload(data)
        published, _ = publish_upload(client, key, '.pdf', 'application/pdf', 1024, 'resources/test/')
        upload(b'<html>replacement</html>')
        result = client.get_object(Bucket=bucket, Key=published)
        try:
            assert result['Body'].read() == data
        finally:
            result['Body'].close()
        with pytest.raises(ValueError):
            publish_upload(client, key, '.pdf', 'application/pdf', 1024, 'resources/test/')
    finally:
        for item in client.list_objects_v2(Bucket=bucket).get('Contents', []):
            client.delete_object(Bucket=bucket, Key=item['Key'])
        client.delete_bucket(Bucket=bucket)
