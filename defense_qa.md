# Bộ câu hỏi - trả lời vấn đáp Hybrid FTP

Tài liệu này mô phỏng phần vấn đáp của giảng viên dựa trên `docs.md` và phần hiện thực trong repository. Mục tiêu là giúp trình bày đầy đủ kiến trúc, giao thức, xử lý lỗi, demo và phần triển khai kỹ thuật.

## 1. Kiến trúc tổng thể

**Câu 1.** Em hãy giải thích kiến trúc tổng thể của Hybrid FTP.

**Trả lời:**
Hybrid FTP tách rõ hai mặt phẳng: control plane dùng TCP để truyền lệnh và phản hồi, còn data plane dùng UDP để truyền dữ liệu file thực tế. Mô hình này bám theo tinh thần của FTP chuẩn, nhưng phần data channel được tự hiện thực lại bằng reliable UDP ở tầng ứng dụng.

**Câu 2.** Vì sao dự án này không dùng một thư viện FTP có sẵn?

**Trả lời:**
Vì đề bài yêu cầu tự xây dựng giao thức trên socket thấp cấp, không dùng FTP framework hay transfer library như libcurl FTP wrappers, QUIC, KCP. Mục tiêu là chứng minh hiểu rõ cơ chế TCP control, UDP data, và cơ chế đảm bảo tin cậy do chính mình thiết kế.

**Câu 3.** Tại sao lại tách control channel và data channel?

**Trả lời:**
Control channel cần tính ổn định để trao đổi lệnh, trạng thái phiên, và mã phản hồi. Data channel cần tối ưu cho luồng dữ liệu file. Tách hai kênh giúp mô hình rõ ràng hơn, dễ kiểm soát session, và phản ánh đúng kiến trúc FTP thực tế.

## 2. Control channel TCP

**Câu 4.** Control channel được triển khai ở đâu trong code?

**Trả lời:**
TCP server nằm ở [server/server.py](server/server.py), còn logic xử lý từng session nằm ở [server/session.py](server/session.py). Client TCP nằm ở [client/ftp_client.py](client/ftp_client.py) và CLI nằm ở [client/command_handler.py](client/command_handler.py).

**Câu 5.** Một client kết nối vào server thì chuyện gì xảy ra?

**Trả lời:**
Server accept kết nối, tạo một thread riêng cho client đó, rồi khởi tạo một đối tượng `ClientSession` riêng. Session đó sẽ giữ toàn bộ state như đăng nhập, thư mục hiện tại, chế độ dữ liệu, và trạng thái transfer.

**Câu 6.** Session state được cô lập như thế nào?

**Trả lời:**
Mỗi connection có một instance `ClientSession` riêng, nên các biến như `_auth_state`, `_cwd`, `_data_mode`, `_rnfr_path`, `_transfer_thread` không dùng chung giữa các client. Vì vậy, client này đổi `CWD` không làm client khác bị đổi theo.

**Câu 7.** Có cần một session manager riêng không?

**Trả lời:**
Không bắt buộc. Hiện tại `FTPServer` đóng vai trò nhận connection và tạo `ClientSession`. Mỗi `ClientSession` tự quản lý phiên của chính nó. Chỉ khi muốn thống kê online users, ngắt client từ xa, hay broadcast thì mới cần một registry hoặc session manager ở mức server.

## 3. Data channel UDP và reliable UDP

**Câu 8.** Tại sao dùng UDP cho data channel thay vì TCP?

**Trả lời:**
Vì đề yêu cầu tự xây reliable layer trên UDP. Mục tiêu là chứng minh có thể tự xử lý ACK, timeout, retransmit, duplicate suppression, và ordering ở tầng ứng dụng. Nếu dùng TCP cho data thì không còn phần kỹ thuật đó nữa.

**Câu 9.** Header UDP custom gồm những trường gì?

**Trả lời:**
Theo `common/packet.py`, packet có magic, version, flags, transfer ID, sequence number, acknowledgement number, payload length, và checksum. Đây là phần lõi để nhận diện gói, phát hiện lỗi, và điều khiển luồng truyền dữ liệu.

**Câu 10.** Reliable UDP của project này hoạt động theo nguyên tắc nào?

**Trả lời:**
Sender chia file thành từng chunk, gắn sequence number, gửi theo cửa sổ trượt, chờ ACK cumulatively. Nếu timeout thì retransmit. Receiver chỉ nhận đúng gói kế tiếp, loại bỏ gói lỗi hoặc gói trùng, rồi gửi ACK cho sequence tiếp theo mong đợi.

