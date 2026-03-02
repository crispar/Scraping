#!/bin/bash
# Generate self-signed SSL certificate for development
# For production, replace with Let's Encrypt or real certificates

set -e

SSL_DIR="$(dirname "$0")/ssl"
mkdir -p "$SSL_DIR"

if [ -f "$SSL_DIR/cert.pem" ] && [ -f "$SSL_DIR/key.pem" ]; then
    echo "SSL certificates already exist in $SSL_DIR"
    echo "Delete them first if you want to regenerate."
    exit 0
fi

openssl req -x509 -nodes -days 365 \
    -newkey rsa:2048 \
    -keyout "$SSL_DIR/key.pem" \
    -out "$SSL_DIR/cert.pem" \
    -subj "/C=US/ST=State/L=City/O=ContentExtractor/CN=localhost"

echo "SSL certificates generated in $SSL_DIR"
echo "  - cert.pem (certificate)"
echo "  - key.pem  (private key)"
