#  Copyright (C) 2012   Christian Heimes (christian@python.org)
#  Licensed to PSF under a Contributor Agreement.
#

__all__ = ("sha3_224", "sha3_256", "sha3_384", "sha3_512")
from _sha3 import sha3_224, sha3_256, sha3_384, sha3_512

# monkey patch _hashlib
import hashlib as _hashlib

_hashlib_constructor = _hashlib.__get_builtin_constructor

def __get_builtin_constructor(name):
    if name in set(['sha3_224', 'sha3_256', 'sha3_384', 'sha3_512',
                   'SHA3_224', 'SHA3_256', 'SHA3_384', 'SHA3_512']):
        bs = name[5:]
        if bs == '224':
            return sha3_224
        elif bs == '256':
            return sha3_256
        elif bs == '384':
            return sha3_384
        elif bs == '512':
            return sha3_512
    return _hashlib_constructor(name)

if not hasattr(_hashlib, "sha3_512"):
    _hashlib.sha3_224 = sha3_224
    _hashlib.sha3_256 = sha3_256
    _hashlib.sha3_384 = sha3_384
    _hashlib.sha3_512 = sha3_512
    _hashlib.__get_builtin_constructor = __get_builtin_constructor
