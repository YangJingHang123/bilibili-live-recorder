import oss2
import os
from config import accessKey, accessSecret, endpoint


def update(filename):
    bucket = oss2.Bucket(oss2.Auth(accessKey, accessSecret), endpoint, 'record-results')
    bucket.put_object_from_file(filename.split('/')[-1], filename)
    os.remove(filename)
