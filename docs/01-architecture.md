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
