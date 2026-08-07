# Bộ câu hỏi - trả lời chuyên sâu: Architecture, Common Module, Server/Session

Tài liệu này tập trung đúng vào 3 phần bạn làm: **architecture & protocol design**, **common module**, và **server/session management**. Mỗi câu đều đi kèm trả lời ngắn gọn theo kiểu vấn đáp và chỉ ra chỗ hiện thực trong code để bạn bám vào khi defend.

---

## A. Architecture & Protocol Design

**Câu 1.** Vì sao project này phải tách control channel và data channel?

**Trả lời:**
Vì control channel cần ổn định để truyền lệnh, trạng thái phiên và reply code, còn data channel cần tối ưu cho payload file. Tách hai kênh giúp mô hình rõ ràng hơn và bám đúng tinh thần FTP chuẩn: TCP cho điều khiển, UDP cho dữ liệu.

**Chỗ imple:** [server/server.py](server/server.py), [server/session.py](server/session.py), [client/ftp_client.py](client/ftp_client.py)

---

**Câu 2.** Điểm thiết kế nào khiến project này vẫn là "Hybrid FTP" chứ không phải FTP thuần TCP?

**Trả lời:**
Điểm khác biệt nằm ở data plane dùng UDP tự xây reliable layer thay vì để TCP gánh luôn transfer file. Control vẫn là TCP, nhưng payload đi qua UDP với ACK, sequence, timeout, retransmit, checksum.

**Chỗ imple:** [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py), [common/packet.py](common/packet.py)

---

**Câu 3.** Nếu giảng viên hỏi "vì sao không dùng một thư viện FTP sẵn có?" thì em trả lời thế nào?

**Trả lời:**
Vì đề bài bắt buộc dùng socket thấp cấp và tự hiện thực giao thức tin cậy. Dùng thư viện FTP có sẵn sẽ làm mất phần quan trọng nhất của bài: thiết kế packet, xử lý loss/reorder/corruption, và quản lý session theo yêu cầu đề.

**Chỗ imple:** Kiến trúc tổng thể trong [README.md](README.md), mô tả yêu cầu trong [docs.md](docs.md)

---

**Câu 4.** Protocol design của control channel được xây như thế nào?

**Trả lời:**
Control channel là protocol line-oriented: mỗi lệnh là một dòng ASCII/UTF-8, kết thúc bằng CRLF, server parse ra `Command(name, argument)` rồi trả reply code + message theo chuẩn FTP.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 5.** Tại sao project phải chuẩn hóa command name thành uppercase khi parse?

**Trả lời:**
Để lệnh không phụ thuộc cách người dùng gõ `stor`, `Stor` hay `STOR`. Điều này làm control protocol dễ dùng hơn và tránh lỗi do viết hoa/viết thường khác nhau.

**Chỗ imple:** [common/protocol.py](common/protocol.py), hàm `parse_command()`

---

**Câu 6.** Ý nghĩa của reply code trong design là gì?

**Trả lời:**
Reply code là ngôn ngữ trạng thái của FTP. Nó cho client biết lệnh thành công, đang chờ, hay bị lỗi loại nào. Nhờ đó client có thể quyết định bước tiếp theo mà không cần suy đoán từ message text.

**Chỗ imple:** [common/protocol.py](common/protocol.py), `ReplyCode`, `format_reply()`

---

**Câu 7.** Vì sao project vẫn cần `HELP` nếu đã có CLI?

**Trả lời:**
`HELP` là một phần của protocol và là bằng chứng rằng server hiểu command set theo spec. Ngoài ra, nó giúp demo nhanh syntax của từng lệnh ngay trong session đang chạy.

**Chỗ imple:** [common/protocol.py](common/protocol.py), [server/session.py](server/session.py), [client/command_handler.py](client/command_handler.py)

---

**Câu 8.** Cấu trúc tổng thể của luồng transfer file là gì?

