from markdown_it import MarkdownIt
from mdit_py_plugins.footnote import footnote_plugin


renderer = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": False,
        "typographer": False,
    },
).enable("table").use(footnote_plugin)


def render_markdown(content: str) -> str:
    return renderer.render(content)