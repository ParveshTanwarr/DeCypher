import socket
import ssl
import hashlib


def get_certificate_fingerprint(
    host: str,
    port: int = 443
):
    """
    Connect to an HTTPS target and return its
    SHA-256 certificate fingerprint.

    Intended for authorized test infrastructure.
    """

    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with socket.create_connection(
            (host, port),
            timeout=10
        ) as sock:

            with context.wrap_socket(
                sock,
                server_hostname=host
            ) as secure_socket:

                certificate = secure_socket.getpeercert(
                    binary_form=True
                )

        fingerprint = hashlib.sha256(
            certificate
        ).hexdigest().upper()

        # Format like:
        # AA:BB:CC:DD...
        return ":".join(
            fingerprint[i:i + 2]
            for i in range(0, len(fingerprint), 2)
        )

    except (OSError, ssl.SSLError):
        return None
def match_certificate_fingerprint(
    fingerprint: str,
    known_certificates: dict
):
    """
    Compare a certificate fingerprint against
    known authorized intelligence.

    Returns the matched domain if found.
    """

    if not fingerprint:
        return None

    match = known_certificates.get(
        fingerprint.upper()
    )

    if match:
        return match.get("domain")

    return None