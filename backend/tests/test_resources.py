"""Resource upload / verification / download.

The object store is substituted with an in-memory fake so these run without
MinIO. What is being tested is the *policy* around storage -- extension and
magic-byte checks, generated keys, ownership, listing only verified rows, and
the attachment-only download URL -- not boto3 itself.
"""
import uuid

import pytest

from app.services import resource_service as resource_service_module
from app.services.resource_service import MAX_RESOURCE_BYTES, ResourceService
from app.services.resource_storage import StorageError, StoredObject
from tests.conftest import auth_header, make_user

pytestmark = pytest.mark.asyncio

PDF_BYTES = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


class FakeStorage:
    """Minimal stand-in for S3Storage."""

    def __init__(self):
        self.objects: dict[str, tuple[bytes, str]] = {}
        self.deleted: list[str] = []
        self.fail_upload = False

    def upload(self, key, data, content_type):
        if self.fail_upload:
            raise StorageError("boom")
        self.objects[key] = (data, content_type)

    def head(self, key):
        if key not in self.objects:
            return None
        data, content_type = self.objects[key]
        return StoredObject(size=len(data), content_type=content_type)

    def read_prefix(self, key, length=12):
        return self.objects.get(key, (b"", ""))[0][:length]

    def presign_get(self, key, *, filename, expires_in=300):
        # A URL shaped like the real one but scoped to the fake key.
        return f"https://storage.test/{key}?download={filename}&expires={expires_in}"

    def delete(self, key):
        self.deleted.append(key)
        self.objects.pop(key, None)


@pytest.fixture
def storage():
    return FakeStorage()


@pytest.fixture
def client_with_fake_storage(client, monkeypatch, storage):
    """Route the endpoint's S3Storage construction to the fake."""
    monkeypatch.setattr(
        resource_service_module, "S3Storage", lambda *a, **k: storage
    )
    return client


async def _upload(client, user, *, filename="notes.pdf", content=PDF_BYTES, **form):
    data = {
        "title": form.pop("title", "Machines II notes"),
        "category": form.pop("category", "lecture-note"),
    }
    data.update(form)
    return await client.post(
        "/api/v1/resources",
        files={"file": (filename, content, "application/pdf")},
        data=data,
        headers=auth_header(user),
    )


async def test_upload_requires_authentication(client, db):
    response = await client.post(
        "/api/v1/resources",
        files={"file": ("notes.pdf", PDF_BYTES, "application/pdf")},
        data={"title": "Notes", "category": "lecture-note"},
    )
    assert response.status_code == 401


async def test_upload_stores_generated_key_and_lists_without_it(
    client_with_fake_storage, storage, db
):
    user = await make_user(db)
    response = await _upload(client_with_fake_storage, user)
    assert response.status_code == 201, response.text
    body = response.json()["resource"]

    # The client never chooses, and never sees, the storage key.
    assert "file_key" not in body
    key, = storage.objects.keys()
    assert key.startswith(f"resources/{user.id}/")
    assert key.endswith(".pdf")
    assert storage.objects[key][1] == "application/pdf"

    listing = await client_with_fake_storage.get(
        "/api/v1/resources/search", headers=auth_header(user)
    )
    assert listing.status_code == 200
    assert [row["id"] for row in listing.json()] == [body["id"]]
    assert "file_key" not in listing.json()[0]


async def test_upload_rejects_extension_that_is_not_allowed(client_with_fake_storage, db):
    user = await make_user(db)
    response = await _upload(
        client_with_fake_storage, user, filename="payload.html", content=b"<script>x</script>"
    )
    assert response.status_code == 422
    assert "Unsupported file type" in response.json()["error"]


async def test_upload_rejects_content_that_contradicts_its_extension(
    client_with_fake_storage, db
):
    user = await make_user(db)
    response = await _upload(client_with_fake_storage, user, content=b"just text, not a pdf")
    assert response.status_code == 422
    assert "do not match its extension" in response.json()["error"]


