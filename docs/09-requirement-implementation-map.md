# Requirement Implementation Map

This file is a defense-oriented answer key for the requirements in `docs.md`.
It explains, requirement by requirement, where the feature is implemented, how the runtime flow works, which files are involved, which reply codes are returned, and which tests prove the behavior.

## 1. Core architecture requirements

### 1.1 TCP control channel

- Control-channel socket lifecycle is implemented in `server/server.py:22-69`.
  - `FTPServer.start()` creates a TCP socket, binds to `ServerConfig.host:control_port`, listens, and accepts clients.
  - `_accept_loop()` creates one thread per client.
  - `_handle_client()` creates one `ClientSession` object per connection.
- Per-client command parsing and reply generation are implemented in `server/session.py:81-194`.
  - `run()` sends the `220` greeting, reads CRLF-delimited commands, parses them with `parse_command()`, and dispatches them through `_handlers`.
- TCP command framing is defined in `common/protocol.py:39-54`.
  - `parse_command()` uppercases the command name and preserves one optional argument string.
  - `format_reply()` emits standard FTP replies as `<code> <message>\r\n`.
- Client-side TCP control handling is implemented in `client/ftp_client.py:61-79`, `client/ftp_client.py:369-403`.
  - `connect()` opens the TCP socket and validates the `220` greeting.
  - `_cmd()` sends a CRLF-terminated command.
  - `_read_reply()` handles both single-line and multi-line FTP replies.

### 1.2 UDP data channel

- All file payload bytes are transferred over UDP, not over the TCP control socket.
- The UDP packet format is defined in `common/packet.py:20-91`.
  - Header fields: magic, version, flags, transfer ID, sequence number, acknowledgement number, payload length, checksum.
  - Header format is `!2sBBIIIHI`, total header size is 22 bytes.
- Shared protocol constants are defined in `common/constants.py:6-24`.
  - `MAX_UDP_PAYLOAD = 1024`
  - `DEFAULT_UDP_WINDOW_SIZE = 1`
  - `PacketFlag`: `DATA`, `ACK`, `FIN`, `FIN_ACK`, `ERROR`
- Sender logic is implemented in `transport/udp_sender.py:52-186`.
- Receiver logic is implemented in `transport/udp_receiver.py:51-147`.
- Server-side TCP/UDP coordination is implemented in `server/session.py:430-760`.
- Client-side TCP/UDP coordination is implemented in `client/ftp_client.py:208-364`.

### 1.3 Reliable UDP requirement

- Reliability is implemented at application level, not by any third-party transport library.
- Integrity and corruption detection:
  - CRC-32 per datagram: `common/checksum.py:10-13`, `common/packet.py:51-90`
  - SHA-256 per file: `common/checksum.py:16-23`
- Loss recovery and completion:
  - Sender retransmits timed-out windows in `transport/udp_sender.py:119-139`.
  - Sender retransmits `FIN` until `FIN_ACK` is received in `transport/udp_sender.py:141-156`.
  - Receiver discards corrupted packets, ignores wrong transfer IDs, re-ACKs duplicates, and ACKs in-order progress in `transport/udp_receiver.py:103-137`.
- Focused reliability tests:
  - ACK loss: `test/test_transport.py:201-218`
  - Duplicate data suppression: `test/test_transport.py:220-236`
  - Dropped data retransmit: `test/test_transport.py:238-252`
  - Out-of-order recovery: `test/test_transport.py:254-267`
  - FIN retransmit: `test/test_transport.py:269-283`
  - Sliding window pipeline: `test/test_transport.py:285-302`

## 2. General implementation rules from `docs.md`

| Requirement | Concrete implementation |
| --- | --- |
| Native low-level sockets only | The project uses Python `socket` directly in `server/server.py`, `server/session.py`, `client/ftp_client.py`, `transport/udp_sender.py`, and `transport/udp_receiver.py`. No FTP framework, QUIC, KCP, or transfer library is imported anywhere. |
| Reliable UDP built from scratch | Custom codec in `common/packet.py`, sender in `transport/udp_sender.py`, receiver in `transport/udp_receiver.py`, checksums in `common/checksum.py`. |
| CLI must report commands, network states, transfer progress | Interactive CLI in `client/command_handler.py:40-213`; live control-channel trace in `client/ftp_client.py:369-394`; upload/download progress bars in `transport/udp_sender.py:35-45` and `transport/udp_receiver.py:31-45`. |
| Configuration must be centralized | `ServerConfig` and `ClientConfig` in `common/config.py:9-27`. |

