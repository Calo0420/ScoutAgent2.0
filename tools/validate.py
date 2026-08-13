"""
validate.py
ScoutAgent 2.0 — Input Validation

Centralised pre-flight checks for all scan target inputs.
Called at the top of every tool function before any network connection is made.

Blocks:
  - Empty / whitespace-only hosts
  - Loopback addresses (127.x.x.x, ::1)
  - Link-local / AWS EC2 instance metadata endpoint (169.254.x.x)
  - Hosts with shell metacharacters (defence-in-depth against injection)
  - Hostnames or IPs exceeding DNS/protocol limits
  - Invalid or overly-broad CIDR ranges for network scans
"""

import ipaddress
import re

# Metacharacters that have no business appearing in a hostname or IP
_SHELL_META_RE = re.compile(r'[;|&`$(){}\[\]<>\n\r\\\'"]')

# Max legitimate hostname length per RFC 1035
_MAX_HOST_LEN = 253

# Networks that must never be scan targets
_BLOCKED_NETWORKS = [
    (ipaddress.ip_network("127.0.0.0/8"),   "Loopback addresses cannot be scan targets."),
    (ipaddress.ip_network("169.254.0.0/16"), (
        "169.254.x.x is the link-local / AWS EC2 instance metadata address range. "
        "Scanning it could expose this instance's IAM credentials and identity. BLOCKED."
    )),
    (ipaddress.ip_network("0.0.0.0/8"),     "Unspecified address range (0.x.x.x) cannot be a scan target."),
    (ipaddress.ip_network("::1/128"),        "IPv6 loopback (::1) cannot be a scan target."),
    (ipaddress.ip_network("fe80::/10"),      "IPv6 link-local range cannot be a scan target."),
]

# Subnets too broad to scan (would attempt thousands of hosts)
_MAX_SUBNET_PREFIX = {4: 16, 6: 64}  # /16 for IPv4, /64 for IPv6


def validate_host(host: str) -> None:
    """
    Validate a scan target hostname or IP address.
    Raises ValueError with a clear message on any violation.
    """
    if not host or not host.strip():
        raise ValueError("Scan target host must not be empty.")

    host = host.strip()

    if len(host) > _MAX_HOST_LEN:
        raise ValueError(
            f"Host '{host[:40]}...' exceeds maximum length ({len(host)} chars). "
            f"Maximum is {_MAX_HOST_LEN} characters."
        )

    if _SHELL_META_RE.search(host):
        raise ValueError(
            f"Host '{host[:80]}' contains disallowed characters. "
            "Hostnames and IPs must not contain shell metacharacters."
        )

    # Attempt IP parse — if it succeeds, apply network-level blocks
    # Note: keep this block's ValueError separate from _check_blocked_ip's ValueError
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        # Not a bare IP — hostname; let socket/paramiko handle DNS
        return

    _check_blocked_ip(addr)


def _check_blocked_ip(addr: ipaddress._BaseAddress) -> None:
    """Raise ValueError if addr falls in a blocked network."""
    for network, reason in _BLOCKED_NETWORKS:
        try:
            if addr in network:
                raise ValueError(f"BLOCKED target '{addr}': {reason}")
        except TypeError:
            # IPv4 addr vs IPv6 network or vice versa — skip
            continue


def validate_subnet(subnet: str) -> None:
    """
    Validate a CIDR subnet for network scanning.
    Raises ValueError with a clear message on any violation.
    """
    if not subnet or not subnet.strip():
        raise ValueError("Scan target subnet must not be empty.")

    subnet = subnet.strip()

    if _SHELL_META_RE.search(subnet):
        raise ValueError(
            f"Subnet '{subnet[:80]}' contains disallowed characters."
        )

    try:
        network = ipaddress.ip_network(subnet, strict=False)
    except ValueError:
        raise ValueError(
            f"'{subnet}' is not a valid CIDR subnet (e.g. 10.0.0.0/24)."
        )

    # Block subnets that are too broad (check first so message is clear)
    max_prefix = _MAX_SUBNET_PREFIX.get(network.version, 16)
    if network.prefixlen < max_prefix:
        raise ValueError(
            f"Subnet '{subnet}' is too broad (/{network.prefixlen}). "
            f"Minimum prefix length is /{max_prefix} for IPv{network.version} — "
            "scanning a larger range risks timeout and excessive network traffic."
        )

    # Block dangerous networks — check overlap with each blocked network
    for blocked_net, reason in _BLOCKED_NETWORKS:
        try:
            if network.overlaps(blocked_net):
                raise ValueError(f"BLOCKED subnet '{subnet}': {reason}")
        except TypeError:
            continue
