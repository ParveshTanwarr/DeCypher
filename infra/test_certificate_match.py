import json

from infra.detectors.certificate import (
    get_certificate_fingerprint,
    match_certificate_fingerprint
)


fingerprint = get_certificate_fingerprint(
    "127.0.0.1",
    8443
)


with open(
    "infra/known_certificates.json",
    "r",
    encoding="utf-8"
) as file:
    known_certificates = json.load(file)


domain = match_certificate_fingerprint(
    fingerprint,
    known_certificates
)


print("Fingerprint:")
print(fingerprint)

print("\nClearnet match:")
print(domain)