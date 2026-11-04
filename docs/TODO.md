# Implementation TODO

Local demo, built in small steps. Do one checkbox group at a time. In each group, finish the work, the security line, and the documentation line before starting the next group.

Run and test on this machine. Listen on `127.0.0.1` only. Deploy by running `python app.py` locally.

## Steps

- [x] **1. Project initialization and basic UI**
  - [x] Add `requirements.txt` (`flask`, `paramiko`), `app.py`, and a Jinja base layout.
  - [x] Show a simple dashboard shell: a sign-in placeholder and an empty server list. No separate frontend build.
  - [x] Security: bind `127.0.0.1` only. Keep secrets out of the repo. Add `data/servers.json` and `.venv/` to `.gitignore`.
  - [x] Docs: add a README with the local run commands from `docs/requirements.md`.

- [ ] **2. Sign-in and unit tests**
  - [ ] Read `ADMIN_PASSWORD` at startup. Exit with a short message when it is missing or empty. Hash it with Werkzeug PBKDF2 or bcrypt and keep only the hash in memory.
  - [ ] Sign-in page: username `admin`, password check against the hash, session cookie, short error on failure. `SECRET_KEY` from the environment, with a fixed local demo value when unset.
  - [ ] Unit tests: missing password exits, correct password signs in, wrong password stays on the sign-in page.
  - [ ] Security: do not log or store the plaintext admin password. Session cookie is HTTP-only.
  - [ ] Docs: README notes `ADMIN_PASSWORD` and `SECRET_KEY`.

- [ ] **3. CI and local deploy check (GitHub Actions)**
  - [ ] Add `.github/workflows/ci.yml`. On push and pull request: install dependencies and run the unit tests.
  - [ ] In the same workflow, smoke-check that the app starts with `ADMIN_PASSWORD` set and serves on localhost, then exits.
  - [ ] Security: the workflow uses a dummy `ADMIN_PASSWORD` and `SECRET_KEY`. Do not put real SSH material in Actions.
  - [ ] Docs: README says how to run tests locally and that deploy is `python app.py` on this machine.

- [ ] **4. Require sign-in on every other page**
  - [ ] Unsigned requests to the list, add, and server views redirect to sign-in. Add a sign-out action that clears the session and leaves the server file in place.
  - [ ] Unit tests for the redirect and for sign-out.
  - [ ] Security: one shared `admin` account. No user-admin or password-change screen.
  - [ ] Docs: README describes sign-in and sign-out.

- [ ] **5. Saved server list**
  - [ ] Load and save `data/servers.json`. Missing file starts empty. Unreadable file starts empty and shows a short error on the list.
  - [ ] List page: display name, host, and an empty state that links to Add server.
  - [ ] Unit tests for missing, valid, and unreadable files.
  - [ ] Security: create the file so only the user running the app can read it (`0600`). Do not commit it.
  - [ ] Docs: README states where the file lives and that it holds SSH sign-in material.

- [ ] **6. Add server**
  - [ ] Form fields: display name, host, SSH port (default 22), SSH username, and either a password or a private key.
  - [ ] Reject a duplicate display name, a missing host or username, and a form that has both or neither auth secret. Save a valid entry to the file.
  - [ ] Unit tests for those validation rules and for a saved entry still being present after reload.
  - [ ] Security: never log the SSH password or private key. The form is reachable only after sign-in.
  - [ ] Docs: README lists the add-server fields.

- [ ] **7. Remove server**
  - [ ] Remove deletes one entry from the file and leaves the others.
  - [ ] Unit test: the removed entry is gone after reload.
  - [ ] Security: remove only changes the local server file. It does not open SSH and does not change the remote host.
  - [ ] Docs: README notes remove.

- [ ] **8. SSH status check**
  - [ ] On demand, connect with a timeout of about 5 seconds. Mark the entry up or unreachable with a short reason. Close the SSH session after the check.
  - [ ] On first success, store the host key on the entry. If the key later differs, mark the server unreachable and say the key changed.
  - [ ] Unit tests with a fake SSH client for success, timeout, and host-key change. No real network in tests.
  - [ ] Security: SSH is used only for this read. Do not offer a shell or remote write.
  - [ ] Docs: README notes the host must accept SSH from this machine, and what an unreachable row means.

- [ ] **9. CPU and memory on the server view**
  - [ ] Server detail page with cards for overall CPU percent, the 1, 5, and 15 minute load averages, and memory used, free, total, and percent.
  - [ ] A section that cannot be read shows unavailable. The rest of the page still loads.
  - [ ] Unit tests with fake command output for both sections and for a failed section.
  - [ ] Security: the remote commands are read-only. The page has no kill, service control, or command box.
  - [ ] Docs: README lists the CPU and memory fields.

- [ ] **10. Network rates**
  - [ ] Show current inbound and outbound rate per interface, from two counter samples about 10 seconds apart.
  - [ ] Unit test the rate math with two fake samples.
  - [ ] Security: read interface counters only. Do not change interface state.
  - [ ] Docs: README says rates are per interface over about 10 seconds.

- [ ] **11. Ports**
  - [ ] Show listening ports (protocol, port, process) and active connections (local address, remote address, state). Cap active connections at 100.
  - [ ] Unit tests for parsing and for the cap.
  - [ ] Security: display only. No action opens, closes, or edits a port.
  - [ ] Docs: README describes the ports table and the 100-row cap.

- [ ] **12. Auto-refresh and failure isolation**
  - [ ] The server view refreshes itself about every 10 seconds and links back to the list.
  - [ ] An unreachable host shows as unreachable. Other servers still open. One failed metric section does not blank the page.
  - [ ] Unit test: a failed SSH read renders the unavailable state and does not drop the other entries.
  - [ ] Security: refresh only re-reads metrics. Confirm the pages expose no control that changes a monitored host.
  - [ ] Docs: README states the refresh interval and the unreachable behavior.

## Done when

- [ ] Sign-in, route protection, add, remove, file reload, and metric parsing are covered by unit tests.
- [ ] GitHub Actions runs those tests and the local smoke check.
- [ ] `ADMIN_PASSWORD` is set, `python app.py` serves `http://127.0.0.1:5000`, and a signed-in user can add a Linux host and read CPU, memory, network, and ports.
