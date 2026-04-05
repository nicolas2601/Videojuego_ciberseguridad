import base64


def encode_b64(text):
    return base64.b64encode(text.encode('utf-8')).decode('utf-8')


def decode_b64(encoded):
    try:
        return base64.b64decode(encoded.encode('utf-8')).decode('utf-8', errors='replace')
    except Exception:
        return '?????'


def decode_partial(slots):
    partial = ''.join(s if s else '    ' for s in slots)
    return decode_b64(partial)
