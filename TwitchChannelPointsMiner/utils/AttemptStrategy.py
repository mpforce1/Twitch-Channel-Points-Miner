import logging
import time
from typing import Callable

logger = logging.getLogger(__name__)


class ExceptionContext:
    """Utility for printing a stack trace outside the context of an exception handler."""

    def __init__(self, exception: Exception, stack_trace: str | None):
        self.exception = exception
        self.stack_trace = stack_trace

    def __repr__(self):
        if self.stack_trace is not None:
            return f"{self.stack_trace}\n{self.exception}"
        else:
            return f"{self.exception}"

    def __eq__(self, value: object):
        return (
            isinstance(value, ExceptionContext)
            and self.exception == value.exception
            and self.stack_trace == value.stack_trace
        )


class SuccessResult[TResult]:
    """Returned when the result of `make_attempts` was successful."""

    def __init__(self, errors: list[ExceptionContext], result: TResult):
        self.errors = errors
        """Any errors that occurred."""
        self.result = result
        """The result."""

    @property
    def attempts(self):
        """The number of attempts made."""
        return len(self.errors) + 1

    def __repr__(self):
        return f"SuccessResult({self.__dict__})"

    def __eq__(self, value: object):
        if isinstance(value, SuccessResult) and len(self.errors) == len(value.errors):
            for index in range(len(self.errors)):
                if self.errors[index] != value.errors[index]:
                    return False
            return self.result == value.result
        return False


class ErrorResult:
    """Returned when the result of `make_attempts` was 1 or more errors."""

    def __init__(self, errors: list[ExceptionContext]):
        self.errors = errors
        """The errors in the order they occurred."""

    @property
    def attempts(self):
        """The number of attempts made."""
        return len(self.errors)

    def __repr__(self):
        if len(self.errors) > 1:
            # Group errors of the same type
            error_types = dict[str, tuple[int, str]]()
            for error in self.errors:
                if type(error).__name__ not in error_types:
                    error_types[type(error).__name__] = (1, repr(error))
                else:
                    count, value = error_types[type(error).__name__]
                    error_types[type(error).__name__] = (count + 1, value)
            errors = f"[{', '.join((f'{count} * {e}' for count, e in error_types.values()))}]"
        else:
            errors = f"[{', '.join((repr(e) for e in self.errors))}]"

        return f"ErrorResult({errors})"

    def __eq__(self, value: object):
        if isinstance(value, ErrorResult) and len(self.errors) == len(value.errors):
            for index in range(len(self.errors)):
                if self.errors[index] != value.errors[index]:
                    return False
            return True
        return False


class AttemptStrategy:
    """Handles making an attempt at something multiple times by catching Exceptions and validating the Result."""

    def __init__(self, attempts: int = 3, attempt_interval_seconds: int = 1):
        self.attempts = attempts
        """The number of attempts that should be made."""
        self.attempt_interval_seconds = attempt_interval_seconds
        """The number of seconds to wait between attempts."""

    def make_attempts[TResult](
        self,
        attempt: Callable[[], TResult],
        validate: Callable[[TResult], None],
        retryable: Callable[[Exception], bool],
        exception_context: Callable[[Exception], str | None],
    ) -> SuccessResult[TResult] | ErrorResult:
        """
        Calls `attempt` up to `self.attempts` times until either a successful attempt is made or the maximum number of
        attempts have been made.
        :param attempt: The functon to attempt.
        :param validate: Function to check if the result is valid. Should throw an Exception if not.
        :param retryable: Function that returns True if a given Error can be retried.
        :param exception_context: Function that returns a context string (or None) for a given Exception.
        :return:
        """
        attempts = 0
        errors: list[ExceptionContext] = []
        while attempts < self.attempts:
            attempts += 1
            try:
                result = attempt()
                validate(result)
                return SuccessResult(errors, result)
            except Exception as e:
                errors.append(ExceptionContext(e, exception_context(e)))
                if not retryable(e):
                    logger.debug(f"Error cannot be retried: {e}")
                    break
            if attempts >= self.attempts:
                # Break early to avoid sleeping
                break
            else:
                time.sleep(self.attempt_interval_seconds)
        return ErrorResult(errors)
