from __future__ import annotations

import sys
import traceback
import uuid
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.services.arquivos import _s3_client  # noqa: E402


def _mask(value: str | None) -> str:
    if not value:
        return "<ausente>"
    if len(value) <= 6:
        return "***"
    return f"{value[:4]}...{value[-2:]}"


def main() -> int:
    bucket = settings.S3_BUCKET_NAME
    if not bucket:
        print("ERRO: S3_BUCKET_NAME ausente no .env")
        return 2

    endpoint = (settings.S3_ENDPOINT_URL or "").strip().rstrip("/")
    key = f"diagnostics/codex-b2-test-{uuid.uuid4().hex}.txt"
    body = b"teste de conexao Backblaze B2 via boto3\n"

    print("Diagnostico Backblaze B2/S3")
    print(f"bucket: {bucket}")
    print(f"endpoint: {endpoint or '<padrao boto3>'}")
    print(f"region: {settings.S3_REGION or '<ausente>'}")
    print(f"verify_ssl: {settings.S3_VERIFY_SSL}")
    print(f"key_id: {_mask(settings.B2_APPLICATION_KEY_ID)}")
    print(f"objeto_teste: {key}")

    try:
        client = _s3_client()
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="text/plain; charset=utf-8",
            ContentLength=len(body),
        )
        print("UPLOAD_OK")

        client.head_object(Bucket=bucket, Key=key)
        print("HEAD_OK")

        client.delete_object(Bucket=bucket, Key=key)
        print("DELETE_OK")
        return 0
    except Exception:
        print("ERRO_COMPLETO:")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
