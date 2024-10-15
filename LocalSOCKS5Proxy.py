import socket
import threading
import struct

# Local proxy configuration
local_host = '127.0.0.1'  # The local address to bind to (or 0.0.0.0)
local_port = 9053         # The local port to listen on

def handle_client(client_socket):
    try:
        # SOCKS5 handshake
        client_socket.recv(262)  # Client sends authentication methods
        client_socket.sendall(b"\x05\x00")  # No authentication required

        # Receive connection request
        version, cmd, _, addr_type = struct.unpack("!BBBB", client_socket.recv(4))
        
        if cmd != 0x01:  # Only allow CONNECT command
            client_socket.close()
            return

        # Handle different address types
        if addr_type == 0x01:  # IPv4
            address = socket.inet_ntoa(client_socket.recv(4))
        elif addr_type == 0x03:  # Domain name
            domain_length = client_socket.recv(1)[0]
            address = client_socket.recv(domain_length).decode()
        else:
            client_socket.close()
            return

        port = struct.unpack('!H', client_socket.recv(2))[0]  # Get the port

        print(f"Connecting to {address}:{port}")

        # Connect to the remote server
        remote_socket = socket.create_connection((address, port))
        client_socket.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")  # SOCKS5 response: success

        # Start forwarding data between client and remote server
        threading.Thread(target=forward, args=(client_socket, remote_socket)).start()
        threading.Thread(target=forward, args=(remote_socket, client_socket)).start()

    except Exception as e:
        print(f"Error: {e}")
        client_socket.close()

def forward(source, destination):
    try:
        while True:
            data = source.recv(4096)
            if not data:
                break
            destination.sendall(data)
    except Exception as e:
        print(f"Error during forwarding: {e}")
    finally:
        source.close()
        destination.close()

def start_proxy():
    # Set up the local server to accept connections
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((local_host, local_port))
    server_socket.listen(5)
    print(f"SOCKS5 Proxy listening on {local_host}:{local_port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Accepted connection from {addr}")
        handle_client(client_socket)

if __name__ == "__main__":
    start_proxy()