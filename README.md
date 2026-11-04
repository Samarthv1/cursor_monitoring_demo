# Demo server monitoring

Local read-only page for checking Linux CPU, memory, network, and port usage. This step serves the dashboard shell on this machine.

## Run locally

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export ADMIN_PASSWORD='choose-a-password'
python app.py
```

Open `http://127.0.0.1:5000`.

The app listens on `127.0.0.1` only. The sign-in form on the page is a placeholder. `ADMIN_PASSWORD` is reserved for the sign-in step.

`data/servers.json` is ignored by git. It will hold SSH sign-in material for added hosts. Do not commit it.