## 3. Approved FTP commands

The command dispatch table is built in `server/session.py:147-177`. Every approved command in `docs.md` is present there.

| Command | Server handler | Client/API entry | Main implementation details | Main tests |
| --- | --- | --- | --- | --- |
| `USER` | `server/session.py:200-212` | `client/ftp_client.py:93-99` | Saves `_pending_username`, moves session to `USERNAME_GIVEN`, returns `331 Password required`. Username existence is checked in `server/auth.py:11-16`. | `test/test_server.py:99-113`, `136-139` |
| `PASS` | `server/session.py:213-225` | `client/ftp_client.py:93-99` | Only valid after `USER`; `verify()` checks the hard-coded credential table in `server/auth.py:5-16`. Success returns `230`; failure returns `530`; PASS-before-USER returns `503`. | `test/test_server.py:99-128`, `136-139` |
| `QUIT` | `server/session.py:227-228` | `client/ftp_client.py:71-79` | Sends `221 Goodbye`; the dispatcher stops the session loop because `_dispatch()` returns `False` for `QUIT`. | `test/test_server.py:131-133` |
| `NOOP` | `server/session.py:230-231` | `client/ftp_client.py:180-181` | Always returns `200 OK`; also allowed before login because `NOOP` is in `_PREAUTH_COMMANDS` in `server/session.py:38`. | `test/test_server.py:121-123` |
| `PWD` | `server/session.py:237-238` | `client/ftp_client.py:105-112` | Converts current real directory back to FTP virtual path using `FileManager.to_virtual()` in `server/file_manager.py:38-47`; returns `257`. | `test/test_server.py:149-155` |
| `CWD` | `server/session.py:240-250` | `client/ftp_client.py:114-117` | Resolves client path through `FileManager.change_dir()` and `FileManager.resolve()` in `server/file_manager.py:27-36`, `98-102`; blocks traversal outside storage root. | `test/test_server.py:157-163`, `183-193` |
| `CDUP` | `server/session.py:252-254` | `client/ftp_client.py:119-122` | Builds parent virtual path from `_cwd.parent`, then internally reuses `_cmd_cwd()`. | `test/test_server.py:166-174` |
| `MKD` | `server/session.py:256-266` | `client/ftp_client.py:124-127` | Resolves virtual path, calls `FileManager.make_dir()` in `server/file_manager.py:92-93`, replies `257`. | `test/test_server.py:157-163`, `176-180` |
| `RMD` | `server/session.py:268-278` | `client/ftp_client.py:129-132` | Resolves target and calls `FileManager.remove_dir()` in `server/file_manager.py:95-96`; returns `250` on success. | `test/test_server.py:176-180` |
| `LIST` | `server/session.py:280-299` | `client/ftp_client.py:134-136`, `457-476` | Resolves target path, opens a TCP data socket through `_open_data_connection()`, sends `150`, streams `FileManager.list_dir()` output, then sends `226`. | `test/test_server.py:268-292` |
| `NLST` | `server/session.py:301-320` | `client/ftp_client.py:138-140`, `457-476` | Same data-connection pattern as `LIST`, but sends filename-only output from `FileManager.nlst_dir()` in `server/file_manager.py:88-90`. | `test/test_server.py:294-306` |
| `STAT` | `server/session.py:322-333` | `client/ftp_client.py:167-169` | Without argument returns server/session state using `211`; with a path it returns file metadata using `213`. | Used directly through client API and `defense_demo/raw_demo.py:90-97` |
| `SIZE` | `server/session.py:339-347` | `client/ftp_client.py:146-150` | Uses `FileManager.file_size()` in `server/file_manager.py:108-109`; returns `213 <size>`. | `test/test_server.py:319-326` |
| `MDTM` | `server/session.py:349-357` | `client/ftp_client.py:152-156` | Uses `FileManager.file_mdtm()` in `server/file_manager.py:111-113`; returns 14-digit timestamp `YYYYMMDDHHMMSS`. | `test/test_server.py:328-338` |
| `TYPE` | `server/session.py:374-387` | `client/ftp_client.py:175-178`, CLI in `client/command_handler.py:177-183` | Stores transfer type in session state as `TransferType.ASCII` or `TransferType.BINARY`. It affects the reported mode, but actual file reads/writes remain binary-safe. Invalid values return `501`. | `test/test_server.py:208-223` |
| `MODE` | `server/session.py:388-392` | raw command via `defense_demo/raw_demo.py:80-87` | Only `MODE S` is accepted and returns `200`; `MODE B` and `MODE C` return `502`. This matches the project scope: Stream mode implemented, block/compressed not implemented. | `test/test_server.py:226-229` |
| `PORT` | `server/session.py:394-411` | `client/ftp_client.py:417-437` | Server parses the `h1,h2,h3,h4,p1,p2` tuple, stores `_active_host`, `_active_port`, sets `DataMode.ACTIVE`, and later uses it in `_open_data_connection()`. Client active mode advertises its listener with `_open_active_listener()`. | `test/test_server.py:239-248`; active transfer test `test/test_transfer.py:298-307` |
| `PASV` | `server/session.py:413-424` | `client/ftp_client.py:405-415` | Server opens a temporary listening TCP socket, returns `227 Entering Passive Mode (...)`, client parses host/port and connects to it. Used for `LIST`, `NLST`, `STOR`, `RETR`, `STOU`, `APPE`, and ABOR demo helpers. | `test/test_server.py:232-236`; many transfer tests in `test/test_transfer.py` |
| `RETR` | `server/session.py:430-460` | `client/ftp_client.py:242-287`; active mode in `324-364` | Server verifies the file, opens TCP data connection plus UDP socket, allocates transfer ID, sends `150` containing `port=<udp_port> tid=<id>`, learns the client's UDP port via the TCP data socket, then calls `_send_file()` which uses `UDPSender`. Client binds its UDP receiver socket, sends its UDP port over the TCP data channel, receives the file with `UDPReceiver`, then validates the server SHA-256 digest. | `test/test_transfer.py:135-176`, `183-211`, `298-307`, `352-362` |
| `STOR` | `server/session.py:462-471`, `_do_receive()` in `602-617` | `client/ftp_client.py:208-240`; active mode in `290-323` | Server resolves destination path, opens TCP data connection plus UDP socket, sends `150` with UDP port and transfer ID, then calls `_receive_file()` which writes to a temporary file and only publishes the final file on success. Client uses `UDPSender` to push packets and verifies the returned SHA-256 digest. | `test/test_transfer.py:85-126`, `183-211`, `298-307`, `352-362` |
| `STOU` | `server/session.py:473-477` | direct raw flow in `defense_demo/raw_demo.py:100-137` | Server chooses a unique name with `FileManager.unique_path()` in `server/file_manager.py:138-148`, then reuses `_do_receive()`. The helper script compares directory contents before and after upload to show the generated name. | `test/test_transfer.py:218-252` |
| `APPE` | `server/session.py:479-488`, append branch in `_receive_file()` at `670-673` | direct raw flow in `defense_demo/raw_demo.py:140-172` | Server receives the appended bytes into a temporary file first, then opens the target file in append-binary mode and copies the new bytes to the end. If the file does not exist, opening with `ab` creates it. | `test/test_transfer.py:259-293` |
| `DELE` | `server/session.py:494-504` | `client/ftp_client.py:187-190`; CLI in `client/command_handler.py:142-148` | Resolves target path and deletes it with `FileManager.delete_file()` in `server/file_manager.py:122-123`; returns `250`. | `test/test_server.py:349-360` |
| `RNFR` | `server/session.py:506-518` | `client/ftp_client.py:192-198` | Resolves and validates the source path, stores it in `_rnfr_path`, returns `350 Ready for RNTO`. | `test/test_server.py:363-368` |
| `RNTO` | `server/session.py:520-535` | `client/ftp_client.py:192-198` | Requires a pending `_rnfr_path`; resolves the destination path, renames with `FileManager.rename()` in `server/file_manager.py:125-126`, then clears rename state. | `test/test_server.py:363-377` |
| `HASH` | `server/session.py:359-368` | `client/ftp_client.py:158-165`; CLI in `client/command_handler.py:168-173` | Uses `FileManager.file_hash()` in `server/file_manager.py:115-116`, which calls `sha256_file()` in `common/checksum.py:16-23`; returns `213 SHA-256 <digest> <filename>`. | `test/test_server.py:340-347`; digest checks in `test/test_transfer.py:91-98`, `142-148` |
| `ABOR` | `server/session.py:537-541`, cancellation internals in `735-747` | raw helper in `defense_demo/raw_demo.py:175-200` | `ABOR` sets the active transfer cancel event, closes tracked transfer sockets, and causes sender/receiver loops to raise `TransferError("transfer cancelled")`. Uploads are protected by temporary files in `_receive_file()` so partial files are deleted in the `finally` block. | `test/test_transfer.py:309-319` |
| `HELP` | `server/session.py:543-545` | `client/ftp_client.py:200-202`; raw helper in `defense_demo/raw_demo.py:71-77` | Server builds a sorted command list from `_handlers` and returns a multi-line `214` reply through `_send_multiline()`. | `test/test_server.py:379-383` |

