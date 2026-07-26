# Internetworking Protocol

# Project 1: Design and Implementation of the Hybrid FTP Application

| Item | Description |
|--------|-------------|
| Course Name | Internetworking Protocol |
| Project Title | Design and Implementation of the Hybrid FTP |
| Project Type | Group Project (2 members/group) |
| Programming Language | C/C++, Java, Python, C#, or any widely-adopted systems language |
| Deliverables | Source Code + Technical Report + Live Oral Defense |
| Report Format | Structured Technical Documentation |

---

# 1. Project Description

This project challenges students to design and implement a Hybrid FTP (File Transfer Protocol) system that decouples the control plane from the data plane — mirroring the architectural philosophy of the real-world FTP standard (RFC 959).

Students will build a fully functional client-server application with two independent communication channels.

## 1.1 Control Channel — TCP

The control channel leverages TCP sockets to transmit commands, responses, and session state.

TCP's connection-oriented, reliable delivery guarantees:

- Sequential command execution
- Stable session tracking
- Accurate status reporting throughout the client's lifecycle

## 1.2 Data Channel — UDP

All actual file payload is transmitted over UDP sockets.

Since UDP is inherently unreliable, students must research and engineer a custom application-layer reliability sub-protocol built directly on top of UDP (without external libraries) to provide:

- Zero packet loss
- Corruption detection
- Duplicate elimination
- Correct packet ordering

## 1.3 Evaluation Levels

### Basic Level

- Authentication mechanism: Basic user identification and access verification
- Data type & transmission mode: ASCII text file handling
- File operations: Upload and download of a single file
- Operating mode: Single, fixed data-channel connection mechanism

### Advanced Level

- Binary file handling (images, videos, archives) without corruption
- Directory navigation and tree support
- Traverse, list, and manage nested folder structures
- Active / Passive mode switching or automation
- Multi-threaded or multi-process server with isolated client sessions

### Excellent Level

- Custom Reliable UDP Layer (RDT)
  - ACKs
  - Sequence numbers
  - Timeout / Retransmit
  - Stop-and-Wait, Go-Back-N, or Selective Repeat

- Congestion / Flow Control
  - Sliding Window or equivalent mechanism

- Data Integrity Verification
  - MD5 or SHA-256 comparison before and after transfer

---

# 2. Requirements

## 2.1 General Implementation Rules

- Language: C/C++, Java, Python, C#, or equivalent
- Only native low-level socket APIs bundled with the language runtime are permitted
- No pre-built FTP frameworks or third-party transfer libraries
  - KCP
  - QUIC
  - libcurl FTP wrappers
  - etc.

- The reliable UDP layer must be implemented from scratch
- A CLI or GUI must report:
  - Network states
  - Commands issued
  - Transfer progress

---

## 2.2 Approved FTP Commands

| Command | Syntax | Description |
|----------|----------|-------------|
| USER | USER \<username> | Initiate authentication session |
| PASS | PASS \<password> | Complete authentication |
| QUIT | QUIT | End session |
| NOOP | NOOP | Keep-alive ping |
| PWD | PWD | Print working directory |
| CWD | CWD \<path> | Change directory |
| CDUP | CDUP | Move to parent directory |
| MKD | MKD \<dirname> | Create directory |
| RMD | RMD \<dirname> | Remove empty directory |
| LIST | LIST [path] | Detailed directory listing |
| NLST | NLST [path] | Filename-only listing |
| STAT | STAT [path] | Server status or metadata |
| SIZE | SIZE \<filename> | File size |
| MDTM | MDTM \<filename> | Last modification time |
| TYPE | TYPE {A \| I} | ASCII or Binary transfer |
| MODE | MODE {S \| B \| C} | Stream / Block / Compressed |
| PORT | PORT \<h1,h2,h3,h4,p1,p2> | Active Mode |
| PASV | PASV | Passive Mode |
| RETR | RETR \<filename> | Download file |
| STOR | STOR \<filename> | Upload file |
| STOU | STOU | Upload with unique filename |
| APPE | APPE \<filename> | Append data to file |
| DELE | DELE \<filename> | Delete file |
| RNFR | RNFR \<oldname> | Rename From |
| RNTO | RNTO \<newname> | Rename To |
| HASH | HASH \<filename> | Return MD5/SHA256 hash |
| ABOR | ABOR | Abort current transfer |
| HELP | HELP [command] | Help information |

---

## 2.3 Standard Server Reply Codes

### 1xx — Positive Preliminary Reply

- 125 Data connection already open
- 150 File status okay, opening data connection

### 2xx — Positive Completion Reply

- 200 Command OK
- 220 Service ready
- 221 Goodbye
- 226 Transfer complete
- 230 Login successful
- 250 Requested file action OK

### 3xx — Positive Intermediate Reply

- 331 Username OK, need password
- 350 Requested file action pending RNTO