**Câu 11.** Làm sao phát hiện gói tin bị lỗi hoặc bị sửa?

**Trả lời:**
Mỗi datagram có checksum CRC-32 ở tầng packet để phát hiện lỗi truyền. Sau khi transfer hoàn tất, hai phía còn so SHA-256 của file để xác nhận toàn vẹn end-to-end.

**Câu 12.** Làm sao xử lý duplicate và out-of-order packet?

**Trả lời:**
Receiver chỉ chấp nhận packet có sequence number đúng bằng `expected sequence`. Nếu gói trùng hoặc lệch thứ tự, receiver không ghi dữ liệu lặp, mà gửi lại ACK hiện tại để sender biết mốc tiến trình chính xác.

**Câu 13.** Sender và receiver state machine được hiện thực ở đâu?

**Trả lời:**
Sender nằm trong [transport/udp_sender.py](transport/udp_sender.py), receiver nằm trong [transport/udp_receiver.py](transport/udp_receiver.py). Hai module này là phần cốt lõi của reliable UDP.

## 4. FTP command set

**Câu 14.** Những lệnh FTP nào được hỗ trợ?

**Trả lời:**
Project hỗ trợ toàn bộ nhóm lệnh trong `docs.md`: `USER`, `PASS`, `QUIT`, `NOOP`, `PWD`, `CWD`, `CDUP`, `MKD`, `RMD`, `LIST`, `NLST`, `STAT`, `SIZE`, `MDTM`, `TYPE`, `MODE`, `PORT`, `PASV`, `RETR`, `STOR`, `STOU`, `APPE`, `DELE`, `RNFR`, `RNTO`, `HASH`, `ABOR`, và `HELP`.

**Câu 15.** Lệnh nào được phép trước khi đăng nhập?

**Trả lời:**
Các lệnh tiền đăng nhập là `USER`, `PASS`, `QUIT`, `HELP`, và `NOOP`. Những lệnh còn lại yêu cầu trạng thái login thành công.

**Câu 16.** Ý nghĩa của `TYPE A` và `TYPE I` là gì?

**Trả lời:**
`TYPE A` là ASCII mode dành cho văn bản, còn `TYPE I` là binary mode cho file nhị phân như ảnh, PDF, zip, video. Trong project này, việc đọc ghi file vẫn an toàn với cả hai kiểu dữ liệu.

**Câu 17.** `MODE S` có ý nghĩa gì? Tại sao chỉ hỗ trợ `S`?

**Trả lời:**
`MODE S` là stream mode. Project chỉ hiện thực stream vì phù hợp với phạm vi đề và dễ kết hợp với reliable UDP tự xây. `MODE B` và `MODE C` không được hỗ trợ, nên server trả về không thực thi.

**Câu 18.** `PASV` và `PORT` khác nhau thế nào?

**Trả lời:**
`PASV` là passive mode: server mở cổng data tạm và client chủ động connect đến. `PORT` là active mode: client mở listener, server connect ngược lại. Cả hai đều chỉ là kênh điều khiển data-connection; payload file vẫn đi qua UDP.

**Câu 19.** `STOR`, `RETR`, `STOU`, `APPE` khác nhau ra sao?

**Trả lời:**
`STOR` upload file vào tên đích do client chỉ định. `RETR` tải file từ server về client. `STOU` upload với tên duy nhất do server tự sinh. `APPE` append dữ liệu vào file đích thay vì ghi đè.

**Câu 20.** `RNFR` và `RNTO` hoạt động theo chuỗi thế nào?

**Trả lời:**
`RNFR` đánh dấu file nguồn và chuyển session sang trạng thái chờ đổi tên. `RNTO` lấy tên đích và thực hiện rename. Nếu gọi `RNTO` mà chưa có `RNFR`, server trả lỗi bad sequence.

**Câu 21.** `ABOR` có phải chỉ là lệnh giả lập không?

**Trả lời:**
Không. `ABOR` là abort thật. Nó đặt cancel event của transfer đang chạy, đóng các socket liên quan, làm sender/receiver dừng lại, và upload dở sẽ không được publish thành file hoàn chỉnh.

## 5. File system và sandbox

**Câu 22.** Làm sao đảm bảo client không thoát ra ngoài thư mục storage?

**Trả lời:**
Toàn bộ path đi qua `FileManager.resolve()` trong [server/file_manager.py](server/file_manager.py), nơi path được chuẩn hóa và kiểm tra để đảm bảo vẫn nằm trong `storage_root`. Nhờ đó traversal như `../../` bị chặn.

