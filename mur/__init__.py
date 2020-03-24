import sqlite3
from pathlib import Path

import minicli
import ujson as json
from jinja2 import Environment, PackageLoader, select_autoescape
from roll import Roll, Response
from roll.extensions import static, simple_server, traceback

from . import config


class Response(Response):
    def html(self, template_name, *args, **kwargs):
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.body = env.get_template(template_name).render(*args)


class Roll(Roll):
    Response = Response


app = Roll()
traceback(app)


env = Environment(
    loader=PackageLoader("mur", "templates"), autoescape=select_autoescape(["mur"]),
)


@app.listen("startup")
async def on_startup():
    configure()


@app.route("/", methods=["GET"])
async def home(request, response):
    response.html("index.html")


@app.route("/", methods=["POST"])
async def volunteer_data(request, response):
    data = {k: request.form.get(k) for k in request.form}
    with app.conn as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO volunteers values (?, ?)",
            (data["email"], json.dumps(data)),
        )
    response.html("index.html")


@minicli.cli
def serve(reload=False):
    """Run a web server (for development only)."""
    if reload:
        import hupper

        hupper.start_reloader("mur.serve")
    static(app, root=Path(__file__).parent / "static")
    simple_server(app, port=1919)


@minicli.cli
def init_db():
    configure()
    with app.conn as cursor:
        cursor.execute("CREATE TABLE volunteers (email TEXT, data JSON)")
        cursor.execute("CREATE UNIQUE INDEX volunteers_idx ON volunteers(email);")


def configure():
    app.conn = sqlite3.connect("mur.db")


def main():
    minicli.run()