**Trả lời:**
Client gửi control command `STOR/RETR/...` qua TCP, server phản hồi `150`, sau đó hai bên mở data connection, rồi UDP sender/receiver truyền file, cuối cùng server trả `226` nếu thành công.

**Chỗ imple:** [server/session.py](server/session.py), [client/ftp_client.py](client/ftp_client.py), [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

**Câu 9.** Vì sao có cả `PASV` và `PORT` trong design?

**Trả lời:**
Để hỗ trợ cả passive mode và active mode, đúng tinh thần FTP. `PASV` phù hợp khi client chủ động connect đến server; `PORT` phù hợp khi client mở listener và server connect ngược lại.

**Chỗ imple:** [server/session.py](server/session.py), [client/ftp_client.py](client/ftp_client.py)

---

**Câu 10.** Thiết kế này xử lý integrity như thế nào?

**Trả lời:**
Tầng packet dùng CRC-32 để phát hiện lỗi datagram, còn tầng file dùng SHA-256 để so digest sau transfer. Hai lớp này bổ trợ nhau: một lớp chống packet corruption, một lớp chứng minh file cuối cùng không đổi.

**Chỗ imple:** [common/checksum.py](common/checksum.py), [common/packet.py](common/packet.py), [server/session.py](server/session.py), [client/ftp_client.py](client/ftp_client.py)

---

## B. Common Module

**Câu 11.** `common/config.py` có vai trò gì trong kiến trúc?

**Trả lời:**
Đây là nơi gom toàn bộ cấu hình mặc định của server và client: host, port, storage root, timeout, window size. Nhờ đó các thành phần khác không hardcode giá trị và việc test/demo dễ hơn.

**Chỗ imple:** [common/config.py](common/config.py)

---

**Câu 12.** Vì sao cần `ServerConfig` và `ClientConfig` tách riêng?

**Trả lời:**
Vì server và client có bộ tham số khác nhau. Server cần storage root, control backlog, UDP retry policy; client cần download/upload root và host/port kết nối. Tách riêng giúp code rõ ràng và tránh nhầm config giữa hai vai trò.

**Chỗ imple:** [common/config.py](common/config.py)

---

**Câu 13.** `common/protocol.py` đang gánh những trách nhiệm nào?

**Trả lời:**
Nó gánh 3 việc: định nghĩa command syntax, định nghĩa reply code, và xử lý encode/decode lệnh control. Đây là lớp protocol dùng chung cho cả server và client.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 14.** `parse_command()` bảo vệ những gì?

**Trả lời:**
Hàm này kiểm tra command line không rỗng, không quá dài, tên lệnh chỉ gồm ASCII letters, và tách command/argument chuẩn. Nhờ đó server không phải xử lý các dòng control bẩn hoặc sai format ở tầng sau.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 15.** `format_reply()` có quan trọng không, hay chỉ là tiện ích?

**Trả lời:**
Nó rất quan trọng vì đảm bảo mọi reply của server đều theo đúng wire format `<code> <message>\r\n`. Nếu format sai, client sẽ không đọc được reply ổn định.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 16.** `ReplyCode` được mã hóa dưới dạng gì và vì sao?

**Trả lời:**
Reply code là `IntEnum`, nên vừa có ý nghĩa đọc được trong code, vừa trực tiếp dùng được như số nguyên trên wire protocol. Điều này giúp code dễ bảo trì mà vẫn giữ đúng định dạng FTP.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 17.** Vì sao `FTP_COMMAND_SYNTAX` phải nằm ở module common?

**Trả lời:**
Vì cả server lẫn client CLI đều cần cùng một bộ syntax chuẩn: server dùng để trả `HELP`, client dùng để hiển thị gợi ý cho người dùng. Đặt ở common tránh lệch tài liệu giữa hai phía.

**Chỗ imple:** [common/protocol.py](common/protocol.py), [server/session.py](server/session.py), [client/command_handler.py](client/command_handler.py)

---

**Câu 18.** `common/packet.py` hiện thực packet layer như thế nào?

**Trả lời:**
Nó định nghĩa một `UDPPacket` bất biến với các trường flags, transfer ID, sequence, acknowledgement, payload. Packet được serialize thành byte stream bằng struct format cố định và có checksum để xác minh tính toàn vẹn.

**Chỗ imple:** [common/packet.py](common/packet.py)

---

**Câu 19.** Vì sao packet lại cần `transfer_id`?

**Trả lời:**
Để phân biệt các transfer khác nhau, kể cả khi cùng một server đang xử lý nhiều session hoặc nhiều flow khác nhau. Nhờ transfer ID, receiver có thể bỏ qua datagram không thuộc luồng hiện tại.

**Chỗ imple:** [common/packet.py](common/packet.py), [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

**Câu 20.** Sequence và acknowledgement ở đây mang ý nghĩa gì?

**Trả lời:**
Sequence là số thứ tự packet dữ liệu, còn acknowledgement là packet tiếp theo receiver mong đợi. Cách dùng này cho phép ACK cộng dồn, hỗ trợ duplicate suppression và retransmit đơn giản hơn.

**Chỗ imple:** [common/packet.py](common/packet.py), [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

**Câu 21.** `HEADER_FORMAT` trong packet có vai trò gì?

**Trả lời:**
Đây là layout nhị phân cố định của header UDP custom. Nhờ header format thống nhất, sender và receiver có thể serialize/deserialize cùng một cấu trúc byte mà không lệch field.

**Chỗ imple:** [common/packet.py](common/packet.py)

---

**Câu 22.** Checksum được tính trên phần nào của packet?

**Trả lời:**
Checksum được tính trên header với checksum field bằng 0 cộng với payload. Cách này giúp receiver tái tính checksum và phát hiện packet bị sửa hoặc corrupt trên đường truyền.

**Chỗ imple:** [common/packet.py](common/packet.py), [common/checksum.py](common/checksum.py)

---

**Câu 23.** Khi packet nhận vào sai magic hoặc sai version thì sao?

**Trả lời:**
Packet sẽ bị loại ngay ở bước decode vì nó không thuộc đúng định dạng giao thức của project. Điều này giúp tránh nhầm packet từ protocol khác hoặc packet cũ không tương thích.

**Chỗ imple:** [common/packet.py](common/packet.py)

---

**Câu 24.** `MAX_UDP_PAYLOAD` ảnh hưởng thế nào đến thiết kế transfer?

**Trả lời:**
Nó quyết định kích thước chunk dữ liệu tối đa trong một packet. Sender phải chia file thành các chunk không vượt quá giới hạn này, còn receiver dùng chính giới hạn đó để kiểm tra payload hợp lệ.

**Chỗ imple:** [common/constants.py](common/constants.py), [common/packet.py](common/packet.py), [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

## C. Server & Session Management

**Câu 25.** `FTPServer` đang làm đúng vai trò gì?

**Trả lời:**
`FTPServer` chỉ quản lý accept loop, tạo thread cho mỗi client, và lifecycle của server socket. Nó không giữ state nghiệp vụ của từng client; phần đó được giao cho `ClientSession`.

**Chỗ imple:** [server/server.py](server/server.py)

---

**Câu 26.** Vì sao `FTPServer` không trực tiếp xử lý command?

**Trả lời:**
Vì command handling là stateful theo từng client. Nếu để server handle trực tiếp thì state của nhiều client sẽ bị trộn. Tách ra `ClientSession` giúp mỗi connection có state riêng, đúng với mô hình session.

**Chỗ imple:** [server/server.py](server/server.py), [server/session.py](server/session.py)

---

**Câu 27.** `ClientSession` đang giữ những state nào?

**Trả lời:**
Nó giữ auth state, pending username, current cwd, transfer type, data mode, active/passive endpoint, rename source state, transfer thread, cancel event, transfer sockets, và transfer ID counter. Đây là toàn bộ state của một phiên FTP.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 28.** Tại sao mỗi client nên có một `ClientSession` riêng?

**Trả lời:**
Để session isolation. Nếu dùng chung một object thì login state, cwd, transfer mode hay rename state sẽ bị lẫn giữa nhiều client. Tách instance riêng là cách đơn giản và đúng nhất cho yêu cầu này.

**Chỗ imple:** [server/server.py](server/server.py), [server/session.py](server/session.py)

---

**Câu 29.** `run()` trong `ClientSession` làm gì?

**Trả lời:**
Nó gửi greeting `220`, sau đó đọc từng control line, parse command, dispatch sang handler tương ứng, và cuối cùng dọn transfer/passive listener khi session kết thúc.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 30.** Tại sao session phải tự đọc line theo CRLF thay vì dùng `recv()` thô cho từng command?

**Trả lời:**
Vì control protocol là line-oriented. Đọc theo CRLF giúp đảm bảo một command được parse trọn vẹn, tránh tách dở command hoặc ghép nhiều command vào cùng một lần `recv()`.

**Chỗ imple:** [server/session.py](server/session.py), `run()` và `_readline()`

---

**Câu 31.** `_dispatch()` đang enforce những rule nào?

**Trả lời:**
Nó kiểm tra command có handler không, có cần login trước không, có đang transfer active không, và `QUIT` có được phép ngay cả khi transfer đang chạy. Đây là tầng kiểm soát luật protocol của session.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 32.** Vì sao có `_PREAUTH_COMMANDS`?

**Trả lời:**
Để định nghĩa rõ những lệnh nào được phép trước khi đăng nhập. Nhờ đó server không phải viết lặp lại logic kiểm tra login ở từng handler.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 33.** `_cmd_user()` và `_cmd_pass()` đang quản lý auth state thế nào?

**Trả lời:**
`USER` chuyển session sang `USERNAME_GIVEN` và lưu pending username. `PASS` chỉ hợp lệ sau `USER`; nếu verify thành công thì session sang `LOGGED_IN`, còn sai thì reset trạng thái về chưa login.

**Chỗ imple:** [server/session.py](server/session.py), [server/auth.py](server/auth.py)

---

**Câu 34.** Tại sao `PASS` trước `USER` lại phải trả lỗi?

**Trả lời:**
Vì đó là bad command sequence theo FTP semantics. Server cần biết username trước rồi mới verify password; nếu không, auth state sẽ không nhất quán.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 35.** `PWD`, `CWD`, `CDUP` đang dựa trên state nào?

**Trả lời:**
Chúng dựa trên `_cwd` của từng session. `CWD` đổi cwd theo path được resolve an toàn, `CDUP` đi lên thư mục cha, còn `PWD` trả lại virtual path tương ứng.

**Chỗ imple:** [server/session.py](server/session.py), [server/file_manager.py](server/file_manager.py)

---

**Câu 36.** `FileManager` đóng vai trò gì trong session management?

**Trả lời:**
Nó là lớp filesystem sandbox và path resolution. Session gọi `FileManager` để resolve path, list directory, create/remove dir, rename, delete, hash file, và đảm bảo mọi thao tác vẫn nằm trong `storage_root`.

**Chỗ imple:** [server/file_manager.py](server/file_manager.py)

---

**Câu 37.** `resolve()` bảo vệ chống tấn công gì?

**Trả lời:**
Nó chặn path traversal. Nếu user cố dùng `..` để thoát khỏi storage root, `resolve()` sẽ ném `PathError` thay vì trả path ra ngoài sandbox.

**Chỗ imple:** [server/file_manager.py](server/file_manager.py)

---

**Câu 38.** `_cmd_list()` và `_cmd_nlst()` khác nhau ở đâu?

**Trả lời:**
`LIST` trả dạng chi tiết giống `ls -l`, còn `NLST` chỉ trả tên file/thư mục. Cả hai đều mở data connection rồi gửi data qua TCP channel phụ trước khi trả `226`.

**Chỗ imple:** [server/session.py](server/session.py), [server/file_manager.py](server/file_manager.py)

---

**Câu 39.** `_cmd_stor()`, `_cmd_retr()`, `_cmd_stou()`, `_cmd_appe()` được điều phối ra sao?

**Trả lời:**
Chúng đều resolve path trước, mở data connection, rồi gọi sang worker transfer. `STOR` ghi đè file đích, `RETR` đọc file từ server, `STOU` sinh tên duy nhất, còn `APPE` append dữ liệu vào file đích.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 40.** Vì sao transfer trong session không chạy trực tiếp trên thread control?

**Trả lời:**
Vì nếu transfer chạy trực tiếp, control session sẽ bị block hoàn toàn. Tách transfer sang worker thread giúp session vẫn có thể xử lý cancel, cleanup và một số trạng thái đồng thời một cách rõ ràng hơn.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 41.** `_start_transfer()` giải quyết vấn đề gì?

**Trả lời:**
Nó tạo cancel event, gán transfer sockets, dựng worker thread, và đảm bảo trong một session chỉ có một transfer active. Nếu session đã có transfer chạy, lệnh mới sẽ bị từ chối bằng `450 Transfer already in progress`.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 42.** `_finish_transfer()` cần làm gì ngoài việc close socket?

**Trả lời:**
Nó còn phải reset transfer state trong session: cancel event, transfer thread, và tập socket tracking. Nếu không reset, session sẽ tưởng rằng transfer vẫn còn active và chặn lệnh tiếp theo.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 43.** `ABOR` được hiện thực thật như thế nào?

**Trả lời:**
Khi nhận `ABOR`, session gọi `_cancel_active_transfer()`, set cancel event và đóng các socket đang dùng. Worker transfer đang chạy sẽ thấy cancel event và dừng, sau đó `finally` dọn tài nguyên và trả `426` nếu transfer thật sự bị hủy.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 44.** Vì sao `QUIT` vẫn được phép trong lúc transfer active?

**Trả lời:**
Vì `QUIT` là lệnh đóng phiên có chủ ý. Server cho phép nó đi qua để session có thể dọn transfer và thoát sạch sẽ thay vì bắt client phải chờ transfer kết thúc.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 45.** Tại sao upload bị abort thì file đích không bị để lại dở?

**Trả lời:**
Vì server ghi vào file tạm trước, chỉ khi transfer thành công mới `replace()` hoặc append sang file thật. Nếu transfer lỗi hoặc bị cancel, file tạm sẽ bị xóa trong `finally`.

**Chỗ imple:** [server/session.py](server/session.py)

---

**Câu 46.** Session có xử lý concurrent client thế nào ở tầng server?

**Trả lời:**
`FTPServer` tạo một thread riêng cho mỗi connection, nên nhiều client có thể cùng chạy đồng thời. Mỗi thread giữ một `ClientSession` riêng nên state control không bị lẫn.

**Chỗ imple:** [server/server.py](server/server.py), [server/session.py](server/session.py)

---

**Câu 47.** Điểm yếu concurrency nào cần nói thật với giảng viên?

**Trả lời:**
Session state được cô lập tốt, nhưng filesystem là shared storage. Nếu hai client cùng ghi vào cùng một target path thì không có global file lock; đây là vùng có race condition ở mức filesystem, không phải session state.

**Chỗ imple:** [server/file_manager.py](server/file_manager.py), [server/session.py](server/session.py)

---

**Câu 48.** Nếu giảng viên hỏi "tại sao thread mà không phải process?" em nên trả lời gì?

**Trả lời:**
Bài toán này chủ yếu là I/O-bound. Thread đủ nhẹ để xử lý nhiều client đồng thời, dễ chia sẻ storage và state, và đúng với yêu cầu multi-threaded server trong đề.

**Chỗ imple:** [server/server.py](server/server.py)

---

## D. Câu hỏi phản biện khó hơn

**Câu 49.** Nếu `PASV` bind `0.0.0.0` thì client khác máy tính làm sao connect được?

**Trả lời:**
Server cần advertise một IP LAN thật cho client, không phải `0.0.0.0`. Vì vậy cấu hình `advertise_host` cho phép server trả về địa chỉ có thể reach từ máy khác trong mạng.

**Chỗ imple:** [common/config.py](common/config.py), [server/session.py](server/session.py)

---

**Câu 50.** Vì sao protocol cần cả `Command` object lẫn `ReplyCode` enum?

**Trả lời:**
`Command` giúp biểu diễn input control một cách typed và rõ ràng; `ReplyCode` giúp trả mã phản hồi thống nhất trên wire protocol. Hai lớp này làm code đỡ rối hơn so với xử lý chuỗi raw toàn bộ.

**Chỗ imple:** [common/protocol.py](common/protocol.py)

---

**Câu 51.** Nếu packet UDP bị duplicate thì receiver làm sao biết phải bỏ qua?

**Trả lời:**
Receiver dựa trên `transfer_id` và `sequence`. Chỉ packet thuộc đúng transfer và đúng sequence mong đợi mới được ghi. Packet trùng hoặc lệch thứ tự sẽ bị bỏ qua hoặc ACK lại mốc hiện tại.

**Chỗ imple:** [common/packet.py](common/packet.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

**Câu 52.** Nếu checksum fail thì project có cần sửa packet hay chỉ bỏ qua?

**Trả lời:**
Chỉ bỏ qua. Ý tưởng của reliable UDP là packet lỗi sẽ được phát hiện và tự retransmit bởi cơ chế timeout/ACK, chứ receiver không tự sửa dữ liệu corrupt.

**Chỗ imple:** [common/packet.py](common/packet.py), [transport/udp_receiver.py](transport/udp_receiver.py)

---

**Câu 53.** Nếu giảng viên hỏi "đâu là boundary giữa common module và server logic?" thì trả lời sao?

**Trả lời:**
`common` chỉ giữ protocol primitives: config, command/reply, packet, checksum. `server` chịu trách nhiệm session state, dispatch command, filesystem sandbox và transfer orchestration. Boundary này giúp code sạch và dễ test.

**Chỗ imple:** [common/config.py](common/config.py), [common/protocol.py](common/protocol.py), [common/packet.py](common/packet.py), [server/session.py](server/session.py)

---

**Câu 54.** Phần nào trong code là nơi dễ bị hỏi nhất về correctness?

**Trả lời:**
Dễ bị hỏi nhất là reliable UDP và session transfer flow, vì đây là nơi có nhiều state machine: packet-level state, transfer-level state và session-level state. Chỉ cần một state reset sai là transfer có thể treo hoặc publish file dở.

**Chỗ imple:** [transport/udp_sender.py](transport/udp_sender.py), [transport/udp_receiver.py](transport/udp_receiver.py), [server/session.py](server/session.py)

---

**Câu 55.** Câu trả lời ngắn gọn nhất để tổng kết phần em làm là gì?

**Trả lời:**
Em thiết kế protocol control/data tách bạch, common module chuẩn hóa command/reply/packet/config, và server/session quản lý state từng client với transfer isolation, sandbox filesystem và reliable UDP orchestration.

**Chỗ imple:** [common/protocol.py](common/protocol.py), [common/packet.py](common/packet.py), [common/config.py](common/config.py), [server/server.py](server/server.py), [server/session.py](server/session.py)

---

## Gợi ý dùng tài liệu này khi defend

- Nếu bị hỏi kiến trúc, trả lời theo luồng: **control TCP -> session -> data UDP -> integrity**.
- Nếu bị hỏi về common module, nhớ 3 trụ: **config, protocol, packet/checksum**.
- Nếu bị hỏi về server/session, luôn nhấn mạnh 2 ý: **mỗi client một `ClientSession`** và **transfer state được dọn sạch sau mỗi phiên**.
- Nếu giảng viên xoáy sâu, chỉ luôn vào file implementation ở dòng hoặc module đã ghi dưới mỗi câu.