**Câu 23.** Tại sao cùng một storage nhưng vẫn nói là session được cô lập?

**Trả lời:**
Vì cô lập ở đây là cô lập trạng thái phiên, không phải cô lập dữ liệu trên disk. Hai client dùng chung file system của server, nhưng mỗi client có `PWD`, login state, transfer mode, và trạng thái transfer riêng.

**Câu 24.** Khi upload bị abort, file dở được xử lý thế nào?

**Trả lời:**
Server ghi vào file tạm trước. Chỉ khi transfer thành công mới replace hoặc append vào file thật. Nếu transfer bị abort hoặc lỗi, file tạm sẽ bị xóa trong `finally`, nên file đích không bị để lại một bản dang dở.

## 6. Concurrency và session isolation

**Câu 25.** Server concurrent bằng cơ chế gì?

**Trả lời:**
Server dùng multi-threading: mỗi client connection được gán một thread riêng. Điều này cho phép nhiều client làm việc đồng thời mà không chặn nhau trên control channel.

**Câu 26.** Làm sao chứng minh các session không dính nhau?

**Trả lời:**
Cách test gọn nhất là mở hai client cùng lúc. Client 1 `MKD` hoặc `CWD` sang một thư mục riêng, còn client 2 vẫn `PWD` theo session của nó. Nếu client 2 không bị đổi theo client 1, nghĩa là session state đã được isolate đúng.

**Câu 27.** Có test tự động cho concurrency không?

**Trả lời:**
Có. `test/test_server.py` có test `test_two_clients_isolated` trong nhóm `ConcurrencyTests`. Test này xác nhận một client tạo directory thì client còn lại vẫn giữ working directory riêng.

## 7. Client CLI và demo helper

**Câu 28.** Dùng CLI chính để demo những gì?

**Trả lời:**
CLI chính ở [client/main.py](client/main.py) và [client/command_handler.py](client/command_handler.py) phù hợp cho `CONNECT`, `USER`, `PASS`, `PWD`, `CWD`, `MKD`, `RMD`, `LIST`, `NLST`, `SIZE`, `MDTM`, `HASH`, `TYPE`, `STOR`, `RETR`, `RNFR`, `RNTO`, `DELE`, `QUIT`, `HELP`.

**Câu 29.** Khi nào cần dùng helper file `raw_demo.py`?

**Trả lời:**
Khi muốn demo các lệnh khó thể hiện gọn trong REPL, như `MODE`, `STAT`, `STOU`, `APPE`, `ABOR`, hoặc khi cần verify raw reply của server. Helper này nằm ở [defense_demo/raw_demo.py](defense_demo/raw_demo.py).

**Câu 30.** Demo `ABOR` đúng cách như thế nào?

**Trả lời:**
Phải tạo đúng bối cảnh đang transfer dở: mở data connection, gửi `STOR`, sau đó lập tức gửi `ABOR`. Sau đó kiểm tra rằng file đích không được tạo. Đây là demo quan trọng để chứng minh abort là thật chứ không phải mô phỏng.

**Câu 31.** Demo active mode nên làm sao cho rõ?

**Trả lời:**
Nên dùng `FTPClient.upload_active()` và `download_active()` trong một script ngắn hoặc trình bày cùng output. Cách này rõ hơn việc cố làm bằng tay trong REPL vì active mode liên quan đến việc client mở listener và server connect ngược lại.

## 8. Reply codes và xử lý lỗi

**Câu 32.** Server trả những reply code nào là quan trọng nhất?

**Trả lời:**
Các code quan trọng gồm `220` login greeting, `230` login thành công, `331` yêu cầu password, `150` mở data connection, `226` transfer hoàn tất, `250` thao tác file thành công, `257` tạo directory, `426` transfer aborted, `425` không mở được data connection, `450` file unavailable tạm thời, `500/501/502/530/550` cho các lỗi cú pháp, tham số, lệnh không hỗ trợ, chưa đăng nhập, hoặc file không tồn tại.

**Câu 33.** Khi client gửi lệnh sai cú pháp thì server làm gì?

**Trả lời:**
Server trả lỗi syntax hoặc parameter error tùy trường hợp. Ví dụ lệnh thiếu tham số sẽ trả `501`, còn command không hợp lệ sẽ trả `500` hoặc `502` tùy mức độ lỗi.

**Câu 34.** Nếu đang transfer mà client gửi lệnh khác thì sao?

