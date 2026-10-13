import socket
import pytest

@pytest.fixture(autouse=True)
def block_network_access(monkeypatch):
    """
    Enforces constraint C1 and C8: tests must run without network access.
    Any attempt to open an external socket connection raises an error.
    """
    orig_connect = socket.socket.connect

    def guarded_connect(self, address):
        if isinstance(address, str):
            # Allow Unix domain sockets if any
            return orig_connect(self, address)
        host, port = address[0], address[1]
        raise RuntimeError(
            f"Network call blocked by offline constraint (C1/C8): attempted connection to {host}:{port}"
        )

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