## 4. Filesystem and directory sandboxing

The most important defense point for directory and file commands is that FTP paths are treated as virtual protocol paths, not direct OS paths.

- `FileManager.resolve()` in `server/file_manager.py:27-36`
  - Normalizes the user-supplied FTP path.
  - Joins it under `storage_root`.
  - Calls `resolved.relative_to(self._root)` to guarantee the final real path stays inside the storage sandbox.
- `FileManager._virtual_parts()` in `server/file_manager.py:48-70`
  - Converts backslashes to `/`.
  - Handles absolute versus relative FTP paths.
  - Rejects `..` that would climb above the FTP root.
- `FileManager.to_virtual()` in `server/file_manager.py:38-47`
  - Converts a real storage path back into an FTP-visible path like `/defense-room/file.txt`.

This is why traversal such as `CWD ../../etc` is rejected with `550`, and that behavior is tested in `test/test_server.py:189-193`.

## 5. Data connection modes

### 5.1 Passive mode

- Server side: `server/session.py:413-424`, `551-572`
- Client side: `client/ftp_client.py:405-415`
- Runtime flow:
  1. Client sends `PASV`.
  2. Server opens a temporary TCP listener and returns `227` with host and port.
  3. Client connects to that TCP listener.
  4. The TCP data socket is used only for directory listings or UDP-port negotiation.
  5. Actual file bytes still move over UDP.

