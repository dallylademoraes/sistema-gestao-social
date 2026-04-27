from typing import Optional
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.usuario import Usuario


def registrar_auditoria(
    db: Session,
    action: str,
    entity_type: str,
    entity_id: Optional[int] = None,
    details: Optional[str] = None,
    actor: Optional[Usuario] = None,
    ip_address: Optional[str] = None,
) -> None:
    log = AuditLog(
        actor_user_id=actor.id if actor else None,
        actor_nome=actor.nome if actor else None,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