**Trả lời:**
Session sẽ trả `450 Transfer already in progress` cho các lệnh không phải `ABOR` hoặc `QUIT`. Điều này tránh việc một session bị đè trạng thái transfer giữa chừng.

## 9. Kiểm thử và bằng chứng demo

**Câu 35.** Bộ test của project chứng minh những gì?

**Trả lời:**
Test cover auth, directory operations, transfer, active/passive mode, reliable UDP, ABOR, hash integrity, và concurrency isolation. Đây là bằng chứng mạnh nhất cho phần defend.

**Câu 36.** Nếu giảng viên hỏi “làm sao biết file transfer không bị lỗi dữ liệu?” thì trả lời thế nào?

**Trả lời:**
Em sẽ nói project kiểm tra hai lớp: CRC-32 cho từng packet để phát hiện lỗi truyền, và SHA-256 của file sau transfer để so toàn vẹn end-to-end. Nếu hai digest khớp và test pass thì dữ liệu được bảo toàn.

**Câu 37.** Nếu giảng viên hỏi “điểm khác biệt lớn nhất của project em so với FTP demo thông thường là gì?” thì trả lời thế nào?

**Trả lời:**
Khác biệt lớn nhất là data plane dùng UDP tự xây reliability layer, không dựa vào TCP hay thư viện bên ngoài. Ngoài ra còn có session isolation, active/passive mode, ABOR thật, append/unique upload, và kiểm thử đầy đủ.

## 10. Câu hỏi tổng kết dễ bị hỏi trong bảo vệ

**Câu 38.** Nếu phải tóm tắt project trong 30 giây, em sẽ nói gì?

**Trả lời:**
Em hiện thực một Hybrid FTP tách TCP control và UDP data. Control channel quản lý login, lệnh FTP, session state; data channel truyền file bằng reliable UDP tự xây với ACK, timeout, retransmit, duplicate suppression, và checksum. Server đa luồng, cô lập session theo từng client, hỗ trợ upload/download, directory operations, rename, append, unique upload, active/passive mode, hash verification, và abort transfer.

**Câu 39.** Nếu giảng viên hỏi vì sao phần này đáng điểm cao, em trả lời ra sao?

**Trả lời:**
Vì project không chỉ chạy được mà còn cho thấy hiểu sâu giao thức: phân tầng control/data, thiết kế packet, xử lý lỗi truyền tin, xử lý concurrent sessions, sandbox filesystem, và có test + demo evidence rõ ràng.

**Câu 40.** Điều gì là điểm yếu còn có thể bị hỏi tiếp?

**Trả lời:**
Phần dễ bị hỏi là mức độ mở rộng của concurrency và việc chưa có session manager trung tâm riêng. Tuy nhiên hiện tại session state đã được cô lập đúng cách bằng instance `ClientSession`, nên yêu cầu bài toán vẫn được đáp ứng.

---

## Gợi ý cách học để vấn đáp

1. Học theo 4 lớp: kiến trúc, command set, reliable UDP, demo/test.
2. Với mỗi lệnh FTP, nhớ được: mục đích, reply code, và file/code path liên quan.
3. Khi trả lời, luôn nhấn mạnh 3 ý: đúng protocol, đúng session isolation, đúng integrity.
4. Nếu bị hỏi khó, quay về 3 bằng chứng lớn nhất: `docs.md`, test suite, và helper demo.

## 11. Câu hỏi nâng cao bám sát code

**Câu 41.** Vì sao server chỉ cho một transfer active trên mỗi session, và chỗ nào trong code quyết định điều này?

