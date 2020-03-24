from pathlib import Path

import minicli
import ujson as json
from jinja2 import Environment, PackageLoader, select_autoescape
from roll import Roll, Response
from roll.extensions import static, simple_server

from . import config


class Response(Response):
    def html(self, template_name, *args, **kwargs):
        self.headers["Content-Type"] = "text/html; charset=utf-8"
        self.body = env.get_template(template_name).render(*args)


class Roll(Roll):
    Response = Response


app = Roll()


env = Environment(
    loader=PackageLoader("mur", "templates"), autoescape=select_autoescape(["mur"]),
)


@app.route("/", methods=["GET"])
async def home(request, response):
    response.html("index.html")


@minicli.cli
def serve(reload=False):
    """Run a web server (for development only)."""
    if reload:
        import hupper

        hupper.start_reloader("mur.serve")
    static(app, root=Path(__file__).parent / "static")
    simple_server(app, port=1919)


def main():
    minicli.run()
