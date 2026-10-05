"""
Shared OpenSearch connection, for a local Docker container with security
disabled (the common `discovery.type=single-node` + security plugin off
dev setup). If you later enable security on the container, add http_auth
here.
"""

from opensearchpy import OpenSearch

INDEX_NAME = "resume_chunks"


def get_client():
    return OpenSearch(
        hosts=[{"host": "localhost", "port": 9200}],
        http_compress=True,
        use_ssl=False,
        verify_certs=False,
        ssl_show_warn=False,
    )