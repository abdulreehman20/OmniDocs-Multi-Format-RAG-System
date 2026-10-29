"""Neon Object Storage (S3-compatible) client using boto3."""

from __future__ import annotations

from typing import Any

import boto3
from botocore.client import BaseClient
from botocore.config import Config

from src.config import Settings, get_settings
from src.providers.protocols import ObjectStorage


class Boto3ObjectStorage:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        if not self._settings.aws_endpoint_url_s3:
            raise RuntimeError("AWS_ENDPOINT_URL_S3 is required for Object Storage")
        if not self._settings.aws_access_key_id or not self._settings.aws_secret_access_key:
            raise RuntimeError("AWS credentials are required for Object Storage")
        self._bucket = self._settings.s3_bucket_documents
        self._client: BaseClient = boto3.client(
            "s3",
            region_name=self._settings.aws_region or "auto",
            endpoint_url=self._settings.aws_endpoint_url_s3,
            aws_access_key_id=self._settings.aws_access_key_id,
            aws_secret_access_key=self._settings.aws_secret_access_key,
            config=Config(signature_version="s3v4"),
        )

    @property
    def bucket(self) -> str:
        return self._bucket

    def create_upload_url(
        self,
        key: str,
        content_type: str,
        expires_seconds: int = 300,
    ) -> str:
        return self._client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": self._bucket,
                "Key": key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_seconds,
        )

    def create_download_url(
        self,
        key: str,
        expires_seconds: int = 300,
    ) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )

    def head(self, key: str) -> dict[str, Any]:
        response = self._client.head_object(Bucket=self._bucket, Key=key)
        return {
            "ContentLength": int(response.get("ContentLength") or 0),
            "ContentType": response.get("ContentType"),
            "ETag": response.get("ETag"),
        }

    def download_to_file(self, key: str, destination: str) -> None:
        self._client.download_file(self._bucket, key, destination)

    def upload_file(self, key: str, source: str, content_type: str) -> None:
        extra = {"ContentType": content_type}
        self._client.upload_file(source, self._bucket, key, ExtraArgs=extra)

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)

    def list_prefix(
        self,
        prefix: str,
        continuation: str | None = None,
    ) -> tuple[list[dict], str | None]:
        kwargs: dict[str, Any] = {"Bucket": self._bucket, "Prefix": prefix}
        if continuation:
            kwargs["ContinuationToken"] = continuation
        response = self._client.list_objects_v2(**kwargs)
        contents = response.get("Contents") or []
        items = [
            {"Key": obj["Key"], "Size": obj.get("Size", 0)} for obj in contents if "Key" in obj
        ]
        next_token = response.get("NextContinuationToken")
        return items, next_token


def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.environment == "test":
        from src.providers.fakes import FakeObjectStorage

        return FakeObjectStorage()
    return Boto3ObjectStorage(settings)


__all__ = ["Boto3ObjectStorage", "ObjectStorage", "get_object_storage"]
