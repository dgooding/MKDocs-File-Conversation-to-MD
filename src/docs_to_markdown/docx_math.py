"""In-memory OMML-to-LaTeX preprocessing for DOCX streams."""

import zipfile
from io import BytesIO
from typing import BinaryIO

from bs4 import BeautifulSoup, Tag
from defusedxml import ElementTree as ET


OMML_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
CHARS = ("{", "}", "_", "^", "#", "&", "$", "%", "~")
BLANK = ""
BACKSLASH = "\\"
ALN = "&"
BRK = "\\\\"
FUNC_PLACE = "{fe}"

CHR = {
    "\u0300": "\\grave{{{0}}}",
    "\u0301": "\\acute{{{0}}}",
    "\u0302": "\\hat{{{0}}}",
    "\u0303": "\\tilde{{{0}}}",
    "\u0304": "\\bar{{{0}}}",
    "\u0305": "\\overbar{{{0}}}",
    "\u0306": "\\breve{{{0}}}",
    "\u0307": "\\dot{{{0}}}",
    "\u0308": "\\ddot{{{0}}}",
    "\u0309": "\\ovhook{{{0}}}",
    "\u030a": "\\ocirc{{{0}}}}",
    "\u030c": "\\check{{{0}}}}",
    "\u0310": "\\candra{{{0}}}",
    "\u0312": "\\oturnedcomma{{{0}}}",
    "\u0315": "\\ocommatopright{{{0}}}",
    "\u031a": "\\droang{{{0}}}",
    "\u0338": "\\not{{{0}}}",
    "\u20d0": "\\leftharpoonaccent{{{0}}}",
    "\u20d1": "\\rightharpoonaccent{{{0}}}",
    "\u20d2": "\\vertoverlay{{{0}}}",
    "\u20d6": "\\overleftarrow{{{0}}}",
    "\u20d7": "\\vec{{{0}}}",
    "\u20db": "\\dddot{{{0}}}",
    "\u20dc": "\\ddddot{{{0}}}",
    "\u20e1": "\\overleftrightarrow{{{0}}}",
    "\u20e7": "\\annuity{{{0}}}",
    "\u20e9": "\\widebridgeabove{{{0}}}",
    "\u20f0": "\\asteraccent{{{0}}}",
    "\u0330": "\\wideutilde{{{0}}}",
    "\u0331": "\\underbar{{{0}}}",
    "\u20e8": "\\threeunderdot{{{0}}}",
    "\u20ec": "\\underrightharpoondown{{{0}}}",
    "\u20ed": "\\underleftharpoondown{{{0}}}",
    "\u20ee": "\\underledtarrow{{{0}}}",
    "\u20ef": "\\underrightarrow{{{0}}}",
    "\u23b4": "\\overbracket{{{0}}}",
    "\u23dc": "\\overparen{{{0}}}",
    "\u23de": "\\overbrace{{{0}}}",
    "\u23b5": "\\underbracket{{{0}}}",
    "\u23dd": "\\underparen{{{0}}}",
    "\u23df": "\\underbrace{{{0}}}",
}

CHR_BO = {
    "\u2140": "\\Bbbsum",
    "\u220f": "\\prod",
    "\u2210": "\\coprod",
    "\u2211": "\\sum",
    "\u222b": "\\int",
    "\u22c0": "\\bigwedge",
    "\u22c1": "\\bigvee",
    "\u22c2": "\\bigcap",
    "\u22c3": "\\bigcup",
    "\u2a00": "\\bigodot",
    "\u2a01": "\\bigoplus",
    "\u2a02": "\\bigotimes",
}

