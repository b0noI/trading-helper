import os
import base64

from google.cloud import kms

kms_client = kms.KeyManagementServiceClient()
db_pass = kms_client.decrypt(
    os.environ["SECRET_RESOURCE_NAME"],
    base64.b64decode(os.environ["SECRET_STRING"]),
).plaintext


def estimate_probability_of_change(request):
    return db_pass[:1]