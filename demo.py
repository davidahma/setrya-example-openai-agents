"""Exercise the application's HTTP and storage boundaries on a fresh fixture."""
import argparse
from contextlib import contextmanager
import hmac
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
from tempfile import TemporaryDirectory
from threading import Thread

from storage import open_fixture, STACK

CONVERSATION = "ticket-204"


@contextmanager
def serve(store, *, broken, env):
    class Application(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def payload(self, route, token_env):
            if self.path != route:
                self.send_error(404)
                return
            if not hmac.compare_digest(self.headers.get("Authorization", "").encode(),
                                       ("Bearer " + env[token_env]).encode()):
                self.send_error(403)
                return
            try:
                size = int(self.headers.get("Content-Length", ""))
                if not 0 < size <= 8192:
                    raise ValueError
                data = json.loads(self.rfile.read(size))
                if not isinstance(data, dict) or data.get("conversation") != CONVERSATION:
                    raise ValueError
            except (ValueError, UnicodeError):
                self.send_error(400)
                return
            return data

        def do_POST(self):
            data = self.payload("/answer", "SETRYA_READER_TOKEN")
            if data is None:
                return
            question = data.get("question")
            if not isinstance(question, str):
                self.send_error(400)
                return
            answer = store.answer(question)
            body = json.dumps(dict(caller="duty-agent", route=self.path, conversation=CONVERSATION,
                                   question=question, text=answer)).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_DELETE(self):
            data = self.payload("/erasure", "SETRYA_ERASER_TOKEN")
            if data is None:
                return
            if data.get("subject_ref") != env["SETRYA_SUBJECT_REF"]:
                self.send_error(404)
                return
            if not broken:
                store.erase()
            self.send_response(204)
            self.end_headers()

    with HTTPServer(("127.0.0.1", 0), Application) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05})
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_port}"
        finally:
            server.shutdown()
            thread.join()


def cli(env, *args, expected=0):
    result = subprocess.run([sys.executable, "-m", "setrya", *map(str, args)], env=env, check=False)
    if result.returncode != expected:
        raise SystemExit(f"{args[0]} returned {result.returncode}; expected {expected}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("example-results"))
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False, parents=True)
    for lane in ("broken", "fixed"):
        with TemporaryDirectory() as scratch:
            root = Path(scratch)
            env = dict(os.environ, SETRYA_SUBJECT_REF=secrets.token_hex(32),
                       SETRYA_READER_TOKEN=secrets.token_urlsafe(24), SETRYA_ERASER_TOKEN=secrets.token_urlsafe(24))
            receipt = args.output / lane
            with open_fixture(root, env) as store, serve(store, broken=lane == "broken", env=env) as origin:
                env["SETRYA_TEST_ORIGIN"] = origin
                starter = root / "starter"
                cli(env, "init", "--stack", STACK, "--output", starter)
                case = starter / "case.yml"
                store.configure_case(case)
                cli(env, "doctor", "--case", case, "--mode", "deletion")
                cli(env, "run", case, "--mode", "deletion", "--output", receipt, expected=int(lane == "broken"))
            cli(env, "replay", receipt, expected=int(lane == "broken"))


if __name__ == "__main__":
    main()