### 4xx — Transient Negative Reply

- 421 Service unavailable
- 425 Can't open data connection
- 426 Connection closed; transfer aborted
- 450 File unavailable

### 5xx — Permanent Negative Reply

- 500 Syntax error
- 501 Syntax error in parameters
- 502 Command not implemented
- 530 Not logged in
- 550 File unavailable

---

## 2.4 Technical Report Requirements

The report must contain:

### 1. Application Scenario & Protocol Interaction

- Sequence diagram of full TCP + UDP lifecycle

### 2. Project-Wide Data Structures

- TCP control packet format
- UDP custom header fields
  - Sequence Number
  - ACK
  - Checksum
  - Flags
  - Payload Length

- Session management structures

### 3. Functional Workflows (Flowcharts)

- Server thread dispatch logic
- Reliable UDP sender state machine
- Reliable UDP receiver state machine
- Active/Passive mode switching

### 4. Task Assignment Matrix

- Module owner
- Collaborators
- Responsibilities

### 5. Self-Assessment & Peer Evaluation

- Individual evaluation
- Contribution percentage
- Total = 100%

### 6. GenAI Usage & Code Refinement Log (Mandatory)

Include:

- Exact prompts
- Raw AI outputs
- Refinement process
- Critical analysis

### 7. Application Demo Evidence

- Upload screenshots
- Download screenshots
- Hash verification logs
- Connected client table
- Concurrent session testing

---

# 3. Grading Rubric

## Code Quality & Application Demo (40%)

### Unsatisfactory

- Fails to compile
- Crashes
- Cannot transfer files
- Uses banned FTP libraries

### Satisfactory

- Transfers ASCII files
- Single operating mode
- Single-threaded server

### Good / Very Good

- Stable binary transfers
- Multi-threaded concurrent server
- Directory tree operations

### Excellent

- Reliable UDP with ACK + timeout recovery
- Congestion control
- End-to-end hash verification

---

## Theoretical Understanding (30%)

### Unsatisfactory

- Cannot distinguish TCP and UDP
- Does not understand control/data split
- Cannot explain socket calls

### Satisfactory

- Explains socket workflow
- Explains TCP handshake
- Understands hybrid design rationale

### Good / Very Good

- Explains Active/Passive mode
- Explains concurrency model
- Explains every field in UDP header

### Excellent

- Masters Stop-and-Wait
- Masters Go-Back-N
- Masters Selective Repeat
- Can mathematically justify bandwidth optimization

---

## Live Coding & Debugging (20%)

### Unsatisfactory

- Cannot locate requested code
- Cannot fix logical errors

### Satisfactory

- Locates modules quickly
- Adjusts simple parameters

### Good / Very Good

- Finds injected bugs
- Modifies logic safely

### Excellent

- Rewrites code live
- Handles arbitrary network constraints
- Handles edge-case scenarios

---

## Technical Documentation & GenAI Provenance (10%)

### Unsatisfactory

- Plagiarized report
- Missing diagrams
- Missing flowcharts
- Missing GenAI appendix

### Satisfactory

- All mandatory sections present
- GenAI appendix only copies prompts

### Good / Very Good

- Professional organization
- Diagrams reflect implementation
- Clear distinction between AI output and student changes

### Excellent

- Industry-grade documentation
- Packet header breakdown at bit/byte level
- Deep auditing of AI-generated output

---

# 4. Critical Evaluation Directives

## 4.1 Individual Grading Differentiation

Grades are not distributed equally.

Evaluation considers:

1. Task Assignment Matrix
2. Peer Evaluation
3. Individual Viva Questions

Students unable to explain their assigned module will receive lower individual scores.

---

## 4.2 Zero-Tolerance Policy for Unverifiable Code

Use of AI tools is allowed:

- ChatGPT
- Gemini
- Claude
- GitHub Copilot
- etc.

However:

Students must fully understand and explain:

- Logic
- Runtime behavior
- Data structures

Failure to explain AI-generated code results in:

- 0 for Theoretical Understanding
- 0 for Live Coding

---

## 4.3 GenAI Documentation Requirements

Must document:

### Prompts Used

Exact prompts submitted to AI.

### Raw GenAI Output

Unedited AI responses.

### Refinement & Problem Solving

Analysis of:

- Errors
- Limitations
- Banned libraries
- Debugging performed
- Refactoring performed
- Optimizations performed

---

## 4.4 Academic Integrity Policy

- Copying another group's code is plagiarism
- Entire group receives zero

All code must be version controlled.

Examples:

- Git

Examiners may request:

- Commit history
- Authorship evidence

Third-party code must be:

- Cited
- Explained

Undisclosed use is academic dishonesty.

---

## 4.5 Demo & Submission Checklist

Before Oral Defense:

