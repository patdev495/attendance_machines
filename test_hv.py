import socket


def recv_exact(sock, n):
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            raise ConnectionError("Socket closed")
        data += chunk
    return data


def recv_frame(sock):
    header = recv_exact(sock, 4)
    length = int.from_bytes(header, "big")
    body = recv_exact(sock, length)
    return header + body


def send_frame(sock, hex_data):
    packet = bytes.fromhex(hex_data)
    body_len = int.from_bytes(packet[:4], "big")

    if body_len != len(packet) - 4:
        raise ValueError("Sai length header")

    sock.sendall(packet)


CONNECT_PACKET = (
    "0000005a"
    "4a1167415c45720e130917436d647225404650777c320c626172674545321a3b134150777d7c54620b1146716b734533421119267a7541335e5d173e2a320c62525c5869697e44620b1172617c5445365850504d66764f624c4e"
)

ip = "192.168.209.61"
port = 9922

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(5)

    # 1. Mở TCP connection
    # TCP SYN, SYN-ACK, ACK tự xảy ra ở đây
    s.connect((ip, port))
    print("TCP connected")

    # 2. Gửi lệnh connect của Hanvon
    send_frame(s, CONNECT_PACKET)
    print("Sent Hanvon connect packet")

    # 3. Nhận response
    connect_response = recv_frame(s)
    print("Connect response length:", len(connect_response))
    print(connect_response.hex(" "))

    # 4. Sau này muốn tải log thì phải có packet download log capture từ Wireshark
    # send_frame(s, DOWNLOAD_ATTENDANCE_PACKET)
    # attendance_response = recv_frame(s)