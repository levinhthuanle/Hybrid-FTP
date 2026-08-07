# Luồng tải file (`RETR`)

Sơ đồ này mô tả luồng tải file mặc định của dự án: **passive mode**. TCP được dùng để điều khiển và phối hợp; dữ liệu file đi qua các custom Reliable-UDP packet.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as Client CLI
    participant FC as FTPClient
    participant SC as ServerSession
    participant FS as Server storage

    CLI->>FC: RETR <filename>
    FC->>SC: TCP control: SIZE remote_name (tùy chọn)
    SC-->>FC: TCP control: 213 <total_bytes> (hoặc lỗi)

    FC->>SC: TCP control: PASV
    SC->>SC: Tạo TCP passive listener
    SC-->>FC: TCP control: 227 (server host, TCP data port)
    FC->>SC: TCP data: kết nối tới passive port

    FC->>SC: TCP control: RETR remote_name
    SC->>FS: Kiểm tra và mở file nguồn
    SC->>SC: Tạo UDP socket + transfer_id
    SC-->>FC: TCP control: 150 ... port=<udp_port> tid=<transfer_id>

    FC->>FC: Bind UDP socket tại cổng tạm thời của client
    FC->>SC: TCP data: gửi <client_udp_port>
    SC->>SC: Kết nối UDP socket tới client_udp_port

    loop Mỗi chunk file (tối đa 1200 bytes)
        SC-->>FC: UDP: custom packet DATA<br/>flags=DATA, tid, sequence, checksum, payload
        FC->>FC: Kiểm tra magic/version/length/CRC-32 và sequence
        FC-->>SC: UDP: custom packet ACK<br/>flags=ACK, tid, acknowledgement=sequence
        alt Không nhận được ACK trước timeout
            SC-->>FC: Gửi lại chính packet DATA
        end
    end

    SC-->>FC: UDP: custom packet FIN
    FC-->>SC: UDP: custom packet FIN_ACK
    FC->>FC: Ghi xong file và tính SHA-256 cục bộ

    SC->>SC: Đóng UDP socket và TCP data socket
    SC-->>FC: TCP control: 226 Transfer complete SHA-256=<digest>
    FC->>FC: So sánh SHA-256 cục bộ với digest server gửi
    FC-->>CLI: Download complete
```

## Ý nghĩa các kênh trong sơ đồ

- **TCP control**: gửi lệnh FTP (`SIZE`, `PASV`, `RETR`) và nhận response (`213`, `227`, `150`, `226`).
- **TCP data**: chỉ dùng ngắn hạn để client báo UDP port của nó cho server trong passive mode; không mang byte file.
- **UDP**: mang các packet `DATA`, `ACK`, `FIN`, `FIN_ACK`. Mỗi UDP datagram có UDP header chuẩn do hệ điều hành thêm và custom Reliable-UDP header 22 bytes do `common/packet.py` mã hóa.

`150` chứa UDP port và `transfer_id`; `226` chỉ được trả sau khi quá trình UDP hoàn thành và server đã có SHA-256 của file.
