import socket
import struct
import time
import os
import sys
import select

ICMP_ECHO_REQUEST = 8

# ================= CHECKSUM =================
def checksum(data):
    s = 0
    for i in range(0, len(data), 2):
        part = data[i] + (data[i+1] << 8) if i+1 < len(data) else data[i]
        s += part
    s = (s >> 16) + (s & 0xffff)
    s += (s >> 16)
    return ~s & 0xffff

# ================= CREATE ICMP PACKET =================
def create_packet(pid, seq):
    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, 0, pid, seq)
    data = struct.pack('d', time.time())
    chksum = checksum(header + data)
    header = struct.pack('bbHHh', ICMP_ECHO_REQUEST, 0, chksum, pid, seq)
    return header + data

# ================= PING FUNCTION =================
def ping(host, count=4):
    print(f"\nPinging {host}...\n")

    try:
        dest_ip = socket.gethostbyname(host)
    except socket.gaierror:
        print("Invalid host")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    sock.settimeout(1)

    pid = os.getpid() & 0xFFFF

    sent = 0
    received = 0
    rtts = []

    for seq in range(1, count + 1):
        packet = create_packet(pid, seq)
        sent += 1

        start = time.time()
        sock.sendto(packet, (dest_ip, 1))

        try:
            ready = select.select([sock], [], [], 1)
            if ready[0] == []:
                raise socket.timeout

            recv_packet, addr = sock.recvfrom(1024)
            end = time.time()

            rtt = (end - start) * 1000
            rtts.append(rtt)
            received += 1

            print(f"Reply from {addr[0]}: time={round(rtt,2)} ms")

        except socket.timeout:
            print("Request timed out")

    # ===== Statistics =====
    loss = ((sent - received) / sent) * 100

    print("\n--- Ping Statistics ---")
    print(f"Packets: Sent={sent}, Received={received}, Lost={sent - received} ({loss}%)")

    if rtts:
        print(f"RTT -> Min={round(min(rtts),2)} ms, Max={round(max(rtts),2)} ms, Avg={round(sum(rtts)/len(rtts),2)} ms")

# ================= TRACEROUTE FUNCTION =================
def traceroute(host, max_hops=30):
    print(f"\nTraceroute to {host}...\n")

    try:
        dest_ip = socket.gethostbyname(host)
    except socket.gaierror:
        print("Invalid host")
        return

    port = 33434
    pid = os.getpid() & 0xFFFF

    for ttl in range(1, max_hops + 1):
        recv_sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
        send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)

        send_sock.setsockopt(socket.SOL_IP, socket.IP_TTL, ttl)

        recv_sock.bind(("", port))

        start = time.time()
        send_sock.sendto(b'', (host, port))

        addr = None
        try:
            ready = select.select([recv_sock], [], [], 2)
            if ready[0] == []:
                raise socket.timeout

            _, addr = recv_sock.recvfrom(512)
            end = time.time()

            rtt = (end - start) * 1000

            print(f"{ttl}\t{addr[0]}\t{round(rtt,2)} ms")

        except socket.timeout:
            print(f"{ttl}\t*\tRequest timed out")

        finally:
            send_sock.close()
            recv_sock.close()

        if addr and addr[0] == dest_ip:
            print("\nDestination reached.")
            break

# ================= MAIN =================
def main():
    if len(sys.argv) < 2:
        print("Usage: python tool.py <host1> <host2> ...")
        sys.exit(1)

    hosts = sys.argv[1:]

    for host in hosts:
        print("\n" + "="*50)
        print(f"Diagnostics for {host}")
        print("="*50)

        ping(host)
        traceroute(host)

if __name__ == "__main__":
    main()