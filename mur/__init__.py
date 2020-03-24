import sqlite3
from pathlib import Path

import minicli
import ujson as json
from jinja2 import Environment, PackageLoader, select_autoescape
from roll import HttpError, Response, Roll
from roll.extensions import simple_server, static, traceback

from . import config, utils, emails


class Response(Response):
    def html(self, template_name, *args, **kwargs):
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.body = env.get_template(template_name).render(*args, **kwargs)


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
    response.html("home.html")


@app.route("/cgu.html", methods=["GET"])
async def cgu(request, response):
    response.html("cgu.html")


@app.route("/", methods=["POST"])
async def door_opener(request, response):
    # Send email
    email = request.form.get("email")
    token = utils.create_token(email)
    link = f"https://{request.host}/aider?token={token.decode()}"
    body = f"""
    Salut!

    {link}

    Merci!
    """
    print(link)
    emails.send(email, "MUR sésame", body)
    # TODO message
    response.status = 302
    response.headers["Location"] = "/"


@app.route("/aider", methods=["GET"])
async def volunteer_form(request, response):
    token = request.query.get("token")
    try:
        email = utils.read_token(token)
    except ValueError:
        # TODO message
        raise HttpError(401, "Invalid token")
    response.html("form.html", email=email)


@app.route("/aider", methods=["POST"])
async def volunteer_data(request, response):
    token = request.query.get("token")
    try:
        email = utils.read_token(token)
    except ValueError:
        # TODO message
        raise HttpError(401, "Invalid token")
    data = {k: request.form.get(k) for k in request.form}
    with app.conn as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO volunteers values (?, ?)",
            (email, json.dumps(data)),
        )
    # TODO message
    response.status = 302
    response.headers["Location"] = "/"


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
