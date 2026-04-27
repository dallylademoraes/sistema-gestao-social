from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
import os
import uuid

from fastapi import HTTPException, UploadFile
from fastapi.responses import FileResponse, RedirectResponse, Response
from jose import JWTError, jwt

from app.core.config import settings


BASE_UPLOAD_DIR = Path("uploads")
BASE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

TIPOS_PERMITIDOS = {
    "foto": {"image/jpeg", "image/png", "image/webp"},
    "comprovante": {"application/pdf", "image/jpeg", "image/png", "image/webp"},
    "documento": {"application/pdf", "image/jpeg", "image/png", "image/webp"},
    "termo_imagem": {"application/pdf", "image/jpeg", "image/png", "image/webp"},
    "termo_lgpd": {"application/pdf", "image/jpeg", "image/png", "image/webp"},
}

EXT_PERMITIDAS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "application/pdf": ".pdf",
}


@dataclass
class ArquivoSeguro:
    storage_ref: str
    filename: str
    content_type: str
    size: int


def _provider() -> str:
    return (getattr(settings, "STORAGE_PROVIDER", "local") or "local").lower()


def _max_bytes() -> int:
    return int(getattr(settings, "UPLOAD_MAX_BYTES", 10 * 1024 * 1024))


def _extensao_por_nome(nome: str) -> str:
    return os.path.splitext(nome or "")[1].lower()


def _antivirus_basico(content: bytes) -> None:
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"
    if eicar in content:
        raise HTTPException(status_code=400, detail="Arquivo bloqueado pelo antivírus básico")
    if content[:2] == b"MZ":
        raise HTTPException(status_code=400, detail="Executáveis não são permitidos")


async def validar_arquivo_upload(tipo: str, arquivo: UploadFile) -> tuple[ArquivoSeguro, bytes]:
    if tipo not in TIPOS_PERMITIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {list(TIPOS_PERMITIDOS)}")

    conteúdo = await arquivo.read()
    if not conteúdo:
        raise HTTPException(status_code=400, detail="Arquivo vazio")
    if len(conteúdo) > _max_bytes():
        raise HTTPException(status_code=400, detail="Arquivo excede o tamanho máximo permitido")

    _antivirus_basico(conteúdo)

    content_type = (arquivo.content_type or "").lower()
    if content_type not in TIPOS_PERMITIDOS[tipo]:
        raise HTTPException(status_code=400, detail="Tipo MIME não permitido para este documento")

    ext = _extensao_por_nome(arquivo.filename)
    if ext and ext not in set(EXT_PERMITIDAS.values()):
        raise HTTPException(status_code=400, detail="Extensão de arquivo não permitida")

    expected_ext = EXT_PERMITIDAS.get(content_type)
    if expected_ext and ext and ext != expected_ext:
        raise HTTPException(status_code=400, detail="Extensão não corresponde ao tipo do arquivo")

    nome_unico = f"{uuid.uuid4().hex}{expected_ext or ext or ''}"
    return (
        ArquivoSeguro(
            storage_ref=nome_unico,
            filename=nome_unico,
            content_type=content_type or "application/octet-stream",
            size=len(conteúdo),
        ),
        conteúdo,
    )


def salvar_arquivo_local(storage_ref: str, conteúdo: bytes) -> str:
    destino = BASE_UPLOAD_DIR / storage_ref
    destino.write_bytes(conteúdo)
    return storage_ref


def _s3_client():
    try:
        import boto3  # type: ignore
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="boto3 não está instalado para STORAGE_PROVIDER=s3") from exc
    return boto3.client("s3", region_name=getattr(settings, "S3_REGION", None) or None)


def _blob_service_client():
    try:
        from azure.storage.blob import BlobServiceClient  # type: ignore
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="azure-storage-blob não está instalado para STORAGE_PROVIDER=blob") from exc
    conn = getattr(settings, "BLOB_CONNECTION_STRING", None)
    if not conn:
        raise HTTPException(status_code=500, detail="BLOB_CONNECTION_STRING ausente")
    return BlobServiceClient.from_connection_string(conn)


def salvar_arquivo_externo(storage_ref: str, conteúdo: bytes, content_type: str) -> str:
    provider = _provider()
    if provider == "s3":
        bucket = getattr(settings, "S3_BUCKET_NAME", None)
        if not bucket:
            raise HTTPException(status_code=500, detail="S3_BUCKET_NAME ausente")
        client = _s3_client()
        client.put_object(Bucket=bucket, Key=storage_ref, Body=conteúdo, ContentType=content_type)
        return storage_ref
    if provider == "blob":
        container = getattr(settings, "BLOB_CONTAINER_NAME", None)
        if not container:
            raise HTTPException(status_code=500, detail="BLOB_CONTAINER_NAME ausente")
        service = _blob_service_client()
        blob = service.get_blob_client(container=container, blob=storage_ref)
        blob.upload_blob(conteúdo, overwrite=True, content_type=content_type)
        return storage_ref
    return salvar_arquivo_local(storage_ref, conteúdo)


def gerar_token_download(cadastro_id: int, tipo: str, storage_ref: str) -> str:
    payload = {
        "sub": f"cadastro:{cadastro_id}:{tipo}",
        "ref": storage_ref,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def gerar_url_assinada_download(cadastro_id: int, tipo: str, storage_ref: str) -> str:
    token = gerar_token_download(cadastro_id, tipo, storage_ref)
    return f"/api/cadastros/{cadastro_id}/documentos/{tipo}/baixar?token={token}"


def verificar_token_download(token: str, cadastro_id: int, tipo: str) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Token de download inválido ou expirado") from exc
    esperado = f"cadastro:{cadastro_id}:{tipo}"
    if payload.get("sub") != esperado:
        raise HTTPException(status_code=401, detail="Token de download não corresponde ao recurso")
    storage_ref = payload.get("ref")
    if not storage_ref:
        raise HTTPException(status_code=401, detail="Token de download inválido")
    return storage_ref


def responder_download(storage_ref: str, filename: str, content_type: str) -> Response:
    provider = _provider()
    if provider == "s3":
        bucket = getattr(settings, "S3_BUCKET_NAME", None)
        if not bucket:
            raise HTTPException(status_code=500, detail="S3_BUCKET_NAME ausente")
        client = _s3_client()
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": storage_ref},
            ExpiresIn=900,
        )
        return RedirectResponse(url=url, status_code=302)
    if provider == "blob":
        container = getattr(settings, "BLOB_CONTAINER_NAME", None)
        if not container:
            raise HTTPException(status_code=500, detail="BLOB_CONTAINER_NAME ausente")
        service = _blob_service_client()
        blob = service.get_blob_client(container=container, blob=storage_ref)
        try:
            from azure.storage.blob import generate_blob_sas, BlobSasPermissions  # type: ignore
        except ImportError as exc:
            raise HTTPException(status_code=500, detail="azure-storage-blob não está instalado para URL assinada") from exc
        sas = generate_blob_sas(
            account_name=service.account_name,
            container_name=container,
            blob_name=storage_ref,
            account_key=service.credential.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(minutes=15),
        )
        return RedirectResponse(url=f"{blob.url}?{sas}", status_code=302)

    caminho = Path(storage_ref)
    if not caminho.exists():
        caminho = BASE_UPLOAD_DIR / storage_ref
    if not caminho.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return FileResponse(path=str(caminho), filename=filename, media_type=content_type)