async def test_upload_rejects_oversized_file(client_with_fake_storage, db):
    user = await make_user(db)
    oversized = b"%PDF-" + b"0" * (MAX_RESOURCE_BYTES + 16)
    response = await _upload(client_with_fake_storage, user, content=oversized)
    assert response.status_code == 422
    assert "MB or smaller" in response.json()["error"]


async def test_upload_rejects_unknown_course_code(client_with_fake_storage, db):
    user = await make_user(db)
    response = await _upload(client_with_fake_storage, user, course_code="EEE 999")
    assert response.status_code == 422
    assert "Unknown course code" in response.json()["error"]


async def test_download_returns_attachment_url_and_counts(
    client_with_fake_storage, storage, db
):
    user = await make_user(db)
    created = await _upload(client_with_fake_storage, user)
    resource_id = created.json()["resource"]["id"]

    response = await client_with_fake_storage.get(
        f"/api/v1/resources/{resource_id}/download", headers=auth_header(user)
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["download_url"].startswith("https://storage.test/resources/")
    assert body["file_name"] == "notes.pdf"
    assert body["expires_in"] == 300

    listing = await client_with_fake_storage.get(
        "/api/v1/resources/search", headers=auth_header(user)
    )
    assert listing.json()[0]["download_count"] == 1


async def test_download_of_unknown_resource_is_404(client_with_fake_storage, db):
    user = await make_user(db)
    response = await client_with_fake_storage.get(
        f"/api/v1/resources/{uuid.uuid4()}/download", headers=auth_header(user)
    )
    assert response.status_code == 404


async def test_pending_resource_is_not_listed_or_downloadable(
    client_with_fake_storage, db
):
    """A row is only 'ready' once the object was verified, so nothing else is visible."""
    user = await make_user(db)
    resource = await ResourceService(db, storage=FakeStorage()).upload(
        user,
        filename="notes.pdf",
        data=PDF_BYTES,
        title="Hidden",
        description=None,
        category="lecture-note",
        course_code=None,
    )
    row = await db.get(
        __import__("app.models.resource", fromlist=["AcademicResource"]).AcademicResource,
        resource.id,
    )
    row.status = "pending"
    await db.commit()

    listing = await client_with_fake_storage.get(
        "/api/v1/resources/search", headers=auth_header(user)
    )
    assert listing.json() == []
    download = await client_with_fake_storage.get(
        f"/api/v1/resources/{resource.id}/download", headers=auth_header(user)
    )
    assert download.status_code == 404


async def test_delete_is_limited_to_owner_or_admin(client_with_fake_storage, storage, db):
    owner = await make_user(db)
    other = await make_user(db, identifier="2023999999", email="other@sust.edu")
    created = await _upload(client_with_fake_storage, owner)
    resource_id = created.json()["resource"]["id"]

    forbidden = await client_with_fake_storage.delete(
        f"/api/v1/resources/{resource_id}", headers=auth_header(other)
    )
    assert forbidden.status_code == 403

    removed = await client_with_fake_storage.delete(
        f"/api/v1/resources/{resource_id}", headers=auth_header(owner)
    )
    assert removed.status_code == 204
    assert storage.deleted and not storage.objects


async def test_search_escapes_like_wildcards(client_with_fake_storage, db):
    """`%` is a literal character in a search term, not a wildcard."""
    user = await make_user(db)
    await _upload(client_with_fake_storage, user, title="100% coverage notes")

    all_rows = await client_with_fake_storage.get(
        "/api/v1/resources/search", headers=auth_header(user)
    )
    assert len(all_rows.json()) == 1

    literal = await client_with_fake_storage.get(
        "/api/v1/resources/search", params={"q": "100%"}, headers=auth_header(user)
    )
    assert len(literal.json()) == 1

    wildcard = await client_with_fake_storage.get(
        "/api/v1/resources/search", params={"q": "zzz%"}, headers=auth_header(user)
    )
    assert wildcard.json() == []


async def test_storage_outage_is_reported_not_swallowed(client_with_fake_storage, storage, db):
    user = await make_user(db)
    storage.fail_upload = True
    response = await _upload(client_with_fake_storage, user)
    assert response.status_code == 409
    assert "storage is unavailable" in response.json()["error"].lower()
