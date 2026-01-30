import os
import hashlib
from typing import List, Dict, Any

import boto3

from .db import insert_document, insert_audit_log


def _safe_filename(name: str) -> str:
    return os.path.basename(name).replace("\x00", "")


def _compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_s3_client():
    endpoint = os.getenv("S3_ENDPOINT")
    region = os.getenv("S3_REGION")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    bucket = os.getenv("S3_BUCKET")
    if not endpoint or not region or not access_key or not secret_key or not bucket:
        return None
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
    )


def save_uploaded_files(uploaded_files, company_id: str, user_id: str, base_dir: str = "uploads") -> List[Dict[str, Any]]:
    os.makedirs(base_dir, exist_ok=True)
    saved = []
    s3_client = _get_s3_client()
    s3_bucket = os.getenv("S3_BUCKET") if s3_client else None

    for uploaded_file in uploaded_files:
        filename = _safe_filename(uploaded_file.name)
        file_bytes = uploaded_file.getvalue()
        sha256 = _compute_sha256(file_bytes)

        if s3_client and s3_bucket:
            key = f"{company_id}/{user_id}/{sha256}/{filename}"
            s3_client.put_object(Bucket=s3_bucket, Key=key, Body=file_bytes)
            target_path = f"s3://{s3_bucket}/{key}"
        else:
            target_dir = os.path.join(base_dir, company_id, user_id, sha256)
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)

            with open(target_path, "wb") as f:
                f.write(file_bytes)

        doc_id = insert_document(
            company_id=company_id,
            user_id=user_id,
            filename=filename,
            path=target_path,
            size=len(file_bytes),
            sha256=sha256,
        )

        insert_audit_log(
            company_id=company_id,
            user_id=user_id,
            action="upload_document",
            doc_id=doc_id,
            meta={"filename": filename, "path": target_path},
        )

        saved.append(
            {
                "doc_id": doc_id,
                "filename": filename,
                "path": target_path,
                "sha256": sha256,
                "size": len(file_bytes),
            }
        )

    return saved
