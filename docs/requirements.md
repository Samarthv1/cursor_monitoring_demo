# Demo Server Monitoring — Requirements

## 1. Purpose

L1, L2, and L3 teams currently sign in to Linux servers to check live CPU, memory, network, and port usage. This demo replaces that check with a local web page.

The app runs on the machine where it is started. From that machine it opens SSH to Linux hosts the operator adds, reads those four metrics, and shows them in the browser. It is a local demo, started and used on one machine. It is a read-only view.

## 2. Users

| User | What they do in the demo |
| --- | --- |
| L1, L2, and L3 (infrastructure and application development) | Sign in, add or remove Linux servers, and read live metrics |

All of these teams share one demo account. There are no separate roles and no user-admin screens.

## 3. Scope

- The app is a Python Flask site bound to this machine.
- Monitoring targets are Linux hosts reached by SSH.
- The operator adds a host with its SSH address, user, and either a password or a private key.
- The server list, including SSH sign-in material, is saved in a local file and is still there after a restart.
- Monitoring screens are view-only. The operator can sign in, sign out, add a server, and remove a server. The UI has no action that changes a monitored host.

## 4. Features

### 4.1 Read-only monitoring view

After sign-in, the operator opens a server and reads its current usage. The page has no process kill, service control, command entry, or edits to ports, files, or settings.

The server view refreshes itself about every 10 seconds.

Each server view shows:

| Area | What is shown |
| --- | --- |
| CPU | Overall CPU percent, plus the 1, 5, and 15 minute load averages |
| Memory | Used, free, and total RAM, plus percent used |
| Network | Current inbound and outbound rate for each interface |
| Ports | Listening ports (protocol, port, process) and active connections (local address, remote address, state) |

Network rates are the difference between two counter samples taken about 10 seconds apart.

If SSH fails or one section cannot be read, that section shows unavailable and the rest of the page still loads. A failed SSH attempt shows the server as unreachable with a short reason.

Show at most 100 active connections so the page stays readable.

SSH is used only to read these metrics. The session is closed after the read. Connection attempts time out after about 5 seconds.

### 4.2 Sign-in

- Username: `admin`
- Password: the value of the `ADMIN_PASSWORD` environment variable
- On startup, hash that password with a standard password hash (Werkzeug PBKDF2 or bcrypt). Keep only the hash in memory. Do not log or store the plaintext admin password.
- If `ADMIN_PASSWORD` is missing or empty, the app exits with a short message and does not listen.
- Compare the submitted password to the hash.
- A failed sign-in shows a short error and stays on the sign-in page.
- Every page except sign-in requires a signed-in session.
- Signing out clears the session. It leaves the saved server list in place.

There is no screen to add users or change the password.

### 4.3 Add and remove servers

Add server asks for:

| Field | Rule |
| --- | --- |
| Display name | Required. Unique in the current list. |
| Host | Required. Hostname or IP address. |
| SSH port | Optional. Defaults to 22. |
| SSH username | Required. |
| Auth | Required. Either a password or a private key, not both. |

On first successful connect, store the host key with that entry. On later connects, if the host key changed, mark the server unreachable and show that the key changed.

The new entry is written to the local server file. The list shows the display name, the host, and a live status (up or unreachable).

Remove deletes that entry from the file. Other entries stay.

The list has an empty state that leads to Add server.

The server file holds SSH passwords and private keys so the app can connect again after a restart. This is demo storage on the local machine, not a credential vault. Create the file so only the user running the app can read it. Do not log SSH passwords, private keys, or the admin password. Do not commit the server file.

## 5. Screens

1. **Sign in** — username, password, and a single submit action.
2. **Server list** — entries, status, add, and remove.
3. **Add server** — the fields in §4.3 and submit.
4. **Server detail** — the metric sections in §4.1, updating about every 10 seconds, with a way back to the list.

The interface is a server-rendered Flask UI: a clear dashboard, summary cards for CPU, memory, and network, and a table for ports. It is meant for a laptop browser. No separate frontend build.

## 6. Technical approach

- Python 3 and Flask.
- Jinja templates for the pages.
- An SSH library (Paramiko or equivalent) to read host metrics.
- Flask session cookie for sign-in. Session signing key from the `SECRET_KEY` environment variable. If `SECRET_KEY` is unset, use a fixed local demo value.
- One local JSON file, `data/servers.json`, for the server list. No database.
- If that file is missing, start with an empty list. If it is unreadable, start with an empty list and show a short error on the server list.

The app listens on `127.0.0.1` only.

## 7. Run locally

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install flask paramiko
export ADMIN_PASSWORD='choose-a-password'
python app.py
```

Open `http://127.0.0.1:5000` and sign in as `admin` with the password set in `ADMIN_PASSWORD`.

The Linux hosts being monitored must accept SSH from this machine with the user and password or key entered on Add server.

## 8. Acceptance

- With `ADMIN_PASSWORD` set, sign-in as `admin` opens the server list. A wrong password does not.
- With `ADMIN_PASSWORD` unset, the process exits and does not serve pages.
- Unsigned requests to the list, add, or a server view return to sign in.
- Add server stores an entry that is still present after a restart.
- Remove server drops that entry and it stays gone after a restart.
- The server view shows CPU, memory, network, and ports for that Linux host.
- Those values refresh without a manual reload, about every 10 seconds.
- An unreachable host shows as unreachable. The other servers still open.
- The pages expose no control that changes a monitored host.

## 9. Out of scope

- Windows hosts and agent-based collection
- Disk usage, process lists, alerts, history charts, and retention
- Extra users, roles, or password change
- A shell or any action that changes a monitored host
- Production deployment, TLS, or a public bind address
