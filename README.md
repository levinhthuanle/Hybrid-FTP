# Hybrid FTP

Đồ án môn **Internetworking Protocol** — hiện thực FTP lai (Hybrid FTP) tách biệt control plane (TCP) và data plane (UDP tự-reliable).

---

## Cấu trúc dự án

```
common/       Hợp đồng chung: packet UDP, checksum, config, TCP protocol
transport/    Reliable UDP sender/receiver (Stop-and-Wait ARQ)
server/       TCP control server, session, auth, file manager
client/       CLI, TCP control client, UDP transfer
test/         Unit và integration tests
test_files/   File mẫu để test (txt, pdf, jpg)
docs/         Tài liệu kỹ thuật
```

---

## Yêu cầu

- Python 3.10+
- Không cần thư viện bên ngoài (chỉ dùng stdlib)

---

## Chạy server

```bash
python3.10 server/main.py
```

Server lắng nghe trên `127.0.0.1:2121` (TCP control). Mỗi client được xử lý trên thread riêng.

---

## Chạy client

```bash
python3.10 client/main.py
```

Gõ `help` trong REPL để xem danh sách lệnh.

### Phiên mẫu

```
ftp> connect
Connected to 127.0.0.1:2121

ftp> login admin 1234
Logged in.

ftp> put test_files/sample.txt sample.txt
Uploading ... Upload complete. SHA-256: <digest>

ftp> ls
-rw-r--r--  ...  sample.txt

ftp> get sample.txt
Downloading ... Download complete. SHA-256: <digest>

ftp> hash sample.txt
<digest>

ftp> quit
```

---

## Chạy tests

```bash
python3.10 -m unittest discover -s test -v
```

67 tests - auth, directories, passive/active transfer, ABOR, integrity, concurrency, and reliable-UDP loss/reorder.

---

## Tài khoản mặc định

| Username | Password |
|----------|----------|
| admin | 1234 |
| anonymous | (trống) |

---

## Tài liệu

| File | Nội dung |
| --- | --- |
| `docs/01-architecture.md` | Kiến trúc tổng thể, luồng upload/download |
| `docs/02-common-module.md` | UDP packet format, checksum, TCP protocol |
| `docs/03-server.md` | TCP server, state machine, 27 lệnh |
| `docs/04-ai-prompts.md` | GenAI usage log (yêu cầu đề bài) |
| `docs/05-transport.md` | Reliable UDP layer (Stop-and-Wait ARQ) |
| `docs/06-client.md` | Client CLI và FTPClient API |


---

## Current verification (2026-07-26)

The latest full test run is **67 tests, OK**. Reliable UDP loss/reorder coverage, active-mode file transfers, real ABOR cancellation, and digest comparison are implemented. See `docs/07-demo-evidence.md` for the manual CLI/hash transcript and `docs.md` for the audit completion status.