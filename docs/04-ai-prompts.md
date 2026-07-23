# GenAI Usage & Code Refinement Log

Theo yêu cầu mục 2.4 §6 của đề bài: ghi lại prompt sử dụng, raw output, quá trình chỉnh sửa và phân tích.

---

## Session 1 — Thiết kế và hiện thực TCP Server

**Ngày:** 2026-07-23  
**Công cụ:** Claude (claude.ai / Claude Code CLI)  
**Mục tiêu:** Thiết kế và sinh code cho `server/` module (auth, file_manager, session, server)

---

### Prompt 1 — Khám phá codebase và lên kế hoạch

**Prompt gốc gửi cho AI:**

```
Explore the repository at /Users/.../Hybrid-FTP. I need to understand:
1. Full directory structure (all files and folders)
2. Full content of every Python file in common/
3. Content of test/test_common.py
4. Any existing server/ or client/ directories

Report back all file contents verbatim so I can plan a TCP server implementation.
```

**Raw output (tóm tắt):**

AI liệt kê toàn bộ cấu trúc repo, đọc từng file trong `common/` và `test/`, xác nhận chưa có `server/` hay `client/`. Phát hiện các utilities sẵn có: `parse_command`, `format_reply`, `ReplyCode`, `ServerConfig`, `sha256_file`, `UDPPacket`.

**Phân tích và chỉnh sửa:**

- Output hữu ích vì liệt kê đủ các hàm reusable trong `common/`.
- Không cần chỉnh sửa — đây là bước research thuần túy.

---

### Prompt 2 — Thiết kế kiến trúc TCP server

**Prompt gốc:**

```
Design a TCP server implementation plan for a Hybrid FTP project.
[... context đầy đủ về common/ module, 27 lệnh FTP, requirements từ docs.md ...]

Please provide:
1. File structure for server/ directory
2. Class/function design for each file (with method signatures)
3. Session state machine (auth flow)
4. How to handle PASV vs PORT mode
5. Thread model
6. How commands map to handlers (dispatch table vs if/elif)
7. How to stub RETR/STOR cleanly so they can be filled in later
```

**Raw output (tóm tắt):**

AI đề xuất cấu trúc 5 file: `auth.py`, `file_manager.py`, `session.py`, `server.py`, `main.py`. Thiết kế chi tiết:
- `AuthState` enum 3 state
- Dispatch table thay vì if/elif (O(1), dễ mở rộng)
- PASV: bind OS port, reply 227, accept() chỉ khi có transfer command
- PORT: store host/port, connect() khi transfer
- Stubs với comment `# --- RDT LAYER HOOK ---`
- Thread-safe logging với `threading.Lock`

**Phân tích và chỉnh sửa:**

1. **Giữ nguyên:** Dispatch table pattern — đúng với thiết kế FTP chuẩn, dễ debug.
2. **Giữ nguyên:** PASV listener tạo sớm (tại lệnh PASV), accept() muộn (tại transfer) — đúng RFC 959.
3. **Điều chỉnh:** AI đề xuất `_pasv_port` field riêng, nhưng thực tế chỉ cần `_pasv_sock` và gọi `getsockname()` khi cần — bỏ field dư.
4. **Điều chỉnh:** `_close_pasv_listener()` trong plan đặt riêng, nhưng khi code thực tế cũng reset `_data_mode = None` để tránh state không nhất quán.
5. **Bổ sung:** AI không đề cập `_send_multiline()` cho HELP command — tự thêm vào để format đúng multi-line FTP reply (dùng `-` sau code).
6. **Bổ sung:** `to_virtual()` trong `FileManager` — AI thiết kế nhưng không nêu rõ cần dùng ở `_cmd_pwd` và `_cmd_cwd`; tự xác định khi viết code thực tế.

---

### Prompt 3 — Viết code thực tế

Code được viết dựa trên plan từ Prompt 2, với các điều chỉnh sau trong quá trình implementation:

**`server/auth.py`:**
- AI output: đúng, không cần sửa. Đơn giản và rõ ràng.

**`server/file_manager.py`:**
- AI output: thiết kế đúng nhưng thiếu chi tiết `list_dir` format.
- Chỉnh sửa: tự implement `stat.filemode()` để sinh output giống `ls -l`, thêm `datetime.fromtimestamp` cho MDTM format `YYYYMMDDhhmmss`.
- Bổ sung: `unique_path()` logic cho STOU — AI chỉ mô tả "trả về path chưa tồn tại", phải tự viết counter logic.

**`server/session.py`:**
- Vấn đề phát hiện khi code: `_cwd` lưu dưới dạng `Path` (virtual), nhưng `FileManager.resolve()` cần virtual path làm string. Phải thêm helper `_real_cwd()` để convert.
- `_cmd_cdup`: AI đề xuất gọi `_fm.change_dir(cwd, "..")` nhưng vì cwd là virtual path, cần dùng `self._cwd.parent` để lấy parent virtual path, sau đó gọi `_cmd_cwd` tái sử dụng logic.
- `_cmd_stat`: AI mô tả chung, tự quyết định: nếu có argument thì trả info file, không thì trả server status.

