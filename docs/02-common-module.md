# Module `common` — nền tảng giao thức

## Phạm vi đã triển khai

`common` không tạo socket và không chứa logic client/server. Nó định nghĩa các thành phần cả hai phía phải hiểu giống nhau:

| File | Nội dung |
| --- | --- |
| `constants.py` | Encoding, giới hạn và cờ packet |
| `checksum.py` | CRC-32 datagram, SHA-256 streaming cho file |
| `packet.py` | Mã hóa/giải mã/kiểm tra packet Reliable UDP |
| `protocol.py` | Parser lệnh TCP và FTP reply codes |
| `config.py` | Cấu hình mặc định local development |

## UDP header (22 bytes, network byte order)

| Trường | Kích thước | Ý nghĩa |
| --- | ---: | --- |
| Magic | 2 bytes | `HF`, nhận diện datagram của ứng dụng |
| Version | 1 byte | Phiên bản protocol, hiện là `1` |
| Flags | 1 byte | `DATA`, `ACK`, `FIN`, `FIN_ACK`, `ERROR` |
| Transfer ID | 4 bytes | Phân biệt các transfer đồng thời |
| Sequence | 4 bytes | Số thứ tự packet dữ liệu, bắt đầu từ 0 |
| Acknowledgement | 4 bytes | Sequence number được xác nhận |
| Payload length | 2 bytes | Số byte dữ liệu ngay sau header |
| Checksum | 4 bytes | CRC-32 của header (checksum = 0) + payload |

Payload tối đa là 1200 bytes để tăng throughput nhưng vẫn giữ datagram dưới MTU Ethernet thông dụng sau khi cộng IP/UDP và custom header. `UDPPacket.from_bytes()` từ chối packet sai magic/version, thiếu dữ liệu, sai độ dài hoặc sai checksum, trước khi receiver ghi dữ liệu vào file.

## Hai tầng kiểm tra toàn vẹn

- CRC-32: phát hiện corruption cho từng UDP packet, phục vụ retransmit.
- SHA-256: xác thực file hoàn chỉnh theo chunk 64 KiB, không cần nạp cả file vào RAM.

## TCP control format

Control channel là UTF-8, từng dòng kết thúc `\r\n`. `parse_command()` chuyển tên lệnh thành uppercase; `format_reply()` tạo reply như `b"230 Login successful\r\n"`.

## Kiểm thử

Chạy từ thư mục gốc:

```powershell
python -m unittest discover -s test -v
```

Test hiện kiểm tra packet round-trip, phát hiện dữ liệu bị sửa, parser và formatter. Test transport sau này sẽ mô phỏng mất packet, duplicate và reorder.


---

## Current verification correction (2026-07-26)

The earlier statement that transport loss/reorder tests would be added later is superseded. The test suite now includes focused fake-socket coverage for dropped DATA, dropped ACK, duplicate DATA, out-of-order DATA, and dropped FIN, in addition to packet CRC validation and end-to-end transfer tests. The latest full run is 67 tests passing; see `docs/05-transport.md` and `docs/07-demo-evidence.md`.
