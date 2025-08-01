import asyncio
import os
from datetime import datetime, timedelta
from typing import TypedDict

from src.aibot.cli import logger
from src.aibot.core.entities.chat import ChatMessage

# Import DAOBase for timezone consistency across the bot (DTZ005 compliance)
from src.aibot.infrastructure.db.dao._base import DAOBase


class SessionConfig(TypedDict):
    """Configuration for a thread session."""

    model: str
    temperature: float
    max_tokens: int
    top_p: float
    creator_id: int
    created_at: datetime
    conversation_history: list[ChatMessage]


class ThreadSessionService:
    """Service for managing thread conversation sessions in memory."""

    _instance: "ThreadSessionService | None" = None

    def __init__(self) -> None:
        """Initialize the thread session service."""
        if ThreadSessionService._instance is not None:
            msg = "Use get_instance() to get the singleton instance"
            raise RuntimeError(msg)

        self.active_sessions: dict[int, SessionConfig] = {}
        self._cleanup_task: asyncio.Task | None = None
        self._start_cleanup_task()

    @classmethod
    def get_instance(cls) -> "ThreadSessionService":
        """Get the singleton instance of ThreadSessionService."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_session(  # noqa: PLR0913
        self,
        thread_id: int,
        model: str,
        creator_id: int,
        temperature: float | None = None,
        max_tokens: int | None = None,
        top_p: float | None = None,
    ) -> SessionConfig:
        """Create a new thread session with specified configuration.

        Parameters
        ----------
        thread_id : int
            Discord thread ID.
        model : str
            AI model to use for this session.
        creator_id : int
            Discord user ID who created the session.
        temperature : float | None, optional
            Model temperature. Defaults to environment variable.
        max_tokens : int | None, optional
            Maximum tokens for responses. Defaults to environment variable.
        top_p : float | None, optional
            Top-p sampling parameter. Defaults to environment variable.

        Returns
        -------
        SessionConfig
            The created session configuration.
        """
        # Use environment defaults if not specified
        if temperature is None:
            temperature = float(os.getenv("DEFAULT_TEMPERATURE", "0.6"))
        if max_tokens is None:
            max_tokens = int(os.getenv("DEFAULT_MAX_TOKENS", "4096"))
        if top_p is None:
            top_p = float(os.getenv("DEFAULT_TOP_P", "0.96"))

        session_config: SessionConfig = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "creator_id": creator_id,
            "created_at": datetime.now(DAOBase.TIMEZONE),
            "conversation_history": [],
        }

        self.active_sessions[thread_id] = session_config

        # Ensure cleanup task is running (start it if event loop is now available)
        if self._cleanup_task is None or self._cleanup_task.done():
            self._start_cleanup_task()

        logger.info(
            "Created thread session %d for user %d with model %s",
            thread_id,
            creator_id,
            model,
        )

        return session_config

    def get_session(self, thread_id: int) -> SessionConfig | None:
        """Get an active thread session by thread ID.

        Parameters
        ----------
        thread_id : int
            Discord thread ID.

        Returns
        -------
        SessionConfig | None
            Session configuration if exists, None otherwise.
        """
        return self.active_sessions.get(thread_id)

    def add_message_to_session(self, thread_id: int, message: ChatMessage) -> bool:
        """Add a message to the session's conversation history.

        Parameters
        ----------
        thread_id : int
            Discord thread ID.
        message : ChatMessage
            Message to add to history.

        Returns
        -------
        bool
            True if message was added successfully, False if session doesn't exist.
        """
        session = self.active_sessions.get(thread_id)
        if session is None:
            return False

        session["conversation_history"].append(message)
        logger.debug("Added message to thread %d history", thread_id)
        return True

    def remove_session(self, thread_id: int) -> bool:
        """Remove a thread session.

        Parameters
        ----------
        thread_id : int
            Discord thread ID.

        Returns
        -------
        bool
            True if session was removed, False if it didn't exist.
        """
        if thread_id in self.active_sessions:
            del self.active_sessions[thread_id]
            logger.info("Removed thread session %d", thread_id)
            return True
        return False

    def get_active_session_count(self) -> int:
        """Get the number of currently active sessions.

        Returns
        -------
        int
            Number of active sessions.
        """
        return len(self.active_sessions)

    def _start_cleanup_task(self) -> None:
        """Start the background cleanup task."""
        # Only start if an event loop is running
        try:
            loop = asyncio.get_running_loop()
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = loop.create_task(self._cleanup_loop())
                logger.debug("Started thread session cleanup task")
        except RuntimeError:
            # No event loop running yet, cleanup task will be started later
            logger.debug("No event loop running, cleanup task will be started when needed")

    async def _cleanup_loop(self) -> None:
        """Background task to clean up expired sessions."""
        try:
            while True:
                await asyncio.sleep(1800)  # Run every 30 minutes
                await self._cleanup_expired_sessions()
        except asyncio.CancelledError:
            logger.debug("Thread session cleanup task cancelled")
        except Exception as e:
            logger.exception("Error in thread session cleanup task: %s", e)

    async def _cleanup_expired_sessions(self) -> None:
        """Remove sessions that are older than 1 hour + 5 minutes buffer."""
        cutoff_time = datetime.now(DAOBase.TIMEZONE) - timedelta(
            minutes=65,
        )  # 1 hour + 5 min buffer
        expired_sessions = []

        for thread_id, session in self.active_sessions.items():
            if session["created_at"] < cutoff_time:
                expired_sessions.append(thread_id)

        for thread_id in expired_sessions:
            del self.active_sessions[thread_id]
            logger.info("Cleaned up expired thread session %d", thread_id)

        if expired_sessions:
            logger.info("Cleaned up %d expired thread sessions", len(expired_sessions))

    def shutdown(self) -> None:
        """Shutdown the service and cancel cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            logger.info("Thread session service shutdown")
