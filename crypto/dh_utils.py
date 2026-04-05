def dh_public(g, p, secret):
    return pow(g, secret, p)


def dh_shared_key(received_public, p, own_secret):
    return pow(received_public, own_secret, p)
