# Module: server/ — TCP Control Server

## 1. Tổng quan

Module `server/` hiện thực kênh điều khiển TCP của Hybrid FTP. Mỗi kết nối client được xử lý trên một thread riêng biệt với trạng thái phiên hoàn toàn cô lập.

```
server/
├── __init__.py        # Re-export FTPServer
├── server.py          # Accept loop, thread dispatch, CLI logging
├── session.py         # Per-client state machine + 27 command handlers
├── auth.py            # Credential store
├── file_manager.py    # Sandboxed filesystem operations
├── main.py            # Entry point
└── storage/           # Server filesystem root (tạo tự động)
```

Chạy server:
```bash
python3.10 server/main.py
# hoặc
python3.10 -m server.main
```

---

## 2. Kiến trúc thread

```
Main thread
└── FTPServer.start()
    └── _accept_loop()  ← blocking trên accept()
         ├── client-1 thread → ClientSession.run()
         ├── client-2 thread → ClientSession.run()
         └── ...
```

- Mỗi client được spawn một `daemon=True` thread.
- `ClientSession` sở hữu socket của riêng nó — không có shared mutable state giữa các session.
- Thread-safe logging dùng `threading.Lock` trên `FTPServer._print_lock`.

---

## 3. State machine xác thực (AuthState)

```
          ┌─────────────────────────────────────────────────┐
          │  NOT_LOGGED_IN  (trạng thái ban đầu)            │
          └───────────────────┬─────────────────────────────┘
                              │
            USER <username>   │  → reply: 331 Password required
            (lưu pending_username, chuyển state)
                              ▼
          ┌─────────────────────────────────────────────────┐
          │  USERNAME_GIVEN                                  │
          └───────────────────┬────────────────┬────────────┘
                              │                │
          PASS đúng           │   PASS sai     │
          → 230 Logged in     │   → 530        │
          → LOGGED_IN         │   → NOT_LOGGED_IN
                              ▼
          ┌─────────────────────────────────────────────────┐
          │  LOGGED_IN  (toàn bộ 27 lệnh được phép)         │
          └───────────────────┬─────────────────────────────┘
                              │
          QUIT                │  → 221 Goodbye → kết thúc session
```

**Lệnh được phép trước khi đăng nhập:** `USER`, `PASS`, `QUIT`, `HELP`, `NOOP`

**Lệnh khác khi chưa đăng nhập:** bị chặn với `530 Please login with USER and PASS`

---

## 4. Dispatch table

`session.py` dùng dict để ánh xạ tên lệnh → handler method, thay vì if/elif chain:

```python
self._handlers = {
    "USER": self._cmd_user,
    "RETR": self._cmd_retr,
    # ... 27 lệnh
}
```

Luồng xử lý mỗi dòng TCP:
```
_readline() → parse_command() → _dispatch() → handler(cmd) → _send()
```

---

## 5. Active Mode vs Passive Mode

### PORT (Active Mode)

Client chỉ định địa chỉ IP và port mà server sẽ **kết nối vào**:

```
Client → PORT h1,h2,h3,h4,p1,p2
Server → 200 PORT command successful
...
Client → LIST
Server → connect(h1.h2.h3.h4, p1*256+p2)  ← server chủ động kết nối
Server → 150 Opening data connection
Server → [gửi dữ liệu]
Server → 226 Transfer complete
```

### PASV (Passive Mode)

Server mở một port ngẫu nhiên và client **kết nối vào đó**:

```
Client → PASV
Server bind OS-assigned port, listen(1)
Server → 227 Entering Passive Mode (127,0,0,1,p1,p2)
...
Client → LIST
Server accept() ← chờ client kết nối
Server → 150 Opening data connection
Server → [gửi dữ liệu]
Server → 226 Transfer complete
```

Điểm quan trọng: `_pasv_sock` được tạo tại thời điểm PASV nhưng `accept()` chỉ được gọi khi có lệnh transfer thực sự (LIST/NLST/RETR/STOR).

---

## 6. Sandboxed filesystem (FileManager)

Tất cả đường dẫn đều được resolve về thư mục `server/storage/`. Mọi attempt `../` để thoát ra ngoài đều bị chặn bởi `resolve()`:

```python
resolved = candidate.resolve()
if not str(resolved).startswith(str(self._root)):
    raise PathError("path escapes storage root")
```

Virtual path `/` tương ứng với `server/storage/` trên filesystem thực.

---

## 7. Transfer stubs (RETR/STOR/STOU/APPE)

Bốn lệnh transfer hiện tại là **stubs** — chúng validate path và mở data connection nhưng không truyền byte nào. Điểm hook cho RDT layer được đánh dấu rõ:

```python
def _cmd_retr(self, cmd):
    # ... validate path và data connection ...
    self._send(150, "Opening data connection for <file>")
    # --- RDT LAYER HOOK ---
    data_sock.close()
    self._send(226, "STUB: 0 bytes transferred")
```

Phase sau sẽ thay thế phần `# --- RDT LAYER HOOK ---` bằng UDP sender/receiver từ `transport/` module.

---

## 8. Danh sách 27 lệnh đã hiện thực

| Nhóm | Lệnh | Trạng thái |
|------|------|------------|
| Auth | USER, PASS, QUIT, NOOP | Hoàn chỉnh |
| Directory | PWD, CWD, CDUP, MKD, RMD, LIST, NLST, STAT | Hoàn chỉnh |
| File metadata | SIZE, MDTM, HASH | Hoàn chỉnh |
| Transfer setup | TYPE, MODE, PORT, PASV | Hoàn chỉnh |
| Transfer | RETR, STOR, STOU, APPE | Stub (RDT phase 2) |
| File ops | DELE, RNFR, RNTO, ABOR, HELP | Hoàn chỉnh |

---

## 9. Reply codes dùng

| Code | Ý nghĩa |
|------|---------|
| 200 | Command OK |
| 211 | System status |
| 213 | File status (SIZE, MDTM, HASH) |
| 214 | Help message |
| 220 | Service ready |
| 221 | Goodbye |
| 226 | Transfer complete |
| 227 | Entering Passive Mode |
| 230 | Login successful |
| 250 | File action OK |
| 257 | Pathname created/printed |
| 331 | Username OK, need password |
| 350 | Rename pending (RNFR) |
| 421 | Service unavailable |
| 425 | Cannot open data connection |
| 426 | Transfer aborted |
| 450 | File unavailable (transient) |
| 500 | Syntax error |
| 501 | Parameter error |
| 502 | Command not implemented |
| 503 | Bad sequence of commands |
| 530 | Not logged in |
| 550 | File unavailable |

---

## 10. Test thủ công với telnet

```bash
telnet 127.0.0.1 2121

# Đăng nhập
USER admin
PASS 1234

# Thao tác thư mục
PWD
MKD testdir
CWD testdir
CDUP
LIST

# Passive mode + list
PASV
LIST

# Metadata
SIZE somefile.txt
MDTM somefile.txt
HASH somefile.txt

# Đăng xuất
QUIT
```