T = {
    "\U0001d6fc": "\\alpha ",
    "\U0001d6fd": "\\beta ",
    "\U0001d6fe": "\\gamma ",
    "\U0001d6ff": "\\delta ",
    "\U0001d700": "\\epsilon ",
    "\U0001d701": "\\zeta ",
    "\U0001d702": "\\eta ",
    "\U0001d703": "\\theta ",
    "\U0001d704": "\\iota ",
    "\U0001d705": "\\kappa ",
    "\U0001d706": "\\lambda ",
    "\U0001d707": "\\mu ",
    "\U0001d708": "\\nu ",
    "\U0001d709": "\\xi ",
    "\U0001d70a": "\\omicron ",
    "\U0001d70b": "\\pi ",
    "\U0001d70c": "\\rho ",
    "\U0001d70d": "\\varsigma ",
    "\U0001d70e": "\\sigma ",
    "\U0001d70f": "\\tau ",
    "\U0001d710": "\\upsilon ",
    "\U0001d711": "\\phi ",
    "\U0001d712": "\\chi ",
    "\U0001d713": "\\psi ",
    "\U0001d714": "\\omega ",
    "\U0001d715": "\\partial ",
    "\U0001d716": "\\varepsilon ",
    "\U0001d717": "\\vartheta ",
    "\U0001d718": "\\varkappa ",
    "\U0001d719": "\\varphi ",
    "\U0001d71a": "\\varrho ",
    "\U0001d71b": "\\varpi ",
    "\u2190": "\\leftarrow ",
    "\u2191": "\\uparrow ",
    "\u2192": "\\rightarrow ",
    "\u2193": "\\downarrow ",
    "\u2194": "\\leftrightarrow ",
    "\u2195": "\\updownarrow ",
    "\u2196": "\\nwarrow ",
    "\u2197": "\\nearrow ",
    "\u2198": "\\searrow ",
    "\u2199": "\\swarrow ",
    "\u22ee": "\\vdots ",
    "\u22ef": "\\cdots ",
    "\u22f0": "\\adots ",
    "\u22f1": "\\ddots ",
    "\u2260": "\\ne ",
    "\u2264": "\\leq ",
    "\u2265": "\\geq ",
    "\u2266": "\\leqq ",
    "\u2267": "\\geqq ",
    "\u2268": "\\lneqq ",
    "\u2269": "\\gneqq ",
    "\u226a": "\\ll ",
    "\u226b": "\\gg ",
    "\u2208": "\\in ",
    "\u2209": "\\notin ",
    "\u220b": "\\ni ",
    "\u220c": "\\nni ",
    "\u221e": "\\infty ",
    "\u00b1": "\\pm ",
    "\u2213": "\\mp ",
    "\U0001d434": "A",
    "\U0001d435": "B",
    "\U0001d436": "C",
    "\U0001d437": "D",
    "\U0001d438": "E",
    "\U0001d439": "F",
    "\U0001d43a": "G",
    "\U0001d43b": "H",
    "\U0001d43c": "I",
    "\U0001d43d": "J",
    "\U0001d43e": "K",
    "\U0001d43f": "L",
    "\U0001d440": "M",
    "\U0001d441": "N",
    "\U0001d442": "O",
    "\U0001d443": "P",
    "\U0001d444": "Q",
    "\U0001d445": "R",
    "\U0001d446": "S",
    "\U0001d447": "T",
    "\U0001d448": "U",
    "\U0001d449": "V",
    "\U0001d44a": "W",
    "\U0001d44b": "X",
    "\U0001d44c": "Y",
    "\U0001d44d": "Z",
    "\U0001d44e": "a",
    "\U0001d44f": "b",
    "\U0001d450": "c",
    "\U0001d451": "d",
    "\U0001d452": "e",
    "\U0001d453": "f",
    "\U0001d454": "g",
    "\U0001d456": "i",
    "\U0001d457": "j",
    "\U0001d458": "k",
    "\U0001d459": "l",
    "\U0001d45a": "m",
    "\U0001d45b": "n",
    "\U0001d45c": "o",
    "\U0001d45d": "p",
    "\U0001d45e": "q",
    "\U0001d45f": "r",
    "\U0001d460": "s",
    "\U0001d461": "t",
    "\U0001d462": "u",
    "\U0001d463": "v",
    "\U0001d464": "w",
    "\U0001d465": "x",
    "\U0001d466": "y",
    "\U0001d467": "z",
}

FUNC = {
    "sin": "\\sin({fe})",
    "cos": "\\cos({fe})",
    "tan": "\\tan({fe})",
    "arcsin": "\\arcsin({fe})",
    "arccos": "\\arccos({fe})",
    "arctan": "\\arctan({fe})",
    "arccot": "\\arccot({fe})",
    "sinh": "\\sinh({fe})",
    "cosh": "\\cosh({fe})",
    "tanh": "\\tanh({fe})",
    "coth": "\\coth({fe})",
    "sec": "\\sec({fe})",
    "csc": "\\csc({fe})",
}

CHR_DEFAULT = {"ACC_VAL": "\\hat{{{0}}}", "GROUP_CHR_VAL": "\\underbrace{{{0}}}"}
POS = {"top": "\\overline{{{0}}}", "bot": "\\underline{{{0}}}"}
POS_DEFAULT = {"BAR_VAL": "\\overline{{{0}}}"}
SUB = "_{{{0}}}"
SUP = "^{{{0}}}"
F = {
    "bar": "\\frac{{{num}}}{{{den}}}",
    "skw": r"^{{{num}}}/_{{{den}}}",
    "noBar": "\\genfrac{{}}{{}}{{0pt}}{{}}{{{num}}}{{{den}}}",
    "lin": "{{{num}}}/{{{den}}}",
}
F_DEFAULT = "\\frac{{{num}}}{{{den}}}"
D = "\\left{left}{text}\\right{right}"
D_DEFAULT = {"left": "(", "right": ")", "null": "."}
RAD = "\\sqrt[{deg}]{{{text}}}"
RAD_DEFAULT = "\\sqrt{{{text}}}"
ARR = "\\begin{{array}}{{c}}{text}\\end{{array}}"
LIM_FUNC = {"lim": "\\lim_{{{lim}}}", "max": "\\max_{{{lim}}}", "min": "\\min_{{{lim}}}"}
LIM_TO = ("\\rightarrow", "\\to")
LIM_UPP = "\\overset{{{lim}}}{{{text}}}"
M = "\\begin{{matrix}}{text}\\end{{matrix}}"


