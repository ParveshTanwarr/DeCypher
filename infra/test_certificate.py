from infra.detectors.certificate import (
    get_certificate_fingerprint
)


fingerprint = get_certificate_fingerprint(
    "127.0.0.1",
    8443
)

print("Certificate fingerprint:")
print(fingerprint)