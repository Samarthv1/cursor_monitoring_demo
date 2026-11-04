import os
import sys

from flask import Flask, abort, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from monitoring.ssh import Monitor
from monitoring.store import (
    DEFAULT_SERVERS_PATH,
    load_servers,
    public_view,
    save_servers,
    validate_new_server,
)

LOCAL_DEMO_SECRET = "local-demo-secret"
ADMIN_USERNAME = "admin"


def create_app(admin_password, secret_key=None, servers_path=None, connector=None):
    app = Flask(__name__)
    app.secret_key = secret_key or LOCAL_DEMO_SECRET
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["ADMIN_PASSWORD_HASH"] = generate_password_hash(
        admin_password, method="pbkdf2:sha256"
    )
    app.config["SERVERS_PATH"] = servers_path or DEFAULT_SERVERS_PATH
    app.config["MONITOR"] = Monitor(connector)

    @app.context_processor
    def inject_session():
        return {"signed_in": bool(session.get("signed_in"))}

    @app.before_request
    def require_sign_in():
        if request.endpoint in {"login", "login_submit", "logout", "static"}:
            return None
        if not session.get("signed_in"):
            return redirect(url_for("login"))
        return None

    @app.after_request
    def keep_pages_private(response):
        if request.endpoint != "static":
            response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/login")
    def login():
        if session.get("signed_in"):
            return redirect(url_for("index"))
        return render_template("login.html", error=None)

    @app.post("/login")
    def login_submit():
        username = request.form.get("username") or ""
        password = request.form.get("password") or ""
        password_ok = check_password_hash(app.config["ADMIN_PASSWORD_HASH"], password)
        if username != ADMIN_USERNAME or not password_ok:
            return render_template("login.html", error="Sign-in failed."), 200
        session.clear()
        session["signed_in"] = True
        return redirect(url_for("index"))

    @app.post("/logout")
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.get("/")
    def index():
        servers, error = load_servers(app.config["SERVERS_PATH"])
        if error:
            return render_template("servers.html", servers=[], load_error=error)
        monitor = app.config["MONITOR"]
        for server in servers:
            status, reason, host_key = monitor.probe(server)
            _apply_status(server, status, reason, host_key)
        if servers:
            save_servers(app.config["SERVERS_PATH"], servers)
        return render_template(
            "servers.html",
            servers=[public_view(server) for server in servers],
            load_error=None,
        )

    @app.route("/servers/add", methods=["GET", "POST"])
    def add_server():
        if request.method == "GET":
            return render_template("add_server.html", error=None, form={})
        servers, error = load_servers(app.config["SERVERS_PATH"])
        if error:
            return render_template(
                "add_server.html",
                error=error,
                form=_form_values(request.form),
            )
        entry, form_error = validate_new_server(request.form, servers)
        if form_error:
            return render_template(
                "add_server.html",
                error=form_error,
                form=_form_values(request.form),
            )
        servers.append(entry)
        try:
            save_servers(app.config["SERVERS_PATH"], servers)
        except OSError:
            return render_template(
                "add_server.html",
                error="The server list could not be saved.",
                form=_form_values(request.form),
            )
        return redirect(url_for("index"))

    @app.post("/servers/<server_id>/remove")
    def remove_server(server_id):
        servers, error = load_servers(app.config["SERVERS_PATH"])
        if error:
            return redirect(url_for("index"))
        kept = [server for server in servers if server.get("id") != server_id]
        if len(kept) == len(servers):
            abort(404)
        save_servers(app.config["SERVERS_PATH"], kept)
        return redirect(url_for("index"))

    @app.get("/servers/<server_id>")
    def server_detail(server_id):
        servers, error = load_servers(app.config["SERVERS_PATH"])
        if error:
            return redirect(url_for("index"))
        server = next((item for item in servers if item.get("id") == server_id), None)
        if server is None:
            abort(404)
        report = app.config["MONITOR"].metrics(server)
        _apply_status(
            server,
            "up" if report["reachable"] else "unreachable",
            report["reason"],
            report["host_key"],
        )
        try:
            save_servers(app.config["SERVERS_PATH"], servers)
        except OSError:
            pass
        return render_template(
            "detail.html",
            server=public_view(server),
            report=report,
        )

    return app


def _apply_status(server, status, reason, host_key):
    server["status"] = status
    server["status_reason"] = reason
    if host_key:
        server["host_key"] = host_key


def _form_values(form):
    return {
        "name": form.get("name") or "",
        "host": form.get("host") or "",
        "port": form.get("port") or "",
        "username": form.get("username") or "",
    }


def main():
    password = os.environ.get("ADMIN_PASSWORD", "").strip()
    if not password:
        print("ADMIN_PASSWORD is required.", file=sys.stderr)
        sys.exit(1)
    secret = os.environ.get("SECRET_KEY", "").strip() or None
    app = create_app(password, secret_key=secret)
    app.run(host="127.0.0.1", port=5000)


if __name__ == "__main__":
    main()