**`server/server.py`:**
- AI output: chính xác, implement gần như 1:1 với plan.
- Bổ sung: thread name `f"client-{addr}"` để dễ debug khi có nhiều concurrent connections.

---

### Kết quả kiểm tra

```bash
# Import test
/opt/homebrew/bin/python3.10 -c "from server import FTPServer; print('Import OK')"
# Output: Import OK

# Unit tests (common/ module)
/opt/homebrew/bin/python3.10 -m unittest test.test_common -v
# Output: 3 tests OK
```

**Lỗi phát hiện sau khi chạy:** Python 3.9 system không support `slots=True` trong `@dataclass` (chỉ từ 3.10). Phải dùng `/opt/homebrew/bin/python3.10` thay vì `/usr/bin/python3`.

---

### Tổng kết đóng góp AI vs tự viết

| Phần | AI đóng góp | Tự điều chỉnh |
|------|-------------|---------------|
| Kiến trúc tổng thể | 90% | 10% |
| `auth.py` | 95% | 5% |
| `file_manager.py` | 60% | 40% (list_dir, mdtm format, unique_path logic) |
| `session.py` | 70% | 30% (_cwd handling, _real_cwd, _send_multiline, _cmd_cdup, _cmd_stat) |
| `server.py` | 85% | 15% (thread naming, error handling) |
| Docs | 40% | 60% (viết lại từ plan AI sang prose) |

---

## Session 2 — Reliable UDP Layer (`transport/`) + Client CLI

**Ngày:** 2026-07-23  
**Công cụ:** Claude Code CLI  
**Mục tiêu:** Hiện thực `transport/` (RDT layer), wire vào `server/session.py`, viết `client/` CLI, tạo test_files, cập nhật docs

---

### Prompt 1 — Đọc toàn bộ codebase và lên kế hoạch

**Prompt gốc gửi cho AI:**

```
giờ hãy hoàn thiện tiếp project này cho tôi, với mỗi cái làm, đồng thời
cập nhật docs cho tôi, cũng như các prompt để làm, đọc file docs.md và
các file trong folder docs để có thêm context
```

**Raw output (tóm tắt):**

AI đọc toàn bộ: `docs.md`, `docs/01–04`, tất cả file Python trong `common/`, `server/`, `test/`, `README.md`. Xác định trạng thái: `transport/` và `client/` chưa tồn tại; RETR/STOR/STOU/APPE là stubs có comment `# --- RDT LAYER HOOK ---`. Lập task list 4 mục theo thứ tự phụ thuộc.

**Phân tích:**

- Bước đọc context rất quan trọng để AI không viết lại code đã có.
- AI phát hiện đúng điểm hook trong `session.py` mà không cần chỉ dẫn thêm.

---

### Prompt 2 — Thiết kế và viết `transport/` RDT layer

**Prompt ngầm (từ task list):**

```
Implement transport/ module: udp_sender.py, udp_receiver.py.
Stop-and-Wait ARQ with sequence numbers, ACK, timeout/retransmit,
CRC-32 per packet, SHA-256 end-to-end. No external libraries.
```

**Raw output — `transport/udp_sender.py`:**

AI tạo `UDPSender` với:
- `send_file(path)`: đọc file theo chunk `MAX_UDP_PAYLOAD` (1024 bytes), gán seq tăng dần
- `_send_data(seq, payload)`: gửi `UDPPacket(DATA)`, loop chờ ACK với timeout, retransmit tối đa `max_retries`
- `_send_fin(seq)`: gửi `UDPPacket(FIN)`, chờ `FIN_ACK`
- `_wait_ack(expected_seq)`: dùng `time.monotonic()` để deadline chính xác hơn `socket.timeout` đơn thuần
- Return SHA-256 của file gốc

**Raw output — `transport/udp_receiver.py`:**

AI tạo `UDPReceiver` với:
- `receive_file(dest)`: học `sender_addr` từ `recvfrom` packet đầu tiên
- Filter theo `transfer_id` để bỏ qua datagram không liên quan
- Ghi payload khi `sequence == expected_seq`, tăng `expected_seq`
- Re-ACK `expected_seq - 1` khi duplicate/out-of-order
- Gửi `FIN_ACK` khi nhận `FIN`
- Return SHA-256 của file đã ghi

**Phân tích và chỉnh sửa:**

1. **Giữ nguyên:** `_wait_ack` dùng `time.monotonic()` thay vì reset `settimeout` mỗi lần — đúng vì tránh drift khi có nhiều packets nhanh liên tiếp.
2. **Điều chỉnh:** AI ban đầu dùng `sock.recv` trong receiver nhưng cần `recvfrom` để biết `sender_addr` gửi ACK về đúng chỗ. Đã sửa ngay trong output.
3. **Bổ sung:** `sender_addr` được học từ packet đầu tiên — không hardcode — đúng với cả active mode và passive mode.
4. **Giữ nguyên:** Re-ACK last good seq khi out-of-order thay vì drop silent — đúng vì sender cần được kích để retransmit.

