# Module `client/` — FTP Client CLI

## Cấu trúc

```
client/
├── __init__.py         # Re-export FTPClient, FTPError
├── ftp_client.py       # TCP control client + UDP transfer coordination
├── command_handler.py  # Interactive CLI (REPL)
├── main.py             # Entry point
├── upload/             # Thư mục chứa file cần upload
└── download/           # Thư mục lưu file download về
```

---

## Chạy client

```bash
python3.10 client/main.py
# hoặc
python3.10 -m client.main
```

Sau khi khởi động, gõ `help` để xem danh sách lệnh.

---

## Phiên làm việc mẫu

```
ftp> connect
Connected to 127.0.0.1:2121 — Hybrid FTP Server ready

ftp> login admin 1234
Logged in.

ftp> ls
(empty)

ftp> put sample.txt
Uploading client/upload/sample.txt → sample.txt ...
Upload complete. SHA-256: 3b9e...

ftp> ls
-rw-r--r--   1 owner group           72 Jul 23 16:51 sample.txt

ftp> hash sample.txt
3b9e...

ftp> get sample.txt downloaded.txt
Downloading sample.txt → client/download/downloaded.txt ...
Download complete. SHA-256: 3b9e...

ftp> quit
Disconnected.
```

---

## FTPClient API

`ftp_client.py` cung cấp interface Python cho mọi lệnh FTP:

| Method | FTP command | Mô tả |
| --- | --- | --- |
| `connect()` | — | Kết nối TCP, nhận 220 greeting |
| `login(user, pass)` | USER / PASS | Xác thực |
| `quit()` | QUIT | Đăng xuất và đóng socket |
| `pwd()` | PWD | Lấy thư mục hiện tại |
| `cwd(path)` | CWD | Đổi thư mục |
| `cdup()` | CDUP | Lên thư mục cha |
| `mkd(name)` | MKD | Tạo thư mục |
| `rmd(name)` | RMD | Xóa thư mục |
| `list(path)` | LIST | Liệt kê dạng `ls -l` |
| `nlst(path)` | NLST | Liệt kê tên file |
| `size(file)` | SIZE | Kích thước file (bytes) |
| `mdtm(file)` | MDTM | Thời gian sửa đổi |
| `hash(file)` | HASH | SHA-256 từ server |
| `dele(file)` | DELE | Xóa file |
| `rename(old, new)` | RNFR/RNTO | Đổi tên file |
| `upload(local, remote)` | STOR | Upload qua UDP |
| `download(remote, local)` | RETR | Download qua UDP |

---

## Luồng UDP transfer (client phía)

### Upload (STOR)

```
1. client.upload(local_path, remote_name)
2. Gửi PASV → nhận TCP data socket
3. Gửi STOR <name> → nhận 150 với port=N tid=M
4. Tạo UDP socket, connect(server_host, N)
5. UDPSender.send_file(local_path)
6. Nhận 226 Transfer complete SHA-256=<digest>
```

### Download (RETR)

```
1. client.download(remote_name, local_path)
2. Gửi PASV → nhận TCP data socket
3. Gửi RETR <name> → nhận 150 với port=N tid=M
4. Tạo UDP socket, bind + connect(server_host, N)
5. UDPReceiver.receive_file(local_path)
6. Nhận 226 Transfer complete SHA-256=<digest>
```

---

## Verify toàn vẹn

Sau mỗi transfer, client so sánh digest trả về từ `UDPSender.send_file()` / `UDPReceiver.receive_file()` với digest trong reply 226. Khớp = file toàn vẹn end-to-end.