- [ ] Source code compiles on a clean machine
- [ ] Successful upload demonstrated
- [ ] Successful download demonstrated
- [ ] Server log shows:
  - Client IPs
  - Executed commands
  - Active session table

- [ ] Technical report includes all seven mandatory sections
- [ ] GenAI appendix completed honestly
- [ ] Contribution percentages declared
- [ ] Screenshots and hash logs embedded in report

---

# End of Project Specification

---

# Hybrid FTP Project Development Log

## 1. Project Overview

This log is the official project tracking file from 2026-07-25 onward. Older content above is preserved as the assignment specification. Current implementation is a Python 3.10+ Hybrid FTP application: TCP control channel, UDP data payload channel, and a custom Stop-and-Wait reliable UDP layer.

## 2. Assignment Requirements Summary

- TCP must carry commands, replies, authentication, and session state.
- UDP must carry actual file bytes.
- UDP reliability must be implemented at application layer without third-party transfer libraries.
- Required FTP commands include authentication, directory, metadata, transfer, file management, active/passive setup, and help commands.
- The project must demonstrate at least one upload and one download with integrity evidence.
- Documentation must honestly record audit evidence, tests, GenAI usage, limitations, and oral-defense notes.

## 3. Architecture Summary

- `server/server.py`: TCP bind/listen/accept loop and per-client threads.
- `server/session.py`: per-client state machine, command dispatch, active/passive data setup, and UDP transfer coordination.
- `transport/udp_sender.py`: Stop-and-Wait sender using sequence numbers, ACKs, timeout, retries, FIN/FIN_ACK, and CRC-32 packet checks.
- `transport/udp_receiver.py`: Stop-and-Wait receiver using transfer ID filtering, in-order writes, duplicate ACKing, and SHA-256 file digest.
- `common/packet.py`: 22-byte UDP packet header in network byte order.
- `client/ftp_client.py`: TCP client plus PASV/UDP coordination for upload/download.

## 4. Current Repository Structure

```text
client/
common/
docs/
server/
test/
test_files/
transport/
README.md
docs.md
Project1_SocketProgramming_2026.pdf
```

No `doc.md` was found during the 2026-07-25 audit. `Project1_SocketProgramming_2026.pdf` is present but untracked in Git.

## 5. Build and Run Instructions

- Python detected during audit: `Python 3.13.9`.
- Server entry point: `python server/main.py` or `python -m server.main`.
- Client entry point: `python client/main.py` or `python -m client.main`.
- Test command: `python -m unittest discover -s test -v`.
- Default host/ports: TCP control `127.0.0.1:2121`; UDP transfer sockets are currently allocated dynamically per transfer, while `ServerConfig.udp_port=2122` is defined but not used by current transfer code.
- Dependencies: standard library only.

## 6. Requirement Audit Matrix

