"""Identify conventional Firebase service-account key filenames without reading files."""

from __future__ import annotations

import re

# Firebase Admin SDK downloads commonly embed a five-character account ID and
# a longer key identifier in a project-prefixed JSON filename. Requiring both
# identifiers avoids mistaking unrelated Firebase manifests for credentials.
_FIREBASE_ADMIN_SDK_KEY = re.compile(
    r"(?:[a-z0-9][a-z0-9._-]*-)?firebase-adminsdk-[a-z0-9]{5}-[a-z0-9]{10,}\.json\Z"
)
# Firebase key exports are also frequently renamed to one of these conventional
# service-account names. Keep matches exact to avoid flagging firebase.json or
# Google client configuration files that do not contain private keys.
_SERVICE_ACCOUNT_NAMES = frozenset({
    'serviceaccountkey.json', 'service-account-key.json', 'service_account_key.json',
    'firebase-service-account.json', 'firebase_service_account.json',
    'firebaseserviceaccount.json', 'firebase-service-account-key.json',
    'firebase_service_account_key.json', 'firebaseserviceaccountkey.json',
})


def is_firebase_service_account_key(name: str) -> bool:
    """Recognize likely private-key filenames; never inspect file contents."""
    if not isinstance(name, str):
        return False
    lowered = name.lower()
    return lowered in _SERVICE_ACCOUNT_NAMES or bool(_FIREBASE_ADMIN_SDK_KEY.fullmatch(lowered))
