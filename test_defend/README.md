# Hybrid FTP Defense Test Guide

Tài liệu này hướng dẫn cách test toàn bộ project bằng terminal, theo đúng các nhóm yêu cầu trong `docs.md`. Mục tiêu là:

- chạy được full test suite
- demo live trên terminal cho giảng viên xem
- chỉ rõ trường hợp nào nên dùng helper file/script thay vì gõ tay trực tiếp
- giải thích vì sao mỗi cách test chứng minh được tính năng tương ứng

---

## 1. Chuẩn bị môi trường

Chạy tất cả lệnh từ root của repo:

```bash
D:\Projects\IP\Hybrid-FTP
```

Yêu cầu:
- Python 3.10+
- không cần thư viện ngoài stdlib

Nếu cần server listen trên LAN thay vì localhost, dùng:

```bash
python -m server.main --host 0.0.0.0
```

Nếu test giữa 2 máy trong cùng Wi-Fi / hotspot, client phải connect bằng IP thật của máy server.

---

## 2. Chạy full testcase của project

Đây là cách nhanh nhất để chứng minh project pass toàn bộ automated checks.

```bash
python -m unittest discover -s test -v
```

Hoặc chạy theo từng nhóm:

```bash
python -m unittest test.test_common -v
python -m unittest test.test_server -v
python -m unittest test.test_transport -v
python -m unittest test.test_transfer -v
```

Vì sao cách này quan trọng:
- `test.test_common` kiểm tra packet format, checksum, protocol parser
- `test.test_server` kiểm tra auth, directory tree, mode, PORT/PASV, concurrency, reply codes
- `test.test_transport` kiểm tra reliable UDP: ACK loss, DATA loss, FIN loss, duplicate/out-of-order, sliding window
- `test.test_transfer` kiểm tra upload/download thật, hash verification, active/passive mode, ABOR, STOU, APPE

Nếu giảng viên hỏi "em chứng minh bằng gì?", đây là bằng chứng chắc nhất.

---

## 3. Demo live bằng terminal: kịch bản tổng quan

### 3.1 Mở server

Terminal 1:

```bash
python -m server.main
```

Nếu muốn cho máy khác cùng mạng vào được:

```bash
python -m server.main --host 0.0.0.0
```

### 3.2 Mở client

Terminal 2:

```bash
python -m client.main
```

Sau đó dùng REPL để demo.

---

## 4. Demo từng requirement bằng terminal

## 4.1 Authentication + session basics

```text
CONNECT
USER admin
PASS 1234
NOOP
PWD
QUIT
```

Vì sao chứng minh được:
- `USER/PASS` chứng minh login flow
- `NOOP` chứng minh control channel còn hoạt động sau login
- `PWD` chứng minh session state được giữ đúng

---

## 4.2 Directory tree operations

```text
CONNECT
USER admin
PASS 1234
MKD defense-room
CWD defense-room
MKD docs
MKD data
CWD docs
MKD week1
PWD
LIST
NLST
CDUP
LIST
CDUP
RMD defense-room
QUIT
```

Nếu thư mục không rỗng thì cần xóa file / folder con trước rồi mới `RMD`.

Vì sao chứng minh được:
- `MKD/CWD/CDUP/RMD` chứng minh thao tác cây thư mục
- `LIST/NLST` chứng minh directory traversal và listing
- `PWD` chứng minh virtual cwd hoạt động đúng

Nếu cần demo bằng test thay vì gõ tay:

```bash
python -m unittest test.test_server.DirectoryTests -v
```

---

## 4.3 Type / mode / transfer setup

### TYPE

```text
CONNECT
USER admin
PASS 1234
TYPE A
TYPE I
QUIT
```

### MODE

```text
CONNECT
USER admin
PASS 1234
MODE S
QUIT
```

Lưu ý: `MODE B` và `MODE C` hiện không hỗ trợ, server sẽ trả `502`.

Vì sao chứng minh được:
- `TYPE A/I` chứng minh text/binary transfer setup
- `MODE S` chứng minh server chỉ hỗ trợ stream mode đúng scope project

Nếu muốn demo helper cho `MODE` nhanh hơn:

```bash
python defense_demo\raw_demo.py mode S
python defense_demo\raw_demo.py mode B
```

Helper này hữu ích vì nó show rõ raw reply `200` / `502` của server.

---

## 4.4 Stable binary transfers

