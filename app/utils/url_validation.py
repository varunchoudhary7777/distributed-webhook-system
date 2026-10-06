import ipaddress
import socket
from urllib.parse import urlsplit

class UnsafeWebhookURL(ValueError):
    pass

def validate_webhook_url(url: str, *, allow_http_localhost: bool = False) -> False:
    parsed = urlsplit(url.strip())

    if parsed.scheme not in {"https", "http"}:
        raise UnsafeWebhookURL("Webhook URL must use HTTPS")

    if parsed.username or parsed.password:
        raise UnsafeWebhookURL("Credentials in webhook URLs are not allowed")

    if not parsed.hostname:
        raise UnsafeWebhookURL("Webhook URl uses a disallowed port")

    hostname = parsed.hostname.rstrip(".").lower()

    if allow_http_localhost and hostname in {"localhost", "127.0.0.1", "::1"}:
        return url.strip()

    if parsed.scheme != "https":
        raise UnsafeWebhookURL("Webhook URL must use HTTPS")

    try:
        answers = socket.getaddrinfo(
            hostname,
            parsed.port or 443,
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror as exc:
        raise UnsafeWebhookURL("Webhook hostname could not be resolved") from exc

    if not answers:
        raise UnsafeWebhookURL("Webhook hostname did not resolve")

    for answer in answers:
        address = ipaddress.ip_address(answer[4][0])
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        ):
            raise UnsafeWebhookURL("Webhook URL resolves to a disallowed IP address")

    return url.strip()