### 5.2 Active mode

- Client side: `client/ftp_client.py:417-445`
- Server side: `server/session.py:394-411`, `551-560`
- Runtime flow:
  1. Client opens a local TCP listener.
  2. Client sends `PORT h1,h2,h3,h4,p1,p2`.
  3. Server stores the client endpoint and later connects back to it.
  4. That TCP socket again carries only listing data or UDP-port negotiation.
  5. File payload still uses UDP sender/receiver objects.

Active-mode upload and download are tested in `test/test_transfer.py:298-307`.

## 6. UDP transfer algorithm details

### 6.1 Sender logic

- Implemented in `transport/udp_sender.py:90-139`.
- The sender:
  - Reads the file in `MAX_UDP_PAYLOAD` chunks.
  - Wraps each chunk into `UDPPacket(PacketFlag.DATA, ...)`.
  - Sends up to `window_size` unacknowledged packets.
  - Waits for cumulative ACKs.
  - Retransmits the active window if no ACK progress arrives before timeout.
  - Sends `FIN` after the last data packet is cumulatively acknowledged.
  - Waits for `FIN_ACK` in `transport/udp_sender.py:141-156`.
  - Returns the local SHA-256 digest so the caller can compare it against the server reply.

### 6.2 Receiver logic

- Implemented in `transport/udp_receiver.py:85-143`.
- The receiver:
  - Waits on a bound UDP socket.
  - Decodes packets with `UDPPacket.from_bytes()`.
  - Ignores corrupt packets and packets for another transfer ID.
  - Accepts only the next expected sequence number.
  - Writes in-order payloads directly to file.
  - Sends cumulative ACK = next expected sequence number.
  - Re-sends the same ACK when a duplicate or out-of-order packet arrives.
  - Sends `FIN_ACK` when a `FIN` packet arrives.
  - Returns the SHA-256 of the assembled file.

