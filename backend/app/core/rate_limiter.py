"""In-memory rate limiter for login attempts.

Phase 1 implementation using a dictionary with timestamps.
For production, consider Redis-based rate limiting.
"""

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class LoginAttemptRecord:
    """Track failed login attempts for a single email."""

    attempts: list[float] = field(default_factory=list)
    locked_until: float = 0.0


class LoginRateLimiter:
    """
    In-memory rate limiter for login attempts.

    Rules:
    - Max 5 failed attempts per 15-minute window per email
    - 15-minute lockout after exceeding the limit
    """

    MAX_ATTEMPTS = 5
    WINDOW_SECONDS = 15 * 60  # 15 minutes
    LOCKOUT_SECONDS = 15 * 60  # 15 minutes

    def __init__(self) -> None:
        self._records: dict[str, LoginAttemptRecord] = {}
        self._lock = Lock()

    def _cleanup_old_attempts(self, record: LoginAttemptRecord) -> None:
        """Remove attempts older than the window."""
        cutoff = time.time() - self.WINDOW_SECONDS
        record.attempts = [t for t in record.attempts if t > cutoff]

    def is_locked(self, email: str) -> bool:
        """Check if the email is currently locked out."""
        with self._lock:
            record = self._records.get(email)
            if record is None:
                return False
            if record.locked_until > time.time():
                return True
            return False

    def get_lockout_remaining(self, email: str) -> int:
        """Get remaining lockout seconds for an email. Returns 0 if not locked."""
        with self._lock:
            record = self._records.get(email)
            if record is None:
                return 0
            remaining = int(record.locked_until - time.time())
            return max(0, remaining)

    def record_failed_attempt(self, email: str) -> bool:
        """
        Record a failed login attempt.

        Returns True if the account is now locked (just hit the limit).
        """
        with self._lock:
            if email not in self._records:
                self._records[email] = LoginAttemptRecord()

            record = self._records[email]

            # If already locked, stay locked
            if record.locked_until > time.time():
                return True

            self._cleanup_old_attempts(record)
            record.attempts.append(time.time())

            if len(record.attempts) >= self.MAX_ATTEMPTS:
                record.locked_until = time.time() + self.LOCKOUT_SECONDS
                return True

            return False

    def reset(self, email: str) -> None:
        """Reset attempts for an email (e.g., after successful login)."""
        with self._lock:
            if email in self._records:
                del self._records[email]

    def get_attempts_count(self, email: str) -> int:
        """Get current number of failed attempts in the window."""
        with self._lock:
            record = self._records.get(email)
            if record is None:
                return 0
            self._cleanup_old_attempts(record)
            return len(record.attempts)


# Global singleton instance
login_rate_limiter = LoginRateLimiter()
