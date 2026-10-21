#!/usr/bin/env python3
"""CIDR Validation Utility for CI/CD Deployment Security Gates.

Enforces fail-closed ingress validation:
- Requires a valid IPv4 CIDR block, matching Terraform's cidr_blocks rules.
- Strictly rejects wildcard / world-accessible CIDRs (0.0.0.0/0, ::/0, prefix length 0).
- Strictly rejects unspecified addresses (0.0.0.0, ::).
- Strictly rejects multicast address spaces.
- Returns normalized CIDR string on success.
- Exits with code 1 and descriptive error message on failure.
"""

import ipaddress
import sys


def validate_restricted_cidr(cidr_str: str) -> str:
    """Validates that cidr_str is a valid, restricted IPv4 CIDR block.

    Args:
        cidr_str: The CIDR string to validate (e.g. '223.236.96.144/32').

    Returns:
        Normalized CIDR string (e.g. '223.236.96.144/32').

    Raises:
        ValueError: If CIDR is empty, invalid, unrestricted (prefix 0), unspecified, or multicast.
    """
    if cidr_str is None:
        raise ValueError("CIDR must not be None")

    if not isinstance(cidr_str, str):
        raise ValueError(f"Expected CIDR as string, got {type(cidr_str).__name__}")

    cleaned = cidr_str.strip()
    if not cleaned:
        raise ValueError("CIDR cannot be empty or whitespace")

    if "/" not in cleaned:
        raise ValueError(
            f"Invalid CIDR '{cleaned}': Missing prefix length (e.g. /32 or /24)"
        )

    parts = cleaned.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid CIDR '{cleaned}': Multiple slashes found")

    ip_part, prefix_part = parts[0].strip(), parts[1].strip()
    if not ip_part:
        raise ValueError(f"Invalid CIDR '{cleaned}': Empty IP address part")

    if not prefix_part:
        raise ValueError(f"Invalid CIDR '{cleaned}': Empty prefix length")

    try:
        prefix_int = int(prefix_part)
    except ValueError as e:
        raise ValueError(
            f"Invalid prefix '{prefix_part}' in CIDR '{cleaned}': Must be an integer"
        ) from e

    try:
        network = ipaddress.ip_network(cleaned, strict=False)
    except Exception as e:
        raise ValueError(f"Invalid CIDR '{cleaned}': {e}") from e

    if network.version != 4:
        raise ValueError(
            f"IPv6 CIDR '{cleaned}' is not supported: Terraform uses IPv4 cidr_blocks for ALB ingress"
        )

    # Reject wildcard / world-accessible networks (prefix length 0)
    if network.prefixlen == 0 or prefix_int == 0:
        raise ValueError(
            f"Wildcard/unrestricted CIDR '{cleaned}' (prefix length 0) is rejected for app ingress"
        )

    # Reject unspecified address networks (0.0.0.0 or ::)
    if network.network_address.is_unspecified:
        raise ValueError(
            f"Unspecified address in CIDR '{cleaned}' is rejected for app ingress"
        )

    # Reject multicast address networks
    if network.network_address.is_multicast:
        raise ValueError(
            f"Multicast address in CIDR '{cleaned}' is rejected for app ingress"
        )

    return str(network)


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Error: Missing CIDR argument.\nUsage: validate_cidr.py <cidr>\n")
        sys.exit(1)

    raw_cidr = sys.argv[1]
    try:
        normalized = validate_restricted_cidr(raw_cidr)
        print(normalized)
        sys.exit(0)
    except ValueError as err:
        sys.stderr.write(f"Error: {err}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