### 6.3 Why the implementation is safe

- Packet corruption is rejected before use: `common/packet.py:73-91`.
- Transfer IDs isolate simultaneous transfers: `common/packet.py:34-39`, `transport/udp_sender.py:173-181`, `transport/udp_receiver.py:108-109`.
- Uploads are crash-safe against partial publication because `_receive_file()` first writes to a temporary file and only replaces/appends the real target after successful completion: `server/session.py:658-687`.
- `ABOR` cannot leave a partial upload published because unfinished temp files are deleted in the `finally` block of `_receive_file()`: `server/session.py:681-687`.

## 7. Standard reply codes from `docs.md`

| Reply code | Where it is implemented | How it is used in this project |
| --- | --- | --- |
| `125` | Enumerated in `common/protocol.py:17`; accepted by list client in `client/ftp_client.py:461` | Reserved for already-open data connections. Current list client accepts either `125` or `150`, but the server currently emits `150` for listings/transfers. |
| `150` | `server/session.py:293`, `314`, `446-447`, `610-611` | Sent before directory data transfer or before starting the UDP payload channel. For file transfer it includes `port=<udp_port> tid=<id>`. |
| `200` | `common/protocol.py:14`; used throughout `server/session.py:230-231`, `381-384`, `390`, `411` | Returned for `NOOP`, `TYPE`, `MODE S`, `PORT`. |
| `220` | `common/protocol.py:12`; sent in `server/session.py:82` | Initial greeting when a TCP control connection is established. |
| `221` | `common/protocol.py:13`; sent in `server/session.py:227-228` | Session termination reply for `QUIT`. |
| `226` | `common/protocol.py:19`; sent in `server/session.py:299`, `320`, `642`, `677`, `541` | Completion of directory transfer, file transfer, or a no-op `ABOR` when no transfer exists. |
| `230` | `common/protocol.py:15`; sent in `server/session.py:218-221` | Successful login after correct `USER` + `PASS`. |
| `250` | `common/protocol.py:16`; sent in `server/session.py:250`, `278`, `504`, `535` | Successful `CWD`, `RMD`, `DELE`, `RNTO`. |
| `331` | `common/protocol.py:20`; sent in `server/session.py:207-211` | Password required after `USER`. |
| `350` | `common/protocol.py:21`; sent in `server/session.py:517-518` | `RNFR` accepted, waiting for `RNTO`. |
| `421` | Enumerated in `common/protocol.py:22` | Defined for standards completeness; current server shutdown path closes sockets instead of explicitly replying `421`. |
| `425` | `common/protocol.py:23`; sent in `server/session.py:559`, `568`, `571` | Data connection could not be opened or no `PORT`/`PASV` was selected. |
| `426` | `common/protocol.py:24`; sent in `server/session.py:539`, `645`, `680` | Transfer aborted or failed, including `ABOR` and transfer exceptions. |
| `450` | `common/protocol.py:25`; sent in `server/session.py:189`, `715` | Transient file/action failure, especially when another transfer is already active in the same session. |
| `500` | `common/protocol.py:26`; sent in `server/session.py:90-92`, `107-109` | Syntax errors from malformed commands or overlong command lines. |
| `501` | `common/protocol.py:27`; used throughout parameter validation in `server/session.py` | Missing or invalid parameters, for example invalid `TYPE`, bad `PORT`, missing filename, or missing path. |
| `502` | `common/protocol.py:28`; sent in `server/session.py:183`, `392` | Unknown command or unsupported `MODE` other than `S`. |
| `530` | `common/protocol.py:29`; sent in `server/session.py:186`, `225` | Login required or login failed. |
| `550` | `common/protocol.py:30`; used throughout `server/session.py` around file/path operations | Missing file, invalid path, traversal attempt, or other file-unavailable condition. |
| `211` | literal in `server/session.py:333` | General `STAT` reply without a path argument. |
| `213` | literal in `server/session.py:330`, `345`, `355`, `366` | `STAT <path>`, `SIZE`, `MDTM`, `HASH`. |
| `214` | literal in `server/session.py:545` | Multi-line `HELP` reply. |
| `227` | literal in `server/session.py:424` | Passive-mode endpoint advertisement. |
| `257` | literal in `server/session.py:238`, `266` | `PWD` and `MKD`. |
| `503` | literal in `server/session.py:215`, `522` | Bad command sequence: `PASS` before `USER`, or `RNTO` before `RNFR`. |

