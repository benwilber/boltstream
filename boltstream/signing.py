import base64
import hashlib
import hmac


def get_signature(secret, message):
    m = hmac.new(secret.encode(), digestmod=hashlib.sha1)
    m.update(message.encode())
    return base64.b64encode(m.digest())
