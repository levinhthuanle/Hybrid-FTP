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
