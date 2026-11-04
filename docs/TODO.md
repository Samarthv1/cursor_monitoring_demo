# Implementation TODO

Local demo, built in small steps. Do one checkbox group at a time. In each group, finish the work, the security line, and the documentation line before starting the next group.

Run and test on this machine. Listen on `127.0.0.1` only. Deploy by running `python app.py` locally.

## Steps

- [x] **1. Project initialization and basic UI**
  - [x] Add `requirements.txt` (`flask`, `paramiko`), `app.py`, and a Jinja base layout.
  - [x] Show a simple dashboard shell: a sign-in placeholder and an empty server list. No separate frontend build.
  - [x] Security: bind `127.0.0.1` only. Keep secrets out of the repo. Add `data/servers.json` and `.venv/` to `.gitignore`.
  - [x] Docs: add a README with the local run commands from `docs/requirements.md`.

- [x] **2. Sign-in and unit tests**
  - [x] Read `ADMIN_PASSWORD` at startup. Exit with a short message when it is missing or empty. Hash it with Werkzeug PBKDF2 or bcrypt and keep only the hash in memory.
  - [x] Sign-in page: username `admin`, password check against the hash, session cookie, short error on failure. `SECRET_KEY` from the environment, with a fixed local demo value when unset.
  - [x] Unit tests: missing password exits, correct password signs in, wrong password stays on the sign-in page.
  - [x] Security: do not log or store the plaintext admin password. Session cookie is HTTP-only.
  - [x] Docs: README notes `ADMIN_PASSWORD` and `SECRET_KEY`.

- [x] **3. CI and local deploy check (GitHub Actions)**
  - [x] Add `.github/workflows/ci.yml`. On push and pull request: install dependencies and run the unit tests.
  - [x] In the same workflow, smoke-check that the app starts with `ADMIN_PASSWORD` set and serves on localhost, then exits.
  - [x] Security: the workflow uses a dummy `ADMIN_PASSWORD` and `SECRET_KEY`. Do not put real SSH material in Actions.
  - [x] Docs: README says how to run tests locally and that deploy is `python app.py` on this machine.

- [x] **4. Require sign-in on every other page**
  - [x] Unsigned requests to the list, add, and server views redirect to sign-in. Add a sign-out action that clears the session and leaves the server file in place.
  - [x] Unit tests for the redirect and for sign-out.
  - [x] Security: one shared `admin` account. No user-admin or password-change screen.
  - [x] Docs: README describes sign-in and sign-out.

- [x] **5. Saved server list**
  - [x] Load and save `data/servers.json`. Missing file starts empty. Unreadable file starts empty and shows a short error on the list.
  - [x] List page: display name, host, and an empty state that links to Add server.
  - [x] Unit tests for missing, valid, and unreadable files.
  - [x] Security: create the file so only the user running the app can read it (`0600`). Do not commit it.
  - [x] Docs: README states where the file lives and that it holds SSH sign-in material.

- [x] **6. Add server**
  - [x] Form fields: display name, host, SSH port (default 22), SSH username, and either a password or a private key.
  - [x] Reject a duplicate display name, a missing host or username, and a form that has both or neither auth secret. Save a valid entry to the file.
  - [x] Unit tests for those validation rules and for a saved entry still being present after reload.
  - [x] Security: never log the SSH password or private key. The form is reachable only after sign-in.
  - [x] Docs: README lists the add-server fields.

- [x] **7. Remove server**
  - [x] Remove deletes one entry from the file and leaves the others.
  - [x] Unit test: the removed entry is gone after reload.
  - [x] Security: remove only changes the local server file. It does not open SSH and does not change the remote host.
  - [x] Docs: README notes remove.

- [x] **8. SSH status check**
  - [x] On demand, connect with a timeout of about 5 seconds. Mark the entry up or unreachable with a short reason. Close the SSH session after the check.
  - [x] On first success, store the host key on the entry. If the key later differs, mark the server unreachable and say the key changed.
  - [x] Unit tests with a fake SSH client for success, timeout, and host-key change. No real network in tests.
  - [x] Security: SSH is used only for this read. Do not offer a shell or remote write.
  - [x] Docs: README notes the host must accept SSH from this machine, and what an unreachable row means.

- [x] **9. CPU and memory on the server view**
  - [x] Server detail page with cards for overall CPU percent, the 1, 5, and 15 minute load averages, and memory used, free, total, and percent.
  - [x] A section that cannot be read shows unavailable. The rest of the page still loads.
  - [x] Unit tests with fake command output for both sections and for a failed section.
  - [x] Security: the remote commands are read-only. The page has no kill, service control, or command box.
  - [x] Docs: README lists the CPU and memory fields.

- [x] **10. Network rates**
  - [x] Show current inbound and outbound rate per interface, from two counter samples about 10 seconds apart.
  - [x] Unit test the rate math with two fake samples.
  - [x] Security: read interface counters only. Do not change interface state.
  - [x] Docs: README says rates are per interface over about 10 seconds.

- [x] **11. Ports**
  - [x] Show listening ports (protocol, port, process) and active connections (local address, remote address, state). Cap active connections at 100.
  - [x] Unit tests for parsing and for the cap.
  - [x] Security: display only. No action opens, closes, or edits a port.
  - [x] Docs: README describes the ports table and the 100-row cap.

- [x] **12. Auto-refresh and failure isolation**
  - [x] The server view refreshes itself about every 10 seconds and links back to the list.
  - [x] An unreachable host shows as unreachable. Other servers still open. One failed metric section does not blank the page.
  - [x] Unit test: a failed SSH read renders the unavailable state and does not drop the other entries.
  - [x] Security: refresh only re-reads metrics. Confirm the pages expose no control that changes a monitored host.
  - [x] Docs: README states the refresh interval and the unreachable behavior.

## Done when

- [x] Sign-in, route protection, add, remove, file reload, and metric parsing are covered by unit tests.
- [ ] GitHub Actions runs those tests and the local smoke check.
- [ ] `ADMIN_PASSWORD` is set, `python app.py` serves `http://127.0.0.1:5000`, and a signed-in user can add a Linux host and read CPU, memory, network, and ports.
