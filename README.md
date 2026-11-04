# Demo server monitoring

Local read-only page for Linux CPU, memory, network, and port usage. The app runs on this machine and reads other Linux hosts over SSH. It does not change those hosts.

## Run locally

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='choose-a-password'
export SECRET_KEY='choose-a-session-key'
python app.py
```

Open `http://127.0.0.1:5000` and sign in as `admin` with `ADMIN_PASSWORD`.

`ADMIN_PASSWORD` is required. The app hashes it at startup and exits if it is missing. `SECRET_KEY` signs the session cookie. If you leave it unset, the app uses a fixed local demo value.

Deploy is this command on the machine where you want the page. The app listens on `127.0.0.1` only.

Sign out clears the session and leaves the saved server list in place. There is one shared admin account and no password-change screen.

## Servers

Add server asks for a display name, host, SSH port (default 22), SSH username, and either a password or a private key.

The list is stored in `data/servers.json`. That file holds SSH passwords and private keys so the app can connect again after a restart. It is created so only the user running the app can read it, and git ignores it. Do not commit it.

The Linux host must accept SSH from this machine. A row marked unreachable could not be read; the reason is shown next to the name. Other servers still open. The first successful connect stores the host key. If that key later changes, the row stays unreachable and says the host key changed.

Remove deletes that row from `data/servers.json` only.

## Metrics

Open a server to read:

- CPU: overall percent and the 1, 5, and 15 minute load averages
- Memory: used, free, total, and percent used
- Network: inbound and outbound rate for each interface
- Ports: listening protocol, port, and process, plus up to 100 active connections (local address, remote address, state)

The server page refreshes about every 10 seconds. Network rates use the previous sample from that refresh, so the first view has no rate yet. An unreachable host, or a section that cannot be read, shows unavailable and leaves the rest of the page up.

## Tests

```bash
python -m unittest discover -s tests -t .
```

GitHub Actions runs these tests and a localhost smoke check on push and pull request. The workflow uses a dummy `ADMIN_PASSWORD` and `SECRET_KEY`.