## 8. Concurrency and session isolation

- One client connection maps to one `ClientSession`: `server/server.py:58-61`.
- One OS thread is created per client connection: `server/server.py:49-56`.
- Session-local state is stored inside the `ClientSession` object: `server/session.py:54-73`.
  - auth state
  - current working directory
  - transfer type
  - active/passive data mode
  - rename source state
  - transfer thread, cancel event, transfer sockets, transfer ID counter
- The isolation property is validated by `test/test_server.py:393-403`, where one client creates a directory and the other client still reports its own independent `PWD` state.

## 9. Client CLI and demo helpers

### 9.1 Interactive CLI

- Entry point: `client/main.py:1-11`
- REPL command dispatcher: `client/command_handler.py:48-213`
- Important defense points:
  - `connect` creates `FTPClient(trace_control=True)` so the professor can see the raw TCP conversation.
  - `put` / `get` use passive mode helpers by default.
  - `put-active` / `get-active` explicitly demonstrate active mode.
  - Uploaded local files are resolved under `client/upload/`; downloaded files are stored under `client/download/`.

### 9.2 Raw defense helper

- File: `defense_demo/raw_demo.py:1-231`
- Purpose: expose approved FTP commands that are implemented in the server but not given a dedicated REPL command in the main CLI.
- Subcommands:
  - `help`: `defense_demo/raw_demo.py:71-77`
  - `mode`: `80-87`
  - `stat`: `90-97`
  - `stou`: `100-137`
  - `appe`: `140-172`
  - `abor`: `175-200`

## 10. Technical report requirement mapping

The assignment's section 2.4 asks for report content, not runtime commands. The repository already contains most technical material, but some items still require student-authored explanation in the final report.

| Report requirement from `docs.md` | Current repo evidence |
| --- | --- |
| Application scenario and protocol interaction | `docs/01-architecture.md`, `report/main.tex`, and the control/data workflow visible in `server/session.py` plus `client/ftp_client.py`. |
| Project-wide data structures | `common/protocol.py`, `common/packet.py`, `common/config.py`, `server/session.py`. |
| Functional workflows / flowcharts | Logic exists in code, especially `server/session.py`, `transport/udp_sender.py`, `transport/udp_receiver.py`. If the professor asks for an actual flowchart image, that must be in the report, not just in source. |
| Task assignment matrix | `docs.md` contains a partial matrix, but member names and exact ownership should be finalized by the students. |
| Self-assessment and peer evaluation | Not generated by code; must be filled by the students. |
| GenAI usage and code refinement log | `docs/04-ai-prompts.md` and `docs.md` already contain GenAI provenance material. |
| Demo evidence | `docs/07-demo-evidence.md` plus `defense_demo/README.md` and `defense_demo/raw_demo.py`. |

## 11. Fast oral-defense summary

If the professor asks for a short explanation, the most defensible answer is:

1. TCP is used only for FTP control commands and replies. That logic is in `server/server.py`, `server/session.py`, `client/ftp_client.py`, and `common/protocol.py`.
2. UDP is used only for file payload. The packet format is in `common/packet.py`; the reliability algorithm is in `transport/udp_sender.py` and `transport/udp_receiver.py`.
3. The server never trusts client paths directly. `server/file_manager.py` normalizes FTP virtual paths and prevents escaping the storage root.
4. Every approved FTP command is wired in `ClientSession._build_dispatch()` in `server/session.py:147-177`.
5. Passive and active mode only choose how the temporary TCP data socket is established. The actual file data is still sent over reliable UDP.
6. Integrity is checked twice: CRC-32 per UDP packet and SHA-256 per completed file.
7. The implementation is backed by real tests in `test/test_server.py`, `test/test_transfer.py`, and `test/test_transport.py`.
