# Defense Demo Bundle

Folder nay duoc tao de em demo nhanh tat ca chuc nang da hien thuc trong Hybrid FTP.

## 1. Local files da chuan bi san

Tat ca file upload bang CLI nen dung trong `client/upload/defense_demo/`:

- `ascii_demo.txt`: file text nho de demo `STOR`, `RETR`, `HASH`, `SIZE`, `MDTM`, `TYPE A`
- `rename_source.txt`: file text de demo `RNFR`/`RNTO`, `DELE`
- `append_base.txt`: phan dau cua file append
- `append_tail.txt`: phan du lieu them vao de demo `APPE`
- `multi_packet.txt`: file text > 1 KB de demo reliable UDP nhieu packet

File binary co san trong repo de demo `TYPE I`, binary upload/download, active mode:

- `test_files/sample.jpg`
- `test_files/sample.pdf`
- `test_files/docker.png`

Remote binary co san trong `server/storage/` neu muon demo download truc tiep:

- `10mb-example-jpg.jpg`
- `book.pdf`
- `window.zip`
- `pexels-simplyart-9020071.mp4`
- `viber.deb`

## 2. Demo nhanh bang CLI chinh

Chay server:

```bash
python3 server/main.py
```

Chay client:

```bash
python3 client/main.py
```

Chuoi lenh nen demo trong buoi defense:

```text
CONNECT
USER admin
PASS 1234
HELP
NOOP
PWD
MKD defense-room
CWD defense-room
PWD
STOR defense_demo/ascii_demo.txt
LIST
NLST
SIZE ascii-demo.txt
MDTM ascii-demo.txt
HASH ascii-demo.txt
stat ascii-demo.txt
TYPE A
RETR ascii-demo.txt
TYPE I
# Place an image in client/upload/image-demo.jpg before this command.
STOR image-demo.jpg
RETR image-demo.jpg
# Active-mode binary transfer: use FTPClient.upload_active() and FTPClient.download_active() in a short Python demo.
STOR defense_demo/rename_source.txt
RNFR rename-source.txt
RNTO renamed-demo.txt
DELE renamed-demo.txt
STOR defense_demo/append_base.txt
CDUP
LIST
QUIT
```

Sau do dung helper script ben duoi de demo nhung lenh khong tien show trong REPL.

## 3. Lenh khong demo tien trong CLI

Script ho tro: `defense_demo/raw_demo.py`

Chay cac lenh nay tu thu muc goc cua repo `Hybrid-FTP`.

### MODE

```bash
python3 defense_demo/raw_demo.py mode S
```

Neu thay muon hoi ve mode khong ho tro:

```bash
python3 defense_demo/raw_demo.py mode B
```

Se tra `502` vi server chi ho tro `MODE S`.

### HELP (reply raw tu server)

```bash
python3 defense_demo/raw_demo.py help
```

### STAT tong quat

```bash
python3 defense_demo/raw_demo.py stat
python3 defense_demo/raw_demo.py stat ascii-demo.txt --cwd /defense-room
```

### STOU

```bash
python3 defense_demo/raw_demo.py stou client/upload/defense_demo/rename_source.txt --cwd /defense-room
```

Script se in ra ten file moi vua duoc tao.

### APPE

```bash
python3 defense_demo/raw_demo.py appe client/upload/defense_demo/append_tail.txt append-demo.txt --cwd /defense-room
```

Sau do co the kiem tra bang:

```text
CWD defense-room
RETR append-demo.txt
HASH append-demo.txt
```

### ABOR

```bash
python3 defense_demo/raw_demo.py abor aborted-demo.bin --cwd /defense-room
```

Script se mo `STOR`, gui `ABOR`, roi kiem tra rang file dich khong duoc tao.

## 4. Don dep de demo `RMD`

Sau khi demo xong trong `defense-room`, xoa cac file vua tao roi moi `RMD`:

```text
CWD defense-room
DELE ascii-demo.txt
DELE image-demo.jpg
DELE active-demo.png
DELE append-demo.txt
DELE multi-packet.txt
DELE file
DELE file.1
CDUP
RMD defense-room
```

Neu `STOU` tao ten khac, xem lai bang `nlst` roi xoa dung ten do.

## 5. Mapping requirement -> file / cach demo

| Requirement | Cach demo | File dung |
| --- | --- | --- |
| `USER`, `PASS`, `QUIT`, `NOOP` | CLI | khong can file |
| `PWD`, `CWD`, `CDUP`, `MKD`, `RMD` | CLI voi `defense-room` | khong can file |
| `LIST`, `NLST` | CLI sau khi tao/upload file | `ascii_demo.txt` |
| `STAT` | CLI hoac `raw_demo.py stat` | `ascii_demo.txt` |
| `SIZE`, `MDTM`, `HASH` | CLI | `ascii_demo.txt`, `image-demo.jpg` |
| `TYPE A` | CLI truoc text transfer | `ascii_demo.txt` |
| `TYPE I` | CLI truoc binary transfer | `sample.jpg`, `docker.png` |
| `MODE` | `raw_demo.py mode S` | khong can file |
| `PASV` | Automatically used by `STOR` / `RETR` | bat ky file upload/download |
| `PORT` | `FTPClient.upload_active()` / `download_active()` | `docker.png` |
| `STOR`, `RETR` | CLI | `ascii_demo.txt`, `sample.jpg` |
| `STOU` | `raw_demo.py stou` | `rename_source.txt` |
| `APPE` | `raw_demo.py appe` | `append_base.txt`, `append_tail.txt` |
| `DELE` | CLI | `renamed-demo.txt` |
| `RNFR`, `RNTO` | CLI as two commands | `rename_source.txt` |
| `ABOR` | `raw_demo.py abor` | khong can local file |
| `HELP` | CLI `help` hoac `raw_demo.py help` | khong can file |

## 6. Ghi chu de defense

- `STOR` va `RETR` dung passive mode trong CLI. Active mode duoc demo qua `FTPClient.upload_active()` va `download_active()`.
- CLI hien tai hien thi cac verb FTP chuan; `raw_demo.py` van huu ich de lap lai cac tinh huong STOU, APPE, ABOR va active mode.
- Khi can chung minh binary khong bi hong, dung `FTPClient.upload_active()` / `download_active()` va `HASH` de so sanh digest.
- Khi can chung minh reliable UDP nhieu packet, dung `STOR defense_demo/multi_packet.txt` sau khi tao remote folder phu hop.
