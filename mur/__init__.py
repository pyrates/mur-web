import sqlite3
from pathlib import Path

import minicli
import ujson as json
from jinja2 import Environment, PackageLoader, select_autoescape
from roll import HttpError, Response, Roll
from roll.extensions import simple_server, static, traceback

from . import utils, emails


class Response(Response):
    def html(self, template_name, *args, **context):
        if self.request.cookies.get("message"):
            context["message"] = json.loads(self.request.cookies["message"])
            self.cookies.set("message", "")
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.body = env.get_template(template_name).render(*args, **context)

    def message(self, text, status="success"):
        self.cookies.set("message", json.dumps((text, status)))


class Roll(Roll):
    Response = Response


app = Roll()
traceback(app)


env = Environment(
    loader=PackageLoader("mur", "templates"), autoescape=select_autoescape(["mur"]),
)


def token_required(view):

    def wrapper(request, response, *args, **kwargs):
        token = request.query.get("token")
        try:
            request["email"] = utils.read_token(token)
        except ValueError:
            # TODO message
            raise HttpError(401, "Invalid token")
        return view(request, response, *args, **kwargs)
    return wrapper


@app.listen("request")
async def attach_request(request, response):
    # TODO should this be done by default in Roll ?
    response.request = request


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
    response.message(f"Un sésame a été envoyé sur le courriel {email}", "info")
    response.status = 302
    response.headers["Location"] = "/"


@app.route("/aider", methods=["GET"])
@token_required
async def volunteer_form(request, response):
    response.html("form.html", email=request["email"])


@app.route("/aider", methods=["POST"])
@token_required
async def volunteer_data(request, response):
    data = {k: request.form.get(k) for k in request.form}
    with app.conn as cursor:
        cursor.execute(
            "INSERT OR REPLACE INTO volunteers values (?, ?)",
            (request["email"], json.dumps(data)),
        )
    response.message(f"Merci! Nous reviendrons vers vous très vite", "info")
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
