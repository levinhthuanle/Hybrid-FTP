# Demo and Verification Evidence

Date: 2026-07-26  
Environment: Windows workspace, local server at `127.0.0.1:2121`

## Manual CLI transfer

A local server was started with `python server/main.py`. The following command sequence uses the current approved CLI syntax. Place the source file under `client/upload/` with the same filename before `STOR`:

```text
Hybrid FTP Client. Type 'help' for commands.
ftp> connect
Connected to 127.0.0.1:2121 - Hybrid FTP Server ready
ftp> USER admin
Username accepted; send PASS <password>.
ftp> PASS 1234
Login successful.
ftp> STOR demo-sample.txt
Uploading D:\Projects\IP\Hybrid-FTP\test_files\sample.txt -> demo-sample.txt ...
Upload complete. SHA-256: f84e951432fc2c1b6da5f28397ed07d6c362098a4a7b92848eafbda1770a8b76
ftp> HASH demo-sample.txt
f84e951432fc2c1b6da5f28397ed07d6c362098a4a7b92848eafbda1770a8b76
ftp> RETR demo-sample.txt
Downloading demo-sample.txt -> client\download\demo-sample.txt ...
Download complete. SHA-256: f84e951432fc2c1b6da5f28397ed07d6c362098a4a7b92848eafbda1770a8b76
Saved to: client\download\demo-sample.txt
ftp> DELE demo-sample.txt
Deleted 'demo-sample.txt'.
ftp> QUIT
Disconnected.
```

The upload, remote HASH response, and download all produced the same SHA-256 value. The remote demo file was deleted with `DELE`; the temporary local download was also removed after capture, so the repository does not retain demo artifacts.

## Automated verification

```text
Command: python -m unittest discover -s test -v
Result: Ran 67 tests in 4.893s
Status: OK
```

The suite includes end-to-end text/binary/empty/multi-packet transfer checks, active-mode upload/download, ABOR cancellation, two-client isolation, and focused reliable-UDP loss/reorder tests.

## Evidence boundaries

This file records a reproducible terminal transcript and test result. It does not claim that image screenshots were captured. If the course rubric requires visual screenshots, capture the server and client terminals during the same command sequence and add those images to the final report.