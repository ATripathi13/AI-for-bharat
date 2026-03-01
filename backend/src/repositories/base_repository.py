"""
Base repository interface for data access
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any

T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """Base repository interface defining CRUD operations"""

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create a new entity"""
        pass

    @abstractmethod
    def get(self, **kwargs) -> Optional[T]:
        """Get an entity by identifier(s)"""
        pass

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing entity"""
        pass

    @abstractmethod
    def delete(self, **kwargs) -> bool:
        """Delete an entity by identifier(s)"""
        pass

    @abstractmethod
    def list(self, filters: Optional[Dict[str, Any]] = None, limit: Optional[int] = None) -> List[T]:
        """List entities with optional filters"""
        pass