def escape_latex(text: str) -> str:
    last = None
    escaped = []
    for character in text.replace(r"\\", "\\"):
        escaped.append(BACKSLASH + character if character in CHARS and last != BACKSLASH else character)
        last = character
    return BLANK.join(escaped)


def get_val(key, default=None, store=CHR):
    if key is None or not store:
        return default
    return store.get(key, default)


def get_char(key, default=None, store=CHR):
    if key is None:
        return default
    return store.get(key, key) if store else key


class Tag2Method:
    def call_method(self, element, short_tag=None):
        if short_tag is None:
            short_tag = element.tag.replace(OMML_NS, "")
        method = self.tag2meth.get(short_tag)
        return method(self, element) if method else None

    def process_children_list(self, element, include=None):
        for child in list(element):
            if OMML_NS not in child.tag:
                continue
            short_tag = child.tag.replace(OMML_NS, "")
            if include and short_tag not in include:
                continue
            value = self.call_method(child, short_tag=short_tag)
            if value is None:
                value = self.process_unknown(child, short_tag)
                if value is None:
                    continue
            yield short_tag, value, child

    def process_children_dict(self, element, include=None):
        return {short_tag: value for short_tag, value, _ in self.process_children_list(element, include)}

    def process_children(self, element, include=None):
        return BLANK.join(value if not isinstance(value, Tag2Method) else str(value) for _, value, _ in self.process_children_list(element, include))

    def process_unknown(self, element, short_tag):
        return None


class Properties(Tag2Method):
    text = ""
    value_tags = ("chr", "pos", "begChr", "endChr", "type")

    def __init__(self, element):
        self.values = {}
        self.text = self.process_children(element)

    def __str__(self):
        return self.text

    def __getattr__(self, name):
        return self.values.get(name)

    def do_break(self, element):
        self.values["brk"] = BRK
        return BRK

    def do_common(self, element):
        short_tag = element.tag.replace(OMML_NS, "")
        if short_tag in self.value_tags:
            self.values[short_tag] = element.get(f"{OMML_NS}val")
        return None

    tag2meth = {"brk": do_break, "chr": do_common, "pos": do_common, "begChr": do_common, "endChr": do_common, "type": do_common}


