# Module `transport/` — Reliable UDP Layer

## Phạm vi

`transport/` hiện thực lớp RDT (Reliable Data Transfer) trên nền UDP thuần. Không dùng thư viện bên ngoài — chỉ dùng `socket` và các primitive từ `common/`.

| File | Nội dung |
| --- | --- |
| `udp_sender.py` | Stop-and-Wait ARQ sender: chia file thành chunk, gửi từng packet, chờ ACK |
| `udp_receiver.py` | Stop-and-Wait ARQ receiver: nhận packet theo thứ tự, ghi file, gửi ACK |

---

## Cơ chế Stop-and-Wait

```
Sender                          Receiver
  |-- DATA seq=0 ------------>|
  |<-- ACK ack=0 ------------|
  |-- DATA seq=1 ------------>|
  |<-- ACK ack=1 ------------|
  ...
  |-- FIN seq=N ------------>|
  |<-- FIN_ACK --------------|
```

- Sender gửi một packet rồi **block** chờ ACK trước khi gửi packet tiếp theo.
- Nếu timeout (mặc định 0.5s), packet được retransmit tối đa `max_retries` lần (mặc định 10).
- Receiver lọc duplicate bằng `expected_seq` — nếu nhận lại packet đã ACK, vẫn gửi lại ACK mà không ghi file lần hai.
- Out-of-order packet bị drop, ACK cuối cùng được resent để trigger retransmit từ sender.

---

## UDPSender

```python
from transport.udp_sender import UDPSender

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(("127.0.0.1", udp_port))
sender = UDPSender(sock, transfer_id=1, timeout_s=0.5, max_retries=10)
digest = sender.send_file(Path("file.txt"))
# digest là SHA-256 hex của file gốc
```

`send_file()` trả về SHA-256 hex digest của file đã gửi để caller có thể verify với digest mà server báo cáo qua TCP.

---

## UDPReceiver

```python
from transport.udp_receiver import UDPReceiver

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("127.0.0.1", 0))
receiver = UDPReceiver(sock, transfer_id=1, timeout_s=10.0)
digest = receiver.receive_file(Path("output.txt"))
# digest là SHA-256 hex của file đã nhận
```

`receive_file()` học địa chỉ sender từ packet đầu tiên (`recvfrom`), ghi dữ liệu theo thứ tự sequence, và gửi FIN_ACK khi nhận FIN.

---

## Tích hợp với server

`server/session.py` gọi layer này trong `_cmd_retr` và `_do_receive`:

1. Server bind một UDP socket trên port ngẫu nhiên.
2. Server gửi `150` reply qua TCP với thông tin `port=<N> tid=<M>`.
3. Client parse reply, tạo UDP socket, connect/bind vào port server.
4. Transfer diễn ra hoàn toàn qua UDP.
5. Server gửi `226 Transfer complete SHA-256=<digest>` qua TCP khi xong.

---

## Kiểm thử

```bash
python -m unittest discover -s test -v
# Historical run: 38 tests OK (common + server integration)
```

Test RDT end-to-end được cover bởi integration test upload/download trong `test/test_transfer.py` (phase sau).


---

## Current verification correction (2026-07-26)

The old `38 tests OK` count is superseded. The full suite has 67 passing tests.

Focused reliability tests in `test/test_transport.py` now demonstrate:

- retransmission after the first DATA datagram is dropped;
- retransmission after the first DATA ACK is dropped;
- duplicate DATA is acknowledged without duplicate file output;
- an out-of-order DATA datagram is ignored until the expected sequence arrives; and
- FIN is retransmitted after a dropped FIN datagram.

`UDPSender` and `UDPReceiver` also accept an optional cancellation event. They check it in their transfer/wait loops and raise `TransferError` when ABOR cancels a live session. This is used by the server worker model described in `docs/03-server.md`.

## Current throughput tuning correction (2026-08-07)

The old Stop-and-Wait wording is now historical for the default behavior. The
transport is Go-Back-N capable and the default tuning is:

- `MAX_UDP_PAYLOAD = 1200`
- `DEFAULT_UDP_WINDOW_SIZE = 8`

This lets the sender keep up to eight unacknowledged DATA packets in flight.
The 1200-byte payload keeps the application payload larger than the original
1024-byte setting while still staying comfortably below a typical Ethernet MTU
after adding the custom 22-byte header plus UDP/IP overhead.