Cách demo tốt nhất là dùng file binary thật và kiểm tra hash.

Ví dụ:

```text
CONNECT
USER admin
PASS 1234
TYPE I
STOR test_files\sample.jpg
HASH sample.jpg
RETR sample.jpg
HASH sample.jpg
QUIT
```

Hoặc file lớn hơn để thấy transfer ổn định:

```text
CONNECT
USER admin
PASS 1234
TYPE I
STOR test_files\docker.png
RETR docker.png
QUIT
```

Vì sao chứng minh được:
- `TYPE I` đảm bảo binary mode
- `STOR/RETR` chứng minh upload/download thật
- `HASH` chứng minh end-to-end integrity
- file binary nhiều bytes chứng minh không bị hỏng newline/encoding

Nếu muốn test bằng automated test:

```bash
python -m unittest test.test_transfer.UploadTests.test_upload_binary_file -v
python -m unittest test.test_transfer.DownloadTests.test_download_binary_file -v
python -m unittest test.test_transfer.RoundTripTests.test_roundtrip_binary -v
```

---

## 4.5 Reliable UDP: ACK + timeout recovery

### Test bằng terminal trực tiếp

Có thể demo live, nhưng để thấy timeout recovery rõ ràng thì phải tạo tình huống mất ACK / mất DATA. Cách này thường khó kiểm soát nếu chỉ gõ tay trên REPL.

### Cách chứng minh chắc chắn nhất

Dùng test có sẵn:

```bash
python -m unittest test.test_transport.ReliableUDPBehaviorTests.test_sender_retransmits_data_when_ack_is_lost -v
python -m unittest test.test_transport.ReliableUDPBehaviorTests.test_sender_retransmits_when_data_is_dropped -v
python -m unittest test.test_transport.ReliableUDPBehaviorTests.test_sender_retransmits_fin_when_fin_is_dropped -v
```

Vì sao chứng minh được:
- test đầu tiên chứng minh sender resend khi ACK mất
- test thứ hai chứng minh sender resend khi DATA mất
- test thứ ba chứng minh FIN cũng được resend

### Nếu muốn show live trên terminal

Bạn có thể upload file lớn để thấy progress chạy và transfer không bị treo:

```text
CONNECT
USER admin
PASS 1234
TYPE I
STOR video.mp4
QUIT
```

Nhưng lưu ý: đây chỉ chứng minh transfer hoạt động ổn định, không tạo được packet loss thật như test harness.

---

## 4.6 Functional congestion control / sliding window

Cách chứng minh trực tiếp nhất là test sliding window:

```bash
python -m unittest test.test_transport.ReliableUDPBehaviorTests.test_sender_pipelines_multiple_packets_with_sliding_window -v
```

Vì sao chứng minh được:
- test này kiểm tra sender có pipeline nhiều DATA packet trong một window
- đây là bằng chứng rõ nhất cho congestion / flow control kiểu sliding window

Nếu muốn demo live bằng terminal:

```text
CONNECT
USER admin
PASS 1234
TYPE I
STOR test_files\multi_packet.txt
QUIT
```

File càng lớn, progress càng thể hiện rõ sender đang xử lý transfer nhiều packet.

---

## 4.7 End-to-end hash verification

### Demo live trên terminal

```text
CONNECT
USER admin
PASS 1234
TYPE I
STOR test_files\sample.jpg
HASH sample.jpg
RETR sample.jpg
HASH sample.jpg
QUIT
```

### Test tự động

```bash
python -m unittest test.test_transfer.UploadTests.test_upload_digest_matches -v
python -m unittest test.test_transfer.DownloadTests.test_download_digest_matches -v
python -m unittest test.test_transfer.RoundTripTests.test_roundtrip_large -v
```

Vì sao chứng minh được:
- server trả SHA-256 sau transfer
- client so sánh digest local với digest server báo
- round-trip test chứng minh digest khớp trước và sau transfer

---

## 4.8 Concurrency / multi-threaded server

### Demo live bằng 2 terminal client

Terminal A:

```text
CONNECT
USER admin
PASS 1234
MKD client1dir
CWD client1dir
PWD
```

Terminal B (chạy cùng lúc):

```text
CONNECT
USER admin
PASS 1234
PWD
```

Vì sao chứng minh được:
- server tạo thread riêng cho mỗi connection
- session state không bị lẫn giữa 2 client
- client A đổi cwd không làm client B đổi theo

