from markdown_it import MarkdownIt


renderer = MarkdownIt(
    "commonmark",
    {
        "html": False,
        "linkify": False,
        "typographer": False,
    },
).enable("table")


def render_markdown(content: str) -> str:
    return renderer.render(content)