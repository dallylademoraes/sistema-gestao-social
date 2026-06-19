import logging
from functools import lru_cache

from b2sdk.v2 import B2Api, InMemoryAccountInfo
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_b2_api() -> B2Api:
    """
    Inicializa e retorna uma instância da B2Api.
    Usa lru_cache para garantir que a inicialização ocorra apenas uma vez.
    """
    info = InMemoryAccountInfo()
    b2_api = B2Api(info)
    try:
        b2_api.authorize_account(
            "production",
            settings.B2_APP_KEY_ID,
            settings.B2_APP_KEY,
        )
        logger.info("Autorização com Backblaze B2 bem-sucedida.")
    except Exception:
        logger.exception("Falha ao autorizar com a API do Backblaze B2.")
        raise HTTPException(
            status_code=500,
            detail="Configuração do serviço de armazenamento está incorreta.",
        )
    return b2_api


def delete_file_from_b2(file_name: str, file_id: str):
    """
    Apaga um arquivo do bucket no Backblaze B2.
    """
    if not all([settings.B2_BUCKET_NAME, file_name, file_id]):
        logger.warning("Tentativa de apagar arquivo sem nome, ID ou nome do bucket.")
        return

    try:
        b2_api = get_b2_api()
        bucket = b2_api.get_bucket_by_name(settings.B2_BUCKET_NAME)
        bucket.delete_file_version(file_id, file_name)
        logger.info("Arquivo '%s' (ID: %s) apagado do Backblaze B2.", file_name, file_id)
    except Exception:
        logger.exception("Falha ao apagar o arquivo '%s' do Backblaze B2.", file_name)
        # Não lançamos exceção para não impedir a exclusão do cadastro no banco