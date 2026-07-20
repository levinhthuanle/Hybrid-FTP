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