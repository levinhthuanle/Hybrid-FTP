hybrid-ftp/
│
├── client/
│   ├── main.py
│   ├── ftp_client.py
│   ├── command_handler.py
│   ├── download/
│   └── upload/
│
├── server/
│   ├── main.py
│   ├── ftp_server.py
│   ├── session.py
│   ├── auth.py
│   ├── file_manager.py
│   └── storage/
│
├── common/
│   ├── packet.py
│   ├── protocol.py
│   ├── checksum.py
│   ├── config.py
│   └── constants.py
│
├── transport/
│   ├── tcp_control.py
│   ├── udp_sender.py
│   ├── udp_receiver.py
│   └── reliability.py
│
├── report/
│
├── test_files/
│   ├── sample.txt
│   ├── sample.pdf
│   └── sample.jpg
│
└── README.md