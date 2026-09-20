"""Excepciones tipadas del dominio, traducidas a HTTP por app/main.py."""
from __future__ import annotations


class AppError(Exception):
    code = "APP_ERROR"
    status_code = 400

    def __init__(self, message: str, code: str | None = None, status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        if status_code:
            self.status_code = status_code


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = 404


class ValidationAppError(AppError):
    code = "VALIDATION_ERROR"
    status_code = 422


class InvalidFileError(AppError):
    code = "INVALID_FILE"
    status_code = 400


class DuplicateVideoError(AppError):
    code = "DUPLICATE_VIDEO"
    status_code = 409


class FFmpegError(AppError):
    code = "FFMPEG_ERROR"
    status_code = 500


class PathNotAllowedError(AppError):
    code = "PATH_NOT_ALLOWED"
    status_code = 403
