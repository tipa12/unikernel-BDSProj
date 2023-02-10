from google.cloud import storage

from typing import List


def get_bucket(project: str, bucket_name: str) -> storage.Bucket:
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    return bucket


def get_blobs(bucket: storage.Bucket) -> List[storage.Blob]:
    client = storage.Client(project=bucket.user_project)
    blobs = []
    for blob in client.list_blobs(bucket):
        blobs.append(blob)
    return blobs


def get_blobs_by_id(bucket: storage.Bucket, id: str) -> List[storage.Blob]:
    client = storage.Client(project=bucket.user_project)
    blobs = []
    for blob in client.list_blobs(bucket):
        if id in blob.name:
            blobs.append(blob)
    return blobs
