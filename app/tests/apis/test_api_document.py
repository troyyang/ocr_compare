# tests/test_data_source.py
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
import main
import core.config as config
import pytest
import asyncio
from datetime import datetime
from models.models import DocumentStatus
from services.document_service import DocumentService
from schemas.document import DocumentView
import json

username = "admin"
email = "admin@example.com"
password = "admin"

@pytest.fixture(autouse=True)
def setup_function(monkeypatch) -> None:
    monkeypatch.setattr(config, 'API_ENV', 'test')
    def mock_perm(doc_id, token):
        return 'FULL_CONTROL'
    import services.document_service
    monkeypatch.setattr(services.document_service, "request_doc_permissions", mock_perm)
    yield

@pytest_asyncio.fixture(loop_scope="module")
async def client(monkeypatch):
    config.API_ENV = 'test' 
    config.IS_CAMEL_CASE = False

    transport = ASGITransport(app=main.create_app())
    async with AsyncClient(base_url="http://test", transport=transport) as ac:
        yield ac

@pytest_asyncio.fixture(loop_scope="module")
async def document_service() -> DocumentService:
    document_service = DocumentService()
    yield document_service

@pytest_asyncio.fixture(loop_scope="module")
async def setup_test_data(client: AsyncClient) -> tuple[str, str]:
    """ 
    Setup test data
    """
    response = await client.post("/api/auth/login", json={
        "username": username,
        "password": password
    })
    assert response.status_code == 200
    data = response.json()["data"]
    valid_token = f"Bearer {data['token']}"
    yield valid_token

@pytest.mark.asyncio(loop_scope="module")
async def test_create_document(client: AsyncClient, setup_test_data: str, document_service: DocumentService):
    """Test valid tag creation"""
    valid_token = setup_test_data
    response = await client.put("/api/documents", headers={
        "Authorization": valid_token
    }, json={
        "title": "jQuery JavaScript库", 
        "abstract": "jQuery is a fast, small, and feature-rich JavaScript library.", 
        "department_code": "AS", 
        "code": "01", 
        "current_version": "1.0.0", 
        "status": DocumentStatus.draft
    })
    
    assert response.status_code == 200
    document = response.json()["data"]
    assert document["title"] == "jQuery JavaScript库"
    assert document["abstract"] == "jQuery is a fast, small, and feature-rich JavaScript library."
    document_service.delete_document(str(document["id"]), "admin")

@pytest.mark.asyncio(loop_scope="module")
async def test_update_document(client: AsyncClient, setup_test_data: str, document_service: DocumentService):
    """Test valid tag creation"""
    valid_token = setup_test_data
    document_id = "b0a0a1a2-3c4d-5e6f-7a8b-9c0d1e2f3a4b"
    document_view = {
        "id": str(document_id), 
        "title": "技术文档系统架构设计update", 
        "abstract": "技术文档系统架构设计update", 
        "department_code": "AS", 
        "code": "01", 
        "current_version": "1.0.0", 
        "status": DocumentStatus.draft
    }
    response = await client.put("/api/documents", headers={
        "Authorization": valid_token
    }, json=document_view)
    
    assert response.status_code == 200
    document_data = response.json()["data"]
    assert document_data["title"] == "技术文档系统架构设计update"
    assert document_data["abstract"] == "技术文档系统架构设计update"

    document = document_service.save_document(DocumentView(id=document_id, 
                                                title="技术文档系统架构设计", 
                                                abstract=None, 
                                                proposer_id=["admin"], 
                                                department_code = "IT",
                                                code = "ARCH-001",
                                                current_version="1.0.0", 
                                                status=DocumentStatus.draft), "admin", "token")
    assert document is not None
    assert document.title == "技术文档系统架构设计"
    document = document_service.get_document_by_id(str(document.id))
    assert document is not None
    assert document.title == "技术文档系统架构设计"


@pytest.mark.asyncio(loop_scope="module")
async def test_find_document_by_id(client: AsyncClient, setup_test_data: str, document_service: DocumentService):
    """Test valid tag retrieval"""
    valid_token = setup_test_data
    document_id = "b0a0a1a2-3c4d-5e6f-7a8b-9c0d1e2f3a4b"
    response = await client.get(f"/api/documents/find/{document_id}", headers={
        "Authorization": valid_token
    })
    assert response.status_code == 200
    document = response.json()["data"]
    print(json.dumps(document, indent=4, ensure_ascii=False))
    assert document["title"] == "技术文档系统架构设计"
    assert document["abstract"] == None

@pytest.mark.asyncio(loop_scope="module")
async def test_find_documents_by_condition(client: AsyncClient, setup_test_data: str, document_service: DocumentService):
    """Test valid tag retrieval"""
    valid_token = setup_test_data
    from_time = '2025-06-11 00:00:00'
    title = "技术文档系统架构设计"
    department_code = "IT"
    code = "ARCH-001"
    response = await client.post(f"/api/documents", headers={
        "Authorization": valid_token,
    }, json={
        "current": 1,
        "page_size": 10,
        "from_time": from_time,
        "title": title,
        "department_code": department_code,
        "code": code,
        "proposer_id": "admin",
        "sort_by": "created_at",
        "desc": True
    })
    assert response.status_code == 200
    result = response.json()["data"]
    print(json.dumps(result, indent=4, ensure_ascii=False))
    assert result["total"] == 1
    assert len(result["documents"]) == 1