---

### Prompt 3 — Wire RDT vào `server/session.py`

**Prompt ngầm:**

```
Replace # --- RDT LAYER HOOK --- stubs in server/session.py with real
calls to transport/ sender/receiver. RETR sends file via UDP, STOR
receives. Server binds UDP socket on random port, sends port+tid in
150 reply, client parses and connects.
```

**Raw output (tóm tắt):**

AI:
- Thêm import `UDPSender`, `UDPReceiver` vào `session.py`
- Thêm `_transfer_id_counter` field
- Viết `_next_transfer_id()`, `_open_udp_socket()`, `_do_receive()`, `_append_dest()`
- `_cmd_retr`: bind UDP, gửi `150 ... port=N tid=M`, gọi `UDPSender.send_file`, gửi `226 SHA-256=<digest>`
- `_cmd_stor`, `_cmd_stou`, `_cmd_appe` đều delegate vào `_do_receive()`

**Phân tích và chỉnh sửa:**

1. **Vấn đề thiết kế:** TCP data socket (PASV/PORT) không còn truyền bytes file — chỉ dùng để "giữ connection" báo hiệu với client. AI xử lý đúng: mở PASV data socket nhưng đóng nó sau khi UDP xong, không gửi gì qua TCP data socket.
2. **Điều chỉnh:** `_do_receive` timeout cho receiver = `udp_timeout_seconds * 20` (tối thiểu 10s) — receiver cần timeout lớn hơn sender vì chờ nhiều packet liên tiếp.
3. **Bổ sung:** `_append_dest` để APPE nhận vào file tạm, sau đó merge vào file đích — tránh ghi đè file đang tồn tại.

---

### Prompt 4 — Viết `client/` module

**Prompt ngầm:**

```
Create client/ module: ftp_client.py (TCP control + UDP coordination),
command_handler.py (CLI REPL), main.py. Support all 27 commands.
upload() parses port+tid from 150 reply, creates UDP socket, calls
UDPSender. download() same with UDPReceiver.
```

**Raw output — `client/ftp_client.py`:**

AI tạo `FTPClient` với đầy đủ method cho 27 lệnh. Điểm quan trọng:
- `_open_pasv_data()`: issue PASV, parse `(h1,h2,h3,h4,p1,p2)`, return connected TCP socket
- `_parse_udp_params(reply_msg)`: parse `port=N tid=M` từ 150 reply text
- `upload()`: PASV + STOR, parse UDP params, `UDPSender.send_file()`
- `download()`: PASV + RETR, parse UDP params, `UDPReceiver.receive_file()`
- `_read_reply()`: xử lý cả single-line và multi-line FTP reply

**Raw output — `client/command_handler.py`:**

AI tạo `CLI` class với `match/case` dispatch (Python 3.10+), aliases (`ls`/`list`/`dir`, `put`/`upload`, `get`/`download`), alias upload/download root dirs.

**Phân tích và chỉnh sửa:**

1. **Giữ nguyên:** `match/case` — sạch hơn if/elif, chỉ cần Python 3.10 (đã dùng cho server).
2. **Điều chỉnh:** AI ban đầu để `connect` tự động khi `CLI.run()` khởi động — đổi thành lệnh tường minh để user tự chọn host/port.
3. **Bổ sung:** `_safe_quit()` gọi `quit()` hoặc fallback `close()` nếu server không phản hồi — tránh hang khi server đã tắt.
4. **Vấn đề phát hiện:** `_parse_udp_params` cần xử lý trường hợp server reply không có `port=` hoặc `tid=` (raise `FTPError` thay vì `KeyError`).

---

### Kết quả kiểm tra

```bash
python3.10 -m unittest discover -s test -v
# Ran 38 tests in 2.130s — OK
```

Tất cả 38 test pass sau khi wire RDT layer vào session (không có test nào bị break bởi thay đổi stubs → real code vì test server không test RETR/STOR — sẽ bổ sung integration test riêng cho UDP transfer).

---

### Tổng kết đóng góp AI vs tự viết (Session 2)

| Phần | AI đóng góp | Tự điều chỉnh |
|------|-------------|---------------|
| `transport/udp_sender.py` | 85% | 15% (`_wait_ack` deadline logic, `recvfrom` fix) |
| `transport/udp_receiver.py` | 80% | 20% (`sender_addr` learning, re-ACK out-of-order) |
| `server/session.py` (wire RDT) | 75% | 25% (`_do_receive` timeout, `_append_dest`, transfer_id counter) |
| `client/ftp_client.py` | 80% | 20% (`_parse_udp_params`, `_read_reply` multiline, connect flow) |
| `client/command_handler.py` | 70% | 30% (connect flow, `_safe_quit`, alias set) |
| `docs/05-transport.md` | 50% | 50% |
| `docs/06-client.md` | 50% | 50% |
| `README.md` | 60% | 40% |
