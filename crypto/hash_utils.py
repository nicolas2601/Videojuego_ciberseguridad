import hashlib


def sha256_short(text, length=16):
    return hashlib.sha256(text.encode()).hexdigest()[:length]


def sha256_full(text):
    return hashlib.sha256(text.encode()).hexdigest()


def build_rainbow_table(candidates, length=16):
    return {word: sha256_short(word, length) for word in candidates}