**Trả lời:**
Mỗi session chỉ nên có một transfer active để tránh chồng state giữa hai file transfer cùng lúc trong cùng một connection. Quy tắc này nằm trong [_start_transfer()](server/session.py#L738) và [_transfer_is_active()](server/session.py#L781). Khi `_transfer_thread` đã tồn tại, session sẽ trả `450 Transfer already in progress` thay vì mở transfer mới.

**Câu 42.** Nếu hai client upload cùng lúc thì code nào chứng minh là server vẫn xử lý được?

**Trả lời:**
Điểm then chốt là [FTPServer](server/server.py#L20) tạo thread riêng cho từng connection và mỗi connection lại có một [ClientSession](server/session.py#L30) riêng. Upload đi qua [_cmd_stor()](server/session.py#L493), sau đó gọi [_do_receive()](server/session.py#L658) và [_start_transfer()](server/session.py#L738), nên mỗi client có worker transfer riêng.

**Câu 43.** Nếu hai client cùng upload nhưng vào cùng một tên file thì điều gì xảy ra?

**Trả lời:**
Server không có global file lock cho toàn bộ storage, nên đây là vùng có race condition. [FileManager.rename()](server/file_manager.py#L125) và [FileManager.delete_file()](server/file_manager.py#L122) thao tác trực tiếp lên filesystem, còn upload trong [_receive_file()](server/session.py#L671) sẽ replace hoặc append file đích. Nếu hai session cùng đích, kết quả phụ thuộc timing: dữ liệu ghi sau có thể ghi đè dữ liệu trước.

**Câu 44.** Tại sao upload không ghi trực tiếp vào file đích mà phải qua file tạm?

**Trả lời:**
Để đảm bảo atomicity ở mức ứng dụng: file chỉ được publish khi transfer thành công. Cơ chế nằm trong [_receive_file()](server/session.py#L671), nơi server ghi vào `temp_dest`, rồi mới `replace(path)` hoặc append sang file thật. Nếu có lỗi hoặc `ABOR`, file tạm sẽ bị xóa trong `finally`.

**Câu 45.** `ABOR` thật sự cắt transfer bằng cách nào?

**Trả lời:**
Khi client gửi `ABOR`, session gọi [_cmd_abor()](server/session.py#L569). Hàm này gọi [_cancel_active_transfer()](server/session.py#L795), set cancel event và đóng các socket đang dùng. Worker transfer trong [_send_file()](server/session.py#L692) hoặc [_receive_file()](server/session.py#L714) sẽ thấy cancel event và dừng, sau đó `finally` giải phóng tài nguyên.

**Câu 46.** `ABOR` khác gì với việc client tự đóng kết nối?

**Trả lời:**
`ABOR` là một lệnh điều khiển hợp lệ nên server biết rõ transfer nào bị hủy và trả mã phản hồi `426 Transfer aborted` hoặc `226 No transfer in progress` nếu không có transfer. Còn nếu client tự drop socket thì server chỉ phát hiện lỗi I/O hoặc EOF trong vòng đọc/transfer, không có ngữ nghĩa rõ như một lệnh abort có chủ ý.

**Câu 47.** Passive mode được chọn host và port như thế nào?

**Trả lời:**
Trong [_cmd_pasv()](server/session.py#L413), server bind một socket TCP tạm bằng `bind((self._config.host, 0))`, sau đó lấy port thực tế từ `getsockname()`. Host trả cho client được tính bằng [_pasv_host()](server/session.py#L424): nếu có `advertise_host` thì dùng giá trị đó, còn nếu không thì ưu tiên local socket address hoặc `ServerConfig.host`.

**Câu 48.** Tại sao `PASV` lại có thêm `advertise_host`?

**Trả lời:**
Vì khi server bind `0.0.0.0`, IP đó không phải địa chỉ client ngoài LAN có thể connect đến. `advertise_host` trong [common/config.py](common/config.py#L9) cho phép server trả về một IP LAN hợp lệ trong `227 Entering Passive Mode (...)`, giúp client ở máy khác vẫn kết nối đúng.

**Câu 49.** Active mode được hiện thực ở đâu, và server connect ngược lại ra sao?

**Trả lời:**
Active mode được set trong [_cmd_port()](server/session.py#L394). Server parse chuỗi `h1,h2,h3,h4,p1,p2`, lưu `_active_host` và `_active_port`, rồi khi cần data connection sẽ đi qua [_open_data_connection()](server/session.py#L781) và `socket.connect((self._active_host, self._active_port))`.

**Câu 50.** Vì sao transfer ID lại cần thiết nếu mỗi session đã riêng?

**Trả lời:**
Session riêng chỉ tách control state, nhưng trong cùng một session, file transfer vẫn cần một định danh riêng để phân biệt packet của transfer hiện tại. `_next_transfer_id()` trong [server/session.py](server/session.py#L767) cấp ID tăng dần, còn [UDPSender](transport/udp_sender.py) và [UDPReceiver](transport/udp_receiver.py) dùng transfer ID đó để loại bỏ packet của luồng khác.

**Câu 51.** Nếu packet UDP bị lỗi checksum thì xử lý ở tầng nào?

**Trả lời:**
Ở tầng packet parsing/receiver. `common/packet.py` chịu trách nhiệm encode/decode packet và checksum, còn [UDPReceiver](transport/udp_receiver.py) chỉ chấp nhận packet hợp lệ. Packet lỗi sẽ bị bỏ qua hoặc không được ghi vào file đích.

**Câu 52.** Vì sao `unique_path()` không đủ để chống race khi nhiều client cùng `STOU`?

**Trả lời:**
`unique_path()` trong [server/file_manager.py](server/file_manager.py#L138) chỉ kiểm tra tên hiện tại rồi chọn tên chưa tồn tại tại thời điểm đó. Nó không phải lock toàn cục, nên nếu nhiều session cùng kiểm tra một lúc thì vẫn có khả năng đụng nhau. Với bài demo, mục tiêu chính là tạo tên khác biệt hợp lý, không phải atomic reservation toàn cục.

**Câu 53.** `FileManager.resolve()` đang bảo vệ điều gì quan trọng nhất?

**Trả lời:**
Nó bảo vệ sandbox filesystem. Hàm [resolve()](server/file_manager.py#L24) ghép virtual path với `storage_root`, rồi `relative_to()` để đảm bảo path thật không thoát khỏi root. Đây là lớp phòng thủ chính chống path traversal như `../`.

**Câu 54.** Nếu đang transfer mà client gửi `PWD`, server xử lý ra sao?

**Trả lời:**
Trong [_dispatch()](server/session.py#L147), server kiểm tra `_transfer_is_active()`. Nếu transfer đang chạy và lệnh không phải `ABOR` hoặc `QUIT`, session sẽ trả `450 Transfer already in progress`. Điều này ngăn việc đổi state control trong lúc data transfer chưa xong.

**Câu 55.** Tại sao `QUIT` vẫn được cho phép ngay khi đang transfer?

**Trả lời:**
Vì `QUIT` là lệnh đóng session có chủ ý. Trong [_dispatch()](server/session.py#L147), `QUIT` được loại khỏi danh sách bị chặn khi transfer active, rồi [_cmd_quit()](server/session.py#L227) sẽ gửi `221 Goodbye` và dọn transfer đang chạy bằng [_cancel_active_transfer()](server/session.py#L795).

**Câu 56.** Chỗ nào chứng minh server có rollback khi transfer lỗi?

**Trả lời:**
Trong [_receive_file()](server/session.py#L714), nếu receiver ném lỗi hoặc có `OSError`, code sẽ đi vào `except` và `finally` để xóa file tạm. Với upload thành công, file tạm mới được `replace()` sang đích. Đây là rollback mức ứng dụng cho các transfer dang dở.

**Câu 57.** Khi giảng viên hỏi “em có thật sự viết reliable UDP từ đầu không?”, em chỉ code nào?

**Trả lời:**
Em có thể chỉ vào [transport/udp_sender.py](transport/udp_sender.py) và [transport/udp_receiver.py](transport/udp_receiver.py), cùng với [common/packet.py](common/packet.py) và [common/checksum.py](common/checksum.py). Các file này tự định nghĩa packet format, ACK, retransmit, checksum và logic gửi/nhận file, không dựa trên thư viện transfer sẵn có.

**Câu 58.** Nếu phải chứng minh concurrency bằng code chứ không chỉ bằng lời nói, em sẽ trích đâu?

**Trả lời:**
Em sẽ trích [server/server.py](server/server.py#L41) để chỉ ra `_accept_loop()` tạo thread theo client, rồi [server/session.py](server/session.py#L30) để cho thấy mỗi connection có `ClientSession` riêng. Nếu hỏi transfer concurrency, em chỉ thêm [_start_transfer()](server/session.py#L738) để chứng minh mỗi session còn có transfer thread riêng.

**Câu 59.** Nếu giảng viên hỏi “tại sao không dùng process thay vì thread?”, em trả lời sao?

**Trả lời:**
Thread đủ cho bài toán I/O-bound này vì phần lớn thời gian là chờ network/socket. Dùng thread đơn giản hơn trong chia sẻ `storage_root` và session state, còn process sẽ phức tạp hơn ở đồng bộ tài nguyên và giao tiếp giữa tiến trình. Yêu cầu của đề chỉ cần multi-threaded hoặc multi-process server với session cô lập, nên thread là hợp lý.

**Câu 60.** Điểm yếu kỹ thuật nào còn có thể bị hỏi tiếp sau khi em trình bày phần này?

**Trả lời:**
Điểm yếu dễ bị hỏi là upload cùng một file đích từ nhiều client chưa có global file lock hoặc versioning. Em nên nói rõ là hệ thống cô lập session state rất tốt, nhưng nếu hai client cùng ghi vào đúng một target path thì đây là race ở filesystem, không phải lỗi của session isolation.
