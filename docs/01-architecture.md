# Kiến trúc Hybrid FTP

## Mục tiêu

Ứng dụng tách hai luồng giao tiếp:

| Kênh | Giao thức | Trách nhiệm |
| --- | --- | --- |
| Control plane | TCP | Đăng nhập, lệnh FTP, phản hồi trạng thái, điều phối transfer |
| Data plane | UDP | Chỉ truyền bytes file qua lớp Reliable UDP tự cài đặt |

TCP phù hợp với lệnh và session vì vốn đáng tin cậy. UDP không đảm bảo dữ liệu đến nơi, đúng thứ tự hoặc không trùng lặp; `transport/` sẽ bổ sung sequence number, ACK, timeout và retransmit.

## Cấu trúc mã nguồn

```text
common/     Hợp đồng dùng chung: packet UDP, checksum, config, TCP protocol
transport/  Reliable UDP sender/receiver và retransmit/window
server/     TCP control server, session, auth, file manager, UDP endpoint
client/     CLI, TCP control client, gọi UDP upload/download
test/       Unit và integration tests
docs/       Tài liệu theo dõi quyết định và phần đã triển khai
```

## Luồng upload dự kiến

```text
Client                         Server
  |--- TCP: USER/PASS --------->| xác thực
  |<-- TCP: 230 ---------------|
  |--- TCP: PASV/STOR ---------->|
  |<-- TCP: 150 ---------------|
  |=== UDP DATA / ACK =========>| ghi file, kiểm tra thứ tự
  |=== UDP FIN / FIN_ACK ======>|
  |<-- TCP: 226 + SHA-256 -----|
```

TCP chỉ điều phối; bytes của file chỉ đi qua UDP.


---

## Current implementation correction (2026-07-26)

This section supersedes earlier planned/future-tense descriptions of the data path.

- The TCP control channel carries FTP commands, replies, session state, and the short-lived TCP coordination connection for each transfer.
- File payloads travel only through the custom reliable UDP layer. The protocol is Stop-and-Wait ARQ with sequence numbers, ACKs, timeout/retry, CRC-32 checks, and FIN/FIN_ACK completion.
- Passive mode remains the default client workflow. Active mode is implemented and verified: the client opens a TCP listener, sends PORT, and accepts the server coordination connection before the UDP transfer.
- A transfer runs in a per-session worker. ABOR signals its cancellation event, closes the relevant transfer sockets, reports 426, and preserves upload atomicity by using a temporary destination file.

The exact verified command paths and evidence are recorded in `docs/07-demo-evidence.md`.