### Test tự động

```bash
python -m unittest test.test_server.ConcurrencyTests.test_two_clients_isolated -v
```

---

## 4.9 Active / Passive mode

### Passive mode

CLI mặc định dùng passive mode cho `STOR/RETR`.

Ví dụ:

```text
CONNECT
USER admin
PASS 1234
RETR video.mp4
QUIT
```

### Active mode

Sau khi user nhập `PORT ...`, client REPL sẽ dùng active listener cho lần transfer tiếp theo.

Ví dụ live:

```text
CONNECT
USER admin
PASS 1234
PORT 127,0,0,1,228,11
RETR video.mp4
QUIT
```

Vì sao chứng minh được:
- `PORT` chuyển session sang active mode
- server connect ngược về client
- data connection không đi theo passive flow nữa

Nếu muốn test tự động:

```bash
python -m unittest test.test_transfer.ActiveAndAbortTests.test_active_mode_upload_and_download -v
```

---

## 4.10 ABOR

### Demo live

```text
CONNECT
USER admin
PASS 1234
PASV
STOR aborted.bin
ABOR
QUIT
```

### Helper nếu muốn demo sạch, dễ lặp lại

```bash
python defense_demo\raw_demo.py abor aborted-demo.bin --cwd /defense-room
```

Vì sao helper hữu ích:
- helper tạo đúng tình huống "đang STOR rồi abort"
- tự kiểm tra file đích không được tạo
- đây là demo dễ show nhất cho giảng viên khi hỏi ABOR thực sự hủy transfer hay không

### Test tự động

```bash
python -m unittest test.test_transfer.ActiveAndAbortTests.test_abor_cancels_waiting_upload_without_creating_target -v
```

---

## 4.11 STOU / APPE / STAT / HELP / MODE

Các lệnh này nên demo bằng helper vì CLI chính không có câu chuyện ngắn gọn bằng raw command.

### MODE

```bash
python defense_demo\raw_demo.py mode S
python defense_demo\raw_demo.py mode B
```

### HELP

```bash
python defense_demo\raw_demo.py help
```

### STAT

```bash
python defense_demo\raw_demo.py stat
python defense_demo\raw_demo.py stat ascii-demo.txt --cwd /defense-room
```

### STOU

```bash
python defense_demo\raw_demo.py stou client\upload\defense_demo\rename_source.txt --cwd /defense-room
```

### APPE

```bash
python defense_demo\raw_demo.py appe client\upload\defense_demo\append_tail.txt append-demo.txt --cwd /defense-room
```

Sau đó có thể verify:

```text
CONNECT
USER admin
PASS 1234
CWD defense-room
RETR append-demo.txt
HASH append-demo.txt
QUIT
```

Vì sao helper cần thiết:
- `MODE`, `STAT`, `STOU`, `APPE`, `ABOR` là các tình huống raw/đặc thù
- helper giúp lặp lại đúng kịch bản, dễ show reply chuẩn của server

---

## 5. Checklist chạy nhanh trước buổi defend

### Chạy full test suite

```bash
python -m unittest discover -s test -v
```

### Chạy riêng transport

```bash
python -m unittest test.test_transport -v
```

### Chạy riêng transfer

```bash
python -m unittest test.test_transfer -v
```

### Mở server

```bash
python -m server.main
```

### Mở client

```bash
python -m client.main
```

### Demo nên đi theo thứ tự

1. login + directory
2. binary transfer + hash
3. active/passive mode
4. concurrency 2 client
5. ABOR
6. helper `MODE/STAT/STOU/APPE`
7. full test suite nếu giảng viên hỏi bằng chứng

---

## 6. Tóm tắt ngắn

- **Có thể demo trực tiếp trên terminal** cho hầu hết chức năng chính: login, directory, LIST/NLST, TYPE, STOR/RETR, hash, concurrency, active/passive, ABOR
- **Nên dùng helper** cho `MODE`, `STAT`, `STOU`, `APPE`, và `ABOR` nếu muốn show chuẩn, lặp lại được, ít phụ thuộc thao tác tay
- **Bằng chứng mạnh nhất** vẫn là full test suite trong `test/`

Nếu bạn muốn, có thể mở rộng file này thành bản "1 trang checklist" ngắn hơn để mang đi defend và chỉ cần đọc theo thứ tự lệnh.