| ID | Requirement | Relevant Files | Current Status | Evidence | Problems | Next Action | Owner |
|----|-------------|----------------|----------------|----------|----------|-------------|-------|
| A1 | Client entry point and CLI | `client/main.py`, `client/command_handler.py` | UNVERIFIED | Code read; CLI exposes connect/login/list/put/get/etc. | Interactive CLI not manually demoed yet. | Demo after Priority 0 fix. | Agent-assisted under student review |
| A2 | Server entry point and clean startup | `server/main.py`, `server/server.py` | PARTIAL | Tests start server threads and receive 220 replies. | Some tests hang until timeout after path-resolution failures. | Fix path handling, rerun tests. | Agent-assisted under student review |
| A3 | Configuration | `common/config.py` | PARTIAL | Host/control port/storage root config exists. | `udp_port` default is unused; CLI has limited command-line args. | Document or remove unused config later. | Agent-assisted under student review |
| B1 | TCP control channel | `server/server.py`, `server/session.py`, `client/ftp_client.py`, `common/protocol.py` | PARTIAL | socket/bind/listen/accept/connect/sendall/recv paths read; tests validate greeting/auth/basic replies. | Runtime failures in path commands prevent full command workflow. | Fix path handling, rerun full tests. | Agent-assisted under student review |
| B2 | TCP command framing and parsing | `common/protocol.py`, `server/session.py`, `client/ftp_client.py` | DONE | CRLF framing, byte-by-byte server readline, buffered client readline, tests cover parser and replies. | No stress test for many pipelined commands yet. | Add later if time. | Agent-assisted under student review |
| C1 | Authentication | `server/auth.py`, `server/session.py`, `test/test_server.py` | DONE | Tests passed before path failures: USER/PASS success, wrong password, unknown user, PASS-before-USER, anonymous login. | Credentials are hard-coded demo accounts; acceptable for class demo but not production. | Document oral-defense limitation. | Agent-assisted under student review |
| D1 | Basic FTP commands USER/PASS/QUIT/NOOP/TYPE | `server/session.py`, `client/ftp_client.py`, tests | DONE | Tests pass for auth, NOOP, TYPE A/I, invalid TYPE, QUIT. | `MODE` client wrapper is missing though raw server supports it. | Add wrapper only if needed for demo. | Agent-assisted under student review |
| D2 | RETR/STOR | `server/session.py`, `client/ftp_client.py`, `transport/*`, `test/test_transfer.py` | BROKEN | Full test run fails all upload/download paths with `550 path escapes storage root`. | Windows virtual path bug blocks transfer setup before UDP starts. | Priority 0: fix `FileManager.resolve()` cross-platform virtual path handling. | Agent-assisted under student review |
| E1 | Directory commands | `server/session.py`, `server/file_manager.py`, `test/test_server.py` | BROKEN | MKD/PWD/LIST/NLST fail on Windows with path escaping root. | `Path("/")` becomes `\` on Windows; `str(cwd).lstrip("/")` is wrong. | Priority 0 path fix. | Agent-assisted under student review |
| F1 | File management commands | `server/session.py`, `server/file_manager.py`, tests | BROKEN | DELE/RNFR/RNTO/SIZE/MDTM/HASH fail on existing files because relative paths escape root. | Same Windows path bug. | Priority 0 path fix. | Agent-assisted under student review |
| G1 | FTP reply codes | `common/protocol.py`, `server/session.py` | PARTIAL | Standard codes are mostly implemented; extra codes 211/213/214/227/257/503 used. | Some error states use non-enum literals; correctness depends on tests after path fix. | Audit after tests pass. | Agent-assisted under student review |
| H1 | Active/passive modes | `server/session.py`, `client/ftp_client.py`, tests | PARTIAL | PASV and PORT raw commands pass setup tests. Client upload/download uses PASV only. | Active-mode file transfer not covered by client API/tests. | Document limitation; test PASV transfer first. | Agent-assisted under student review |
| I1 | Transfer types and modes | `server/session.py` | PARTIAL | TYPE A/I and MODE S implemented. MODE B/C return 502. | ASCII mode does not transform newlines; binary mode is effectively always binary-safe. | Document design choice. | Agent-assisted under student review |
| J1 | UDP data channel | `transport/*`, `server/session.py`, `client/ftp_client.py` | BROKEN | Packet code read; integration tests exist. | Runtime transfer blocked before UDP by FileManager bug. | Rerun after path fix. | Agent-assisted under student review |
| K1 | Custom reliable UDP | `common/packet.py`, `transport/*` | UNVERIFIED | Code includes sequence, ACK, timeout, retransmit, CRC-32, FIN/FIN_ACK, transfer ID. | No packet-loss/ACK-loss simulation tests yet in current suite. | Add/execute loss tests after baseline pass. | Agent-assisted under student review |
| L1 | Binary integrity/hash | `common/checksum.py`, `test/test_transfer.py` | BROKEN | Tests exist for binary upload/download and SHA-256. | Tests fail before transfer due path bug. | Rerun after path fix. | Agent-assisted under student review |
| M1 | Multi-client isolation | `server/server.py`, `server/session.py`, `test/test_server.py` | PARTIAL | Per-client thread/session state exists. | Concurrency test fails because MKD is broken. | Rerun after path fix. | Agent-assisted under student review |
| N1 | Documentation accuracy | `docs.md`, `docs/*.md`, `README.md` | PARTIAL | Existing docs read. | `docs/03-server.md` still says transfer commands are stubs; current code has real UDP integration. SUPERSEDED by this audit entry. | Update docs after code fix. | Agent-assisted under student review |

## 7. Project Status Summary

Initial audit on 2026-07-25 found that the repository has a mostly complete Python implementation, but the current runtime status on Windows is BROKEN for path-dependent commands. The highest priority issue is cross-platform virtual path resolution in `server/file_manager.py`.

SUPERSEDED: Older `docs/03-server.md` section "Transfer stubs (RETR/STOR/STOU/APPE)" is no longer accurate for current source code. Current `server/session.py` wires these commands to `UDPSender`/`UDPReceiver`, but they are blocked by the Windows path bug until fixed.

## 8. Prioritized Implementation Plan

| Priority | Task | Reason | Validation |
| --- | --- | --- | --- |
| P0 | Fix Windows-safe virtual path resolution in `FileManager.resolve()` and `to_virtual()` | Current tests fail before directory/file/UDP workflows can run. | `python -m unittest discover -s test -v` |
| P1 | Rerun full test suite and inspect remaining failures | Establish verified baseline. | Full test output in this file |
| P1 | Add or run packet-loss/ACK-loss reliability tests | Current suite verifies happy-path transfer but not reliability under loss. | Focused transport tests |
| P2 | Update stale docs and oral-defense notes | Docs currently contain stale transfer-stub statement. | Manual review |
| P2 | Manual demo upload/download with SHA-256 evidence | Required for project demo. | Demo log and hashes |

## 9. Work Log

### Work Entry 2026-07-25-01 - Initial audit and P0 path fix plan

- Agent: Codex GPT-5, agent-assisted under student review.
- Files inspected: `Project1_SocketProgramming_2026.pdf`, `docs.md`, `README.md`, `docs/*.md`, all Python files under `common/`, `server/`, `client/`, `transport/`, `test/`.
- Git state: branch `master`; `git status --short` showed only `?? Project1_SocketProgramming_2026.pdf`; `git diff --stat` was empty.
- Test run before fix: `python -m unittest discover -s test -v`.
- Result before fix: FAIL, 60 tests run, 10 failures, 24 errors. Main cause: `550 path escapes storage root` for relative paths on Windows.
- Planned files to change: `server/file_manager.py`.
- Planned logic: normalize FTP virtual paths with POSIX-style `/` semantics independent of Windows filesystem separators; ensure resolved real paths remain inside storage root using `Path.relative_to()` instead of string prefix matching.
- Why needed: Current `Path("/")` becomes `\` on Windows, so `root / "\\" / "file"` resolves outside `storage_root`.
- Oral-defense concept: FTP paths are protocol paths, not OS paths; server must translate virtual paths into real paths and prevent traversal.

### Work Entry 2026-07-25-02 - P1 reliable UDP focused tests plan

- Agent: Codex GPT-5, agent-assisted under student review.
- Files planned to change: `test/test_transport.py`, then `docs.md`.
- Logic planned: add unit tests that simulate ACK loss/retransmission at the sender and duplicate DATA packet handling at the receiver without using third-party libraries.
- Why needed: The existing integration tests prove happy-path upload/download and binary integrity, but they do not directly prove loss recovery behavior required by the assignment.
- Test to run after change: `python -m unittest discover -s test -v`.
- Expected result: full suite remains passing, with added focused reliability coverage.
- Oral-defense concept: Stop-and-Wait correctness depends on retransmitting when ACK is missing and not writing duplicate DATA payload twice.

## 10. Protocol Specification

### 10.1 TCP Control Protocol

Commands are UTF-8 text lines ending in CRLF. Server replies are FTP-style numeric replies ending in CRLF.

### 10.2 FTP Commands and Reply Codes

Current dispatch table supports USER, PASS, QUIT, NOOP, PWD, CWD, CDUP, MKD, RMD, LIST, NLST, STAT, SIZE, MDTM, HASH, TYPE, MODE, PORT, PASV, RETR, STOR, STOU, APPE, DELE, RNFR, RNTO, ABOR, HELP.

### 10.3 Session State Machine

Authentication states are `NOT_LOGGED_IN`, `USERNAME_GIVEN`, and `LOGGED_IN`. Data mode state is per session.

### 10.4 UDP Packet Format

Header is 22 bytes: magic 2, version 1, flags 1, transfer ID 4, sequence 4, acknowledgement 4, payload length 2, checksum 4. `struct` format is `!2sBBIIIHI`.

### 10.5 Reliable UDP Algorithm

Current implementation is Stop-and-Wait ARQ with per-packet ACK, timeout/retry, duplicate ACK handling, CRC-32 corruption rejection, and FIN/FIN_ACK completion.

### 10.6 Transfer Completion Mechanism

Sender transmits FIN after all DATA chunks. Receiver returns FIN_ACK. Control channel sends 226 only after the UDP sender/receiver completes.

### 10.7 Active and Passive Modes

Server supports PORT and PASV setup for TCP data coordination. Current client API uses PASV for list/upload/download.

## 11. Project-Wide Data Structures

- `ServerConfig`, `ClientConfig`
- `Command`, `ReplyCode`
- `UDPPacket`, `PacketFlag`
- `ClientSession` state fields: auth state, cwd, transfer type, data mode, active host/port, passive socket, rename source, abort event, transfer counter.

## 12. Test Plan

- Baseline: `python -m unittest discover -s test -v`.
- After P0: verify directory, file metadata, upload, download, round-trip, STOU, APPE, and concurrency tests.
- Later: add focused transport tests for dropped DATA, dropped ACK, duplicate DATA, corrupted packet, and FIN retransmission.

## 13. Test Results

### 2026-07-25 Baseline Before P0 Fix

- Command: `python -m unittest discover -s test -v`
- Preconditions: Windows workspace, Python 3.13.9, no code changes by Codex yet.
- Expected result: all tests pass.
- Actual result: 60 tests run; 10 failures; 24 errors.
- Result: FAIL.
- Evidence: repeated server replies `550 path escapes storage root: '<relative path>'` and `path escapes storage root: '\\'`.

## 14. Known Issues and Limitations

- P0: Windows path resolution is broken before the fix.
- Active-mode file transfer is not verified by current client/test flow.
- Packet-loss and ACK-loss recovery are implemented in code but not yet verified by dedicated loss-injection tests.
- Credentials are hard-coded demo values.
- Existing docs have mojibake/encoding artifacts and stale statements.

## 15. Task Assignment Matrix

| Module | Primary Owner | Collaborator | Status | Files | Oral Responsibility | Evidence |
|--------|---------------|--------------|--------|-------|---------------------|----------|
| Audit and P0 fix | Agent-assisted under student review | Shared | IN PROGRESS | `docs.md`, `server/file_manager.py` | Explain virtual path vs OS path and storage-root sandboxing | Baseline test failure |
| TCP server | Unassigned | Shared | PARTIAL | `server/*` | Explain bind/listen/accept, per-client thread, dispatch | Tests after P0 |
| Client CLI/API | Unassigned | Shared | UNVERIFIED | `client/*` | Explain connect, PASV, upload/download calls | Pending manual demo |
| Reliable UDP | Unassigned | Shared | UNVERIFIED | `transport/*`, `common/packet.py` | Explain sequence, ACK, timeout, checksum, FIN | Pending loss tests |

## 16. Git Commit Mapping

- Current recent commits inspected: `245d3d6 thuanlv/Add progress bar`, `1eb2470 thuanlv/add user`, `843a7ac thuanlv/Remove pycache files and fix gitignore`, `5c712c5 thuanlv/Add tcp server`, `6376648 thuanlv/Add common files`.
- No new commit created in this session yet.

## 17. Oral Defense Preparation

### Oral Defense Notes - FileManager Path Sandbox

1. Module purpose: map FTP virtual paths to real filesystem paths while preventing traversal outside storage root.
2. Main file: `server/file_manager.py`.
3. Key functions: `resolve()`, `to_virtual()`.
4. Security concept: never trust client path input; normalize and verify resolved path remains below server root.
5. Demo question: why is Windows different? `Path("/")` stringifies as `\`, so protocol paths must be handled separately from OS separators.

## 18. GenAI Usage and Refinement Log

### GenAI Entry 2026-07-25-01

- Date/Time: 2026-07-25 19:54 Asia/Bangkok.
- Tool/Model: Codex GPT-5.
- Exact prompt: User requested a full senior-engineer audit of the Hybrid FTP project, reading the assignment PDF, `docs.md`, source, tests, Git state, then updating `docs.md` before fixing missing/broken functionality.
- Raw output summary: Audit identified Python Hybrid FTP implementation with TCP control, UDP data, Stop-and-Wait RDT, and a Windows path-resolution blocker.
- Code suggested by AI: planned fix for `server/file_manager.py` virtual path normalization.
- Code actually accepted: pending at this log point.
- Code rejected: none yet.
- Errors or limitations found: stale docs, untracked PDF, failing tests, Windows path bug, missing packet-loss tests.
- Banned libraries detected: none; implementation uses Python standard library.
- Security concerns detected: path traversal prevention depends on correct `resolve()` implementation; current string-prefix check is fragile.
- Concurrency concerns detected: per-client session exists; concurrency test currently blocked by path bug.
- Protocol mismatch detected: docs still call transfer commands stubs, source currently wires UDP.
- Manual modifications: this audit log appended before code edits.
- Why the final solution is correct: pending after implementation and tests.
- Tests used to validate: baseline full unittest run failed and established P0 bug.
- Student concepts to understand: virtual path normalization, storage-root sandboxing, TCP control vs UDP data separation.
- Related files: `docs.md`, `server/file_manager.py`.
- Related commits: none yet.

## 19. Demo Evidence

Pending after P0 fix and successful upload/download verification.

## 20. Demo Checklist

- [ ] Project runs on clean or equivalent environment.
- [ ] Server start succeeds.
- [ ] Client connect succeeds.
- [ ] USER/PASS succeeds.
- [x] Login failure is handled.
- [x] NOOP works.
- [ ] PWD works.
- [ ] LIST works.
- [ ] Upload text file succeeds.
- [ ] Download text file succeeds.
- [ ] Upload binary file succeeds.
- [ ] Download binary file succeeds.
- [ ] SHA-256 before and after transfer match.
- [ ] Packet loss recovery is demoed.
- [ ] ACK loss recovery is tested.
- [ ] Directory operations are demoed.
- [ ] Active or Passive mode is demoed.
- [ ] Two clients connect concurrently.
- [ ] Active session table is displayed.
- [ ] Client disconnect does not crash server.
- [x] QUIT closes session correctly.
- [ ] Server shutdown cleanup is verified.
- [ ] Demo screenshots/logs are saved.
- [ ] Technical report has required sections.
- [ ] Task Assignment Matrix is complete.
- [ ] GenAI appendix is complete.
- [ ] Both members have read `docs.md`.
- [ ] Both members can explain assigned code.

## 21. Final Project Status

Current status after initial audit and before P0 code fix: BROKEN. The project has substantial implemented code, but Windows path handling currently prevents directory operations, file metadata commands, and UDP transfer workflows from passing tests.

### Status Update 2026-07-25 After P0/P1 Fixes

SUPERSEDED: The immediately preceding BROKEN status applied before the P0 fix. After the changes below, the tested baseline is PARTIAL/DONE depending on feature group, not BROKEN.

- Changed `server/file_manager.py`.
  - Function changed: `FileManager.resolve()`.
  - Function changed: `FileManager.to_virtual()`.
  - Function added: `FileManager._virtual_parts()`.
  - Reason: Windows converted FTP virtual cwd `/` into OS path `\`, causing relative paths to resolve outside `storage_root`.
  - New logic: normalize FTP paths as POSIX-style virtual segments first, reject `..` above virtual root, join segments into the real storage root, and validate containment with `Path.relative_to()`.
- Added `test/test_transport.py`.
  - Class added: `AckLossSocket`.
  - Class added: `DuplicateDataSocket`.
  - Tests added: sender retransmits when first DATA ACK is lost; receiver ACKs duplicate DATA without duplicate write.
  - Reason: integration tests covered happy-path UDP transfer but did not directly verify reliability behavior under ACK loss or duplicate DATA.

### Requirement Audit Status Update 2026-07-25

| ID | Requirement | Previous Status | New Status | Evidence | Remaining Problems |
|----|-------------|-----------------|------------|----------|--------------------|
| A2 | Server startup and command workflows | PARTIAL | DONE | Full unittest suite starts/stops many server instances and receives valid replies. | Manual CLI demo still useful. |
| B1 | TCP control channel | PARTIAL | DONE | Full suite passes auth, command replies, PASV/PORT setup, LIST/NLST, metadata, and error replies. | No dedicated pipelined-command stress test. |
| D2 | RETR/STOR | BROKEN | DONE | Upload/download and round-trip tests pass for text, binary, empty, exact-boundary, multi-packet, and large files. | Active-mode transfer path not covered by client tests. |
| E1 | Directory commands | BROKEN | DONE | MKD/CWD/CDUP/RMD/LIST/NLST/PWD tests pass; traversal is rejected. | Permission-error cases not deeply simulated. |
| F1 | File management commands | BROKEN | DONE | DELE/RNFR/RNTO/SIZE/MDTM/HASH/STOU/APPE tests pass. | ABOR is still shallow; no live transfer cancellation test. |
| J1 | UDP data channel | BROKEN | DONE | End-to-end UDP transfer tests pass for text, binary, empty, multi-packet, and round-trip workflows. | Active mode plus UDP transfer not tested. |
| K1 | Custom reliable UDP | UNVERIFIED | PARTIAL | Added focused tests for ACK loss retransmission and duplicate DATA elimination; existing packet checksum test covers corruption rejection. | No dedicated dropped-DATA-to-receiver test, out-of-order test, or FIN-loss test yet. |
| L1 | Binary integrity/hash | BROKEN | DONE | Binary upload/download/round-trip and SHA-256 digest tests pass. | Manual demo evidence not saved. |
| M1 | Multi-client isolation | PARTIAL | DONE | Two-client isolation test passes after path fix. | No concurrent simultaneous transfer test. |

### Test Results 2026-07-25 After P0/P1

- Command: `python -m unittest discover -s test -v`
- Preconditions: Windows workspace, Python 3.13.9, after `server/file_manager.py` fix and `test/test_transport.py` addition.
- Expected result: all tests pass.
- Actual result: 62 tests run in 3.529 seconds; OK.
- Result: PASS.
- Evidence covered:
  - Auth: USER/PASS success and failure, anonymous login, PASS-before-USER, login-required command rejection.
  - TCP: greeting, QUIT, NOOP, unknown command, TYPE, MODE, PORT, PASV.
  - Directory/file operations: PWD, MKD, CWD, CDUP, RMD, LIST, NLST, SIZE, MDTM, HASH, DELE, RNFR/RNTO.
  - UDP transfer: STOR, RETR, STOU, APPE, text, binary, empty, exact packet boundary, multi-packet, large file, round-trip, SHA-256.
  - Reliability: ACK loss triggers sender retransmission; duplicate DATA is ACKed without duplicate file write.

### Work Entry 2026-07-25-01 Completion

- Files changed: `server/file_manager.py`, `docs.md`.
- Logic changed: replaced OS-dependent string path joining with FTP virtual segment normalization and `Path.relative_to()` containment check.
- Test run: `python -m unittest discover -s test -v`.
- Result: PASS after fix.
- Remaining issue: active-mode file transfer and transfer cancellation are still not verified.
- Oral-defense note: The server treats FTP paths as virtual POSIX paths. Only after validation are they translated to real OS paths under `storage_root`.

### Work Entry 2026-07-25-02 Completion

- Files changed: `test/test_transport.py`, `docs.md`.
- Logic added: fake socket tests for ACK loss retransmission and duplicate DATA filtering.
- Test run: `python -m unittest discover -s test -v`.
- Result: PASS, 62 tests.
- Remaining issue: no loss-injection integration test with real UDP sockets or proxy yet.
- Oral-defense note: Stop-and-Wait sends one DATA packet, waits for matching ACK, retransmits on timeout, and receiver uses `expected_seq` to avoid duplicate writes.

### GenAI Entry 2026-07-25-01 Completion Addendum

- Code actually accepted: `server/file_manager.py` cross-platform path normalization and `test/test_transport.py` focused RDT behavior tests.
- Code modified before acceptance: removed an unused exception binding in `FileManager.resolve()`.
- Code rejected: none.
- Why the final solution is correct: tests that previously failed with `path escapes storage root` now pass; traversal above root is still rejected; UDP reliability behavior has focused tests for ACK loss and duplicate DATA.
- Tests used to validate: `python -m unittest discover -s test -v`, 62 tests OK.
- Related files: `server/file_manager.py`, `test/test_transport.py`, `docs.md`.

### Updated Demo Checklist 2026-07-25

- [x] Project runs on current verified environment.
- [x] Server start succeeds.
- [x] Client connect succeeds through tests.
- [x] USER/PASS succeeds.
- [x] Login failure is handled.
- [x] NOOP works.
- [x] PWD works.
- [x] LIST works.
- [x] Upload text file succeeds.
- [x] Download text file succeeds.
- [x] Upload binary file succeeds.
- [x] Download binary file succeeds.
- [x] SHA-256 transfer evidence exists in automated tests.
- [ ] Packet loss recovery is demoed with real network/proxy loss.
- [x] ACK loss recovery is tested with fake socket.
- [x] Directory operations are tested.
- [x] Passive mode is tested.
- [x] Two clients connect concurrently.
- [ ] Active session table is displayed.
- [x] Client disconnect does not crash server in tests.
- [x] QUIT closes session correctly.
- [x] Server shutdown cleanup is tested.
- [ ] Demo screenshots/logs are saved.
- [ ] Technical report has required sections.
- [x] Task Assignment Matrix has initial entries.
- [x] GenAI appendix has current session entry.
- [ ] Both members have read `docs.md`.
- [ ] Both members can explain assigned code.

### Historical Remaining Tasks (completed 2026-07-26)

1. Add a real or simulated dropped-DATA/out-of-order/FIN-loss transport test.
2. Add a manual CLI demo log for `connect`, `login`, `put`, `get`, `hash`, and `quit`.
3. Verify or explicitly document active-mode file transfer limitations.
4. Improve `ABOR` from shallow flag setting to real transfer cancellation if required by grading scope.
5. Clean up stale docs in `docs/*.md` or mark them superseded from `docs.md` references.


---

## Completion Update 2026-07-26

All five technical tasks listed under the earlier `Current Remaining Tasks` heading are complete. That heading and all earlier BROKEN/PARTIAL statements are historical audit records, superseded by this update.

| Former task | Completion evidence |
| --- | --- |
| Dropped-DATA / out-of-order / FIN-loss transport coverage | Added focused tests for dropped DATA, dropped ACK, duplicate DATA, out-of-order DATA, and dropped FIN. |
| Manual CLI demonstration | A successful connect, login, put, hash, get, delete, and quit transcript with matching SHA-256 values is in `docs/07-demo-evidence.md`. |
| Active-mode file transfers | Implemented in `FTPClient.upload_active()` / `download_active()` and exposed as `put-active` / `get-active`; binary upload/download is covered by an integration test. |
| Real ABOR cancellation | The server cancels a live worker, closes transfer sockets, returns 426, and protects uploads with temporary files; covered by an integration test. |
| Stale module documents | Each file in `docs/` now has a dated correction; `docs/07-demo-evidence.md` contains the current cross-document evidence. |

### Current technical status

- TCP control and reliable UDP payload transfer: implemented.
- Passive and active transfer coordination: implemented and tested.
- Integrity: client and server verify matching SHA-256 transfer digests.
- Reliability: Stop-and-Wait retransmission, duplicate suppression, ordering protection, CRC-32, and FIN/FIN_ACK are tested.
- Cancellation: ABOR is functional for a live transfer and does not publish a partial upload.
- Latest verification: `python -m unittest discover -s test -v` - 67 tests, OK.

### Submission items that require student-provided facts

These are intentionally not invented by the code audit: named task owners, contribution percentages totaling 100%, peer evaluations, and actual terminal screenshots if the instructor requires images rather than the reproducible transcript. The technical transcript and hash evidence are available in `docs/07-demo-evidence.md`.