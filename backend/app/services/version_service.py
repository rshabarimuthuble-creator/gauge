from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_version import AgentVersion
from app.schemas.agent_version import AgentVersionCreate
from app.core.logging import logger


class VersionService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[AgentVersion]:
        """Fetch all registered agent versions ordered by creation date descending."""
        stmt = select(AgentVersion).order_by(AgentVersion.created_at.desc()).offset(skip).limit(limit)
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_by_id(db: Session, version_id: str) -> Optional[AgentVersion]:
        """Fetch an agent version by its unique ID."""
        return db.get(AgentVersion, version_id)

    @staticmethod
    def create(db: Session, version_in: AgentVersionCreate) -> AgentVersion:
        """Register a new agent snapshot or version."""
        agent_version = AgentVersion(
            name=version_in.name,
            version=version_in.version,
            model_provider=version_in.model_provider,
            model_name=version_in.model_name,
            prompt_text=version_in.prompt_text,
        )
        db.add(agent_version)
        db.commit()
        db.refresh(agent_version)
        logger.info("Registered agent version '%s' %s (id: %s)", agent_version.name, agent_version.version, agent_version.id)
        return agent_version

    @staticmethod
    def count(db: Session) -> int:
        """Count total registered agent versions."""
        stmt = select(AgentVersion)
        return len(list(db.scalars(stmt).all()))