class MathToLatex(Tag2Method):
    direct_tags = ("box", "sSub", "sSup", "sSubSup", "num", "den", "deg", "e")

    def __init__(self, element):
        self.value = self.process_children(element)

    def __str__(self):
        return self.value

    def process_unknown(self, element, short_tag):
        if short_tag in self.direct_tags:
            return self.process_children(element)
        if short_tag.endswith("Pr"):
            return Properties(element)
        return None

    def do_accent(self, element):
        values = self.process_children_dict(element)
        template = get_val(values["accPr"].chr, default=CHR_DEFAULT["ACC_VAL"], store=CHR)
        return template.format(values["e"])

    def do_bar(self, element):
        values = self.process_children_dict(element)
        properties = values["barPr"]
        template = get_val(properties.pos, default=POS_DEFAULT["BAR_VAL"], store=POS)
        return properties.text + template.format(values["e"])

    def do_delimiter(self, element):
        values = self.process_children_dict(element)
        properties = values["dPr"]
        left = get_char(properties.begChr, default=D_DEFAULT["left"], store=T)
        right = get_char(properties.endChr, default=D_DEFAULT["right"], store=T)
        return properties.text + D.format(left=D_DEFAULT["null"] if not left else escape_latex(left), text=values["e"], right=D_DEFAULT["null"] if not right else escape_latex(right))

    def do_subscript(self, element):
        return SUB.format(self.process_children(element))

    def do_superscript(self, element):
        return SUP.format(self.process_children(element))

    def do_fraction(self, element):
        values = self.process_children_dict(element)
        properties = values["fPr"]
        template = get_val(properties.type, default=F_DEFAULT, store=F)
        return properties.text + template.format(num=values.get("num"), den=values.get("den"))

    def do_function(self, element):
        values = self.process_children_dict(element)
        return values["fName"].replace(FUNC_PLACE, values.get("e"))

    def do_function_name(self, element):
        values = []
        for short_tag, value, _ in self.process_children_list(element):
            if short_tag == "r":
                if value not in FUNC:
                    raise NotImplementedError(f"Unsupported function {value}")
                values.append(FUNC[value])
            else:
                values.append(value)
        text = BLANK.join(values)
        return text if FUNC_PLACE in text else text + FUNC_PLACE

    def do_group_character(self, element):
        values = self.process_children_dict(element)
        properties = values["groupChrPr"]
        template = get_val(properties.chr, default=CHR_DEFAULT["GROUP_CHR_VAL"], store=CHR)
        return properties.text + template.format(values["e"])

    def do_radical(self, element):
        values = self.process_children_dict(element)
        return RAD.format(deg=values.get("deg"), text=values.get("e")) if values.get("deg") else RAD_DEFAULT.format(text=values.get("e"))

    def do_array(self, element):
        return ARR.format(text=BRK.join(value for _, value, _ in self.process_children_list(element, include=("e",))))

    def do_lower_limit(self, element):
        values = self.process_children_dict(element, include=("e", "lim"))
        template = LIM_FUNC.get(values["e"])
        if not template:
            raise NotImplementedError(f"Unsupported limit {values['e']}")
        return template.format(lim=values.get("lim"))

    def do_upper_limit(self, element):
        values = self.process_children_dict(element, include=("e", "lim"))
        return LIM_UPP.format(lim=values.get("lim"), text=values.get("e"))

    def do_limit(self, element):
        return self.process_children(element).replace(LIM_TO[0], LIM_TO[1])

    def do_matrix(self, element):
        rows = [value for short_tag, value, _ in self.process_children_list(element) if short_tag == "mr"]
        return M.format(text=BRK.join(rows))

    def do_matrix_row(self, element):
        return ALN.join(value for _, value, _ in self.process_children_list(element, include=("e",)))

    def do_nary(self, element):
        values = []
        operator = ""
        for short_tag, value, _ in self.process_children_list(element):
            if short_tag == "naryPr":
                operator = get_char(value.chr, store=CHR_BO)
            else:
                values.append(value)
        return operator + BLANK.join(values)

    def do_run(self, element):
        text = element.findtext(f"./{OMML_NS}t")
        return escape_latex(BLANK.join(T.get(character, character) for character in text))

    tag2meth = {
        "acc": do_accent,
        "r": do_run,
        "bar": do_bar,
        "sub": do_subscript,
        "sup": do_superscript,
        "f": do_fraction,
        "func": do_function,
        "fName": do_function_name,
        "groupChr": do_group_character,
        "d": do_delimiter,
        "rad": do_radical,
        "eqArr": do_array,
        "limLow": do_lower_limit,
        "limUpp": do_upper_limit,
        "lim": do_limit,
        "m": do_matrix,
        "mr": do_matrix_row,
        "nary": do_nary,
    }


MATH_ROOT_TEMPLATE = "".join(
    (
        '<w:document xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" ',
        'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" ',
        'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "{0}</w:document>",
    )
)


def _convert_math(tag: Tag) -> str:
    root = ET.fromstring(MATH_ROOT_TEMPLATE.format(str(tag)))
    element = root.find(OMML_NS + "oMath")
    return MathToLatex(element).value


def _replacement(tag: Tag, block: bool = False) -> Tag:
    text = Tag(name="w:t")
    latex = _convert_math(tag)
    text.string = f"$${latex}$$" if block else f"${latex}$"
    run = Tag(name="w:r")
    run.append(text)
    return run


def _replace_equations(tag: Tag) -> None:
    if tag.name == "oMathPara":
        paragraph = Tag(name="w:p")
        for child in tag.find_all("oMath"):
            paragraph.append(_replacement(child, block=True))
        tag.replace_with(paragraph)
    elif tag.name == "oMath":
        tag.replace_with(_replacement(tag))
    else:
        raise ValueError(f"Unsupported equation tag: {tag.name}")


def _preprocess_xml(content: bytes) -> bytes:
    soup = BeautifulSoup(content.decode(), features="xml")
    for tag in soup.find_all("oMathPara"):
        _replace_equations(tag)
    for tag in soup.find_all("oMath"):
        _replace_equations(tag)
    return str(soup).encode()


def preprocess_docx_equations(input_docx: BinaryIO) -> BytesIO:
    output_docx = BytesIO()
    enabled_files = {"word/document.xml", "word/footnotes.xml", "word/endnotes.xml"}
    with zipfile.ZipFile(input_docx, mode="r") as zip_input:
        files = {name: zip_input.read(name) for name in zip_input.namelist()}
        with zipfile.ZipFile(output_docx, mode="w") as zip_output:
            zip_output.comment = zip_input.comment
            for name, content in files.items():
                if name in enabled_files:
                    try:
                        content = _preprocess_xml(content)
                    except Exception:
                        pass
                zip_output.writestr(name, content)
    output_docx.seek(0)
    return output_docx