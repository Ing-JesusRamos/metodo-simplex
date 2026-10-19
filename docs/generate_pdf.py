"""Genera el PDF 'El método simplex: de la teoría al código con Python'.

Ejecutar desde la carpeta del proyecto:
    python docs/generate_pdf.py
"""

import inspect
import shutil
import sys
import tempfile
from pathlib import Path

from PIL import Image as PillowImage

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from simplex.big_m import (
    BigMSolver,
    _artificial_remains_in_basis,
    _build_canonical_form,
    _build_objective_row,
    _display_objective,
    _perform_pivot,
    _pick_entering_column,
    _ratio_test,
)
from simplex.problem import LPProblem
from simplex.validate import EXAMPLE_PROBLEM
from viz import plots

FONTS_DIR = Path(r"C:\Windows\Fonts")
OUTPUT_PDF = Path(__file__).resolve().parent / "simplex_metodo_explicado.pdf"

NAVY = colors.HexColor("#1b3a5b")
ACCENT = colors.HexColor("#2c7a7b")
CODE_BG = colors.HexColor("#f2f3f5")
TABLE_HEAD_BG = colors.HexColor("#e3e8ee")
ENTERING_BG = colors.HexColor("#fff3b0")
LEAVING_BG = colors.HexColor("#ffd6d6")
PIVOT_BG = colors.HexColor("#a5d6a7")


def register_fonts() -> None:
    pdfmetrics.registerFont(TTFont("SegoeUI", str(FONTS_DIR / "segoeui.ttf")))
    pdfmetrics.registerFont(TTFont("SegoeUI-Bold", str(FONTS_DIR / "segoeuib.ttf")))
    pdfmetrics.registerFont(TTFont("SegoeUI-Italic", str(FONTS_DIR / "segoeuii.ttf")))
    pdfmetrics.registerFont(TTFont("Consolas", str(FONTS_DIR / "consola.ttf")))
    pdfmetrics.registerFont(TTFont("Consolas-Bold", str(FONTS_DIR / "consolab.ttf")))
    pdfmetrics.registerFontFamily(
        "SegoeUI",
        normal="SegoeUI",
        bold="SegoeUI-Bold",
        italic="SegoeUI-Italic",
        boldItalic="SegoeUI-Bold",
    )
    pdfmetrics.registerFontFamily(
        "Consolas",
        normal="Consolas",
        bold="Consolas-Bold",
        italic="Consolas",
        boldItalic="Consolas-Bold",
    )


def build_styles() -> dict[str, ParagraphStyle]:
    def style(name: str, **kwargs) -> ParagraphStyle:
        return ParagraphStyle(name, **kwargs)

    return {
        "PortadaTitle": style(
            "PortadaTitle",
            fontName="SegoeUI-Bold",
            fontSize=26,
            leading=32,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "PortadaSubtitle": style(
            "PortadaSubtitle",
            fontName="SegoeUI",
            fontSize=13,
            leading=18,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceBefore=12,
        ),
        "PortadaFooter": style(
            "PortadaFooter",
            fontName="SegoeUI",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
            spaceBefore=6,
        ),
        "TOCHeading": style(
            "TOCHeading",
            fontName="SegoeUI-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceAfter=10,
        ),
        "Heading1": style(
            "Heading1",
            fontName="SegoeUI-Bold",
            fontSize=16,
            leading=20,
            textColor=NAVY,
            spaceBefore=14,
            spaceAfter=8,
        ),
        "Heading2": style(
            "Heading2",
            fontName="SegoeUI-Bold",
            fontSize=13,
            leading=17,
            textColor=ACCENT,
            spaceBefore=10,
            spaceAfter=5,
        ),
        "Heading3": style(
            "Heading3",
            fontName="SegoeUI-Italic",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#444444"),
            spaceBefore=8,
            spaceAfter=4,
        ),
        "Body": style(
            "Body",
            fontName="SegoeUI",
            fontSize=10,
            leading=14.5,
            spaceAfter=6,
            alignment=TA_JUSTIFY,
        ),
        "Bullet": style(
            "Bullet",
            fontName="SegoeUI",
            fontSize=10,
            leading=14.5,
            spaceAfter=3,
            leftIndent=12,
            bulletIndent=2,
        ),
        "Formula": style(
            "Formula",
            fontName="Consolas",
            fontSize=9.5,
            leading=13,
            spaceBefore=3,
            spaceAfter=6,
            textColor=NAVY,
            alignment=TA_CENTER,
        ),
        "Code": style(
            "Code",
            fontName="Consolas",
            fontSize=8,
            leading=10.5,
            spaceBefore=4,
            spaceAfter=2,
            backColor=CODE_BG,
            borderPadding=6,
            leftIndent=6,
            rightIndent=6,
        ),
        "CodeNote": style(
            "CodeNote",
            fontName="SegoeUI-Italic",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#555555"),
            spaceAfter=6,
            leftIndent=6,
        ),
        "Caption": style(
            "Caption",
            fontName="SegoeUI-Italic",
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#555555"),
            alignment=TA_CENTER,
            spaceBefore=2,
            spaceAfter=8,
        ),
        "FigureNote": style(
            "FigureNote",
            fontName="SegoeUI",
            fontSize=9.5,
            leading=13.5,
            spaceBefore=4,
            spaceAfter=8,
            alignment=TA_JUSTIFY,
        ),
    }


def esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def fmt(value: float) -> str:
    if value is None:
        return "—"
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.5g}"


def src(func) -> str:
    return inspect.getsource(func).rstrip()


def trim_source(source: str, start_marker: str, end_marker: str) -> str:
    lines = source.splitlines()
    start_indexes = [i for i, line in enumerate(lines) if start_marker in line]
    if not start_indexes:
        return source
    start = start_indexes[0]
    end_indexes = [i for i, line in enumerate(lines) if end_marker in line and i > start]
    if not end_indexes:
        return source
    return "\n".join(lines[start:end_indexes[0] + 1])


# ------------------------------------------------------------------ tableau
def build_tableau_rows(step) -> tuple[list[list[str]], bool]:
    has_ratio = step.kind == "iterate"
    header = [" "] + list(step.column_labels) + ["b"]
    if has_ratio:
        header.append("b/a")
    rows = [header]
    for row_index in range(step.matrix.shape[0] - 1):
        row = [step.basis_names[row_index]]
        row.extend(fmt(value) for value in step.matrix[row_index, :-1])
        row.append(fmt(step.matrix[row_index, -1]))
        if has_ratio:
            ratio = step.ratios[row_index] if row_index < len(step.ratios) else None
            row.append(fmt(ratio))
        rows.append(row)
    objective_row = ["Z"]
    objective_row.extend(fmt(value) for value in step.reduced_costs)
    objective_row.append(fmt(step.objective_value))
    if has_ratio:
        objective_row.append("")
    rows.append(objective_row)
    return rows, has_ratio


def tableau(step) -> Table:
    rows, has_ratio = build_tableau_rows(step)
    num_columns = len(rows[0])
    widths = [max(len(rows[row][column]) for row in range(len(rows))) * 4.6
              for column in range(num_columns)]
    table = Table(rows, colWidths=widths, hAlign="CENTER")
    style_cmds = [
        ("FONTNAME", (0, 0), (-1, -1), "Consolas", 8),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
        ("BACKGROUND", (0, 0), (-1, 0), TABLE_HEAD_BG),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#c9d2da")),
        ("INNERGRID", (0, 0), (-1, -1), 0.2, colors.HexColor("#d7dde3")),
    ]
    last_row = len(rows) - 1
    if step.pivot_col is not None:
        column = step.pivot_col + 1
        style_cmds.append(("BACKGROUND", (column, 1), (column, last_row - 1), ENTERING_BG))
    if step.pivot_row is not None:
        row = step.pivot_row + 1
        style_cmds.append(("BACKGROUND", (0, row), (num_columns - 1, row), LEAVING_BG))
    if step.pivot_col is not None and step.pivot_row is not None:
        style_cmds.append(("BACKGROUND", (step.pivot_col + 1, step.pivot_row + 1),
                           (step.pivot_col + 1, step.pivot_row + 1), PIVOT_BG))
    style_cmds.append(("FONTNAME", (0, last_row), (-1, last_row), "Consolas-Bold", 8))
    style_cmds.append(("TEXTCOLOR", (0, last_row), (-1, last_row), NAVY))
    table.setStyle(TableStyle(style_cmds))
    return table


def ratio_text(step) -> str:
    if step.kind != "iterate" or step.entering is None or step.leaving is None:
        return ""
    lines = []
    for basis_name, ratio, row_index in zip(step.basis_names, step.ratios, range(len(step.ratios))):
        if ratio is None:
            lines.append(f"{basis_name}: coeficiente ≤ 0, no limita")
        else:
            rhs_value = step.matrix[row_index, -1]
            coeff = step.matrix[row_index, _label_index(step, step.entering)]
            lines.append(f"{basis_name}: {fmt(rhs_value)} / {fmt(coeff)} = {fmt(ratio)}")
    minimum = fmt(min(r for r in step.ratios if r is not None))
    return "   ".join(lines) + f"   → sale {step.leaving} (cociente mínimo {minimum})"


def _label_index(step, name: str) -> int:
    return list(step.column_labels).index(name)


# ------------------------------------------------------------------ images
def make_images(result, temp_dir: Path) -> tuple[tuple[str, float, float], tuple[str, float, float]]:
    def save_figure(figure, name: str) -> tuple[str, float, float]:
        path = temp_dir / name
        figure.savefig(str(path), dpi=150)
        width_px, height_px = PillowImage.open(path).size
        return str(path), width_px / height_px

    region = save_figure(
        plots.feasible_region_figure(EXAMPLE_PROBLEM, result.solution, result.status),
        "region.png",
    )
    progress = save_figure(plots.objective_progress_figure(result), "progress.png")
    return region, progress


def embedded_image(info: tuple[str, float, float], target_width_cm: float) -> Image:
    path, aspect = info
    return Image(path, width=target_width_cm * cm, height=target_width_cm / aspect * cm)


# ------------------------------------------------------------------ doc class
class SimplexDoc(BaseDocTemplate):
    def __init__(self, filename, **kwargs):
        super().__init__(filename, **kwargs)
        self.toc = TableOfContents()

    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph):
            style_name = flowable.style.name
            if style_name in ("Heading1", "Heading2"):
                level = 0 if style_name == "Heading1" else 1
                self.notify("TOCEntry", (level, flowable.getPlainText(), self.page))


def draw_page(canvas, doc) -> None:
    canvas.saveState()
    page = canvas.getPageNumber()
    if page > 1:
        canvas.setFont("SegoeUI", 8)
        canvas.setFillColor(colors.HexColor("#777777"))
        canvas.drawString(2 * cm, 1.1 * cm, "Método simplex: de la teoría al código con Python")
        canvas.drawRightString(A4[0] - 2 * cm, 1.1 * cm, f"Página {page}")
        canvas.setStrokeColor(colors.HexColor("#c9d2da"))
        canvas.line(2 * cm, 1.4 * cm, A4[0] - 2 * cm, 1.4 * cm)
    canvas.restoreState()


def make_doc() -> SimplexDoc:
    doc = SimplexDoc(
        str(OUTPUT_PDF),
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title="El método simplex: de la teoría al código con Python",
        author="Proyecto metodo-simplex",
    )
    frame = Frame(
        doc.leftMargin,
        doc.bottomMargin,
        doc.width,
        doc.height,
        leftPadding=0,
        rightPadding=0,
        topPadding=0,
        bottomPadding=0,
    )
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=draw_page)])
    return doc


# ============================================================ content builders
def build_portada(story: list) -> None:
    story.append(Spacer(1, 5.2 * cm))
    story.append(Paragraph("El método simplex", styles["PortadaTitle"]))
    story.append(Paragraph("de la teoría al código con Python", styles["PortadaTitle"]))
    story.append(Spacer(1, 1.2 * cm))
    story.append(Paragraph(
        "Maximización y minimización, restricciones con ≤, ≥ y =, la técnica Big-M "
        "y cada paso del algoritmo traducido al código real del proyecto",
        styles["PortadaSubtitle"],
    ))
    story.append(Spacer(1, 2.4 * cm))
    story.append(Paragraph("Proyecto metodo-simplex — aplicación de escritorio (Tkinter)", styles["PortadaFooter"]))
    story.append(PageBreak())


def build_toc(story: list) -> None:
    story.append(Paragraph("Contenido", styles["TOCHeading"]))
    story.append(doc.toc)
    story.append(PageBreak())


def build_chapter_1(story: list) -> None:
    story.append(Paragraph("1. El problema que resuelve el método", styles["Heading1"]))
    story.append(Paragraph(
        "Un problema de <b>programación lineal</b> pide optimizar (maximizar o minimizar) una "
        "<i>función objetivo</i> lineal Z = c₁·x₁ + c₂·x₂ + … + cₙ·xₙ, sujeta a un conjunto de "
        "<i>restricciones</i> lineales y a que las variables de decisión sean no negativas:",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Maximizar   Z = 3·x₁ + 2·x₂<br/>"
        "sujeto a    x₁ + x₂ ≤ 4<br/>"
        "            2·x₁ + x₂ ≤ 5<br/>"
        "            x₁, x₂ ≥ 0",
        styles["Formula"],
    ))
    story.append(Paragraph(
        "Este formato se llama <b>forma general</b>. En el proyecto ese modelo se escribe con una "
        "<i>dataclass</i> de Python, una de las facilidades que usamos y que veremos en detalle en el capítulo 9:",
        styles["Body"],
    ))
    story.append(Preformatted(src(LPProblem), styles["Code"]))
    story.append(Paragraph(
        "La dataclass declara <i>qué es</i> un problema, no <i>cómo</i> se resuelve. Con "
        "<b>frozen=True</b> la hacemos inmutable: un problema no puede mutarse a mitad de la "
        "resolución, lo que evita errores sutiles al pivotar. Cada restricción guarda sus "
        "coeficientes, la relación (≤, ≥, =) y el término independiente. El método simplex "
        "toma esta estructura y hace lo que describimos a continuación.",
        styles["Body"],
    ))


def build_chapter_2(story: list) -> None:
    story.append(Paragraph("2. La idea geométrica: de esquina en esquina", styles["Heading1"]))
    story.append(Paragraph(
        "Cada restricción corta el plano en dos: un lado permitido y otro prohibido. La "
        "intersección de todos los lados permitidos (incluyendo x ≥ 0) es la <b>región factible</b>, "
        "que siempre es un polígono convexo. Los <b>vértices</b> (esquinas) son los puntos donde "
        "varias restricciones se cumplen con igualdad.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Una propiedad fundamental de la programación lineal dice que si existe una solución "
        "óptima, hay una en algún <b>vértice</b>. El simplex explota esa propiedad: en vez de "
        "probar puntos al azar, <b>visita vértices vecinos de uno en uno, mejorando Z en cada paso</b>, "
        "y se detiene cuando ningún vecino mejora la solución.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Concretamente el método opera sobre una <b>tabla simplex</b> (tableau), una hoja de "
        "cálculo donde cada fila es una ecuación y cada columna una variable. De un vértice a "
        "otro se pasa con un <b>pivote</b>: una variable <b>entra</b> a la base (deja de valer 0) "
        "y otra <b>sale</b>. La base es el conjunto de variables activas que definen el vértice actual.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "El código del proyecto guarda esa lógica en variables con nombre —<i>entering</i>, "
        "<i>leaving</i>, <i>pivot_row</i>, <i>pivot_col</i>— y <b>registra cada iteración como un paso</b> "
        "para poder mostrarla y explicarla en la aplicación:",
        styles["Body"],
    ))
    story.append(Preformatted(
        "@dataclass\n"
        "class SimplexStep:\n"
        "    kind: str          # 'build' | 'iterate' | 'optimal' | 'unbounded' | 'infeasible'\n"
        "    matrix: ...        # tabla simplex completa\n"
        "    entering: str | None\n"
        "    leaving: str | None\n"
        "    pivot_row: int | None\n"
        "    pivot_col: int | None\n"
        "    ratios: tuple[float | None, ...]\n"
        "    ...",
        styles["Code"],
    ))
    story.append(Paragraph(
        "Esta estructura es lo que alimenta la pestaña 'Paso a paso' de la interfaz: el tableau, "
        "el cociente mínimo y el intercambio de variables de cada vértice visitado.",
        styles["Body"],
    ))


def build_chapter_3(story: list) -> None:
    story.append(Paragraph("3. Forma estándar: holguras, superávit y Big-M", styles["Heading1"]))
    story.append(Paragraph(
        "La tabla simplex solo sabe de <i>ecuaciones</i> (=), no de desigualdades. Por eso el primer "
        "paso es convertir cada restricción en una igualdad agregando variables auxiliares:",
        styles["Body"],
    ))
    story.append(Paragraph(
        "• x₁ + x₂ ≤ 4   →   x₁ + x₂ + s₁ = 4      (s₁ = holgura, mide lo que sobra, costo 0)<br/>"
        "• x₁ + x₂ ≥ 3   →   x₁ + x₂ − e₁ + a₁ = 3  (e₁ = superávit, costo 0; a₁ = artificial)<br/>"
        "• x₁ + x₂ = 5   →   x₁ + x₂ + a₂ = 5       (a₂ = artificial)",
        styles["Formula"],
    ))
    story.append(Paragraph(
        "Holguras y superávits son variables honestas: representan 'cuánto sobra' o 'cuánto se pasa'. "
        "Las <b>artificiales</b> son un truco de la técnica <b>Big-M</b>: se agregan solo para que "
        "las filas ≥ y = tengan una variable natural con la que empezar la base (una columna "
        "unitaria de identidad). Para expulsarlas, llevan un costo enorme M en el objetivo, tan grande "
        "que el método las saca de la base solas en cuanto puede.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "El código hace exactamente esto en <b>_build_canonical_form</b>. Lo esencial es el bucle "
        "que recorre las restricciones y coloca 1, −1 o 1 según la relación:",
        styles["Body"],
    ))
    story.append(Preformatted(trim_source(
        src(_build_canonical_form),
        "for row, constraint in enumerate(problem.constraints):",
        "artificial_count += 1",
    ), styles["Code"]))
    story.append(Paragraph(
        "Observa que la <b>base inicial</b> queda formada por holguras (en ≤) y artificiales "
        "(en ≥ y =). El costo −M de las artificiales se define en la línea "
        "<font name='Consolas' size='8.5'>costs[...] = -big_m</font>, y el valor numérico de M se "
        "calcula con una heurística basada en la magnitud de los datos (capítulo 9).",
        styles["Body"],
    ))


def build_chapter_4(story: list) -> None:
    story.append(Paragraph("4. La fila de costos reducidos (cⱼ − zⱼ)", styles["Heading1"]))
    story.append(Paragraph(
        "Para saber si conviene traer una variable a la base, el método calcula, para cada variable "
        "no básica xⱼ, cuánto cambiaría Z si metiéramos una unidad de xⱼ. Eso es el <b>costo reducido</b> "
        "cⱼ − zⱼ:",
        styles["Body"],
    ))
    story.append(Paragraph(
        "zⱼ = c_B · (columna j)      → costo 'oculto' de xⱼ por las variables básicas que desplaza<br/>"
        "cⱼ − zⱼ                      → beneficio neto por unidad de xⱼ<br/>"
        "En maximización: si cⱼ − zⱼ > 0, xⱼ mejora Z → candidata a entrar.",
        styles["Formula"],
    ))
    story.append(Paragraph(
        "El código lo implementa en tres líneas gracias al <b>producto punto de NumPy</b> "
        "(el @ multiplica matrices y vectores completos a la vez):",
        styles["Body"],
    ))
    story.append(Preformatted(src(_build_objective_row), styles["Code"]))
    story.append(Paragraph(
        "Internamente la fila se guarda como zⱼ − cⱼ: así el criterio de parada es natural "
        "(óptimo cuando todos los valores son ≥ 0). Al mostrar al usuario la negamos para que "
        "se lea como cⱼ − zⱼ, la forma clásica de los libros:",
        styles["Body"],
    ))
    story.append(Preformatted("reduced_costs = tuple(-(objective_row))", styles["Code"]))


def build_chapter_5(story: list) -> None:
    story.append(Paragraph("5. El ciclo: escoje, cociente y pivote", styles["Heading1"]))
    story.append(Paragraph(
        "El bucle del simplex repite tres decisiones hasta no poder mejorar:",
        styles["Body"],
    ))
    story.append(Paragraph("5.1 Variable que entra", styles["Heading2"]))
    story.append(Paragraph(
        "Entre las no básicas, se elige la de mejor costo reducido. Como trabajamos con la fila "
        "zⱼ − cⱼ, 'mejor' significa el valor <b>más negativo</b>. Si ninguna es negativa, estamos "
        "en el óptimo. El código excluye primero las variables básicas (por ruido numérico puede "
        "aparecer un −0.0000000001) y, entre empates, gana el índice más pequeño: la <b>regla de "
        "Bland</b>, que evita ciclos infinitos en problemas degenerados.",
        styles["Body"],
    ))
    story.append(Preformatted(src(_pick_entering_column), styles["Code"]))
    story.append(Paragraph("5.2 El que sale: test del cociente", styles["Heading2"]))
    story.append(Paragraph(
        "No basta con elegir quién entra; hay que saber quién sale para que el nuevo vértice siga "
        "siendo factible. Para cada fila con coeficiente positivo en la columna entrante, se divide "
        "<i>el lado derecho entre ese coeficiente</i>; el mínimo de esos cocientes es la restricción "
        "que se agota primero, y esa es la fila que debe salir. Si <b>ninguna</b> fila tiene "
        "coeficiente positivo, xⱼ puede crecer sin límite y el problema es <b>no acotado</b>.",
        styles["Body"],
    ))
    story.append(Preformatted(src(_ratio_test), styles["Code"]))
    story.append(Paragraph("5.3 El pivote (eliminación de Gauss-Jordan)", styles["Heading2"]))
    story.append(Paragraph(
        "El pivote normaliza la fila elegida y la usa para limpiar su columna en todas las demás "
        "filas, <b>incluida la del objetivo</b>. Como la fila del objetivo participa del pivote, "
        "el valor de Z en la última columna se actualiza solo, sin recalcular nada aparte.",
        styles["Body"],
    ))
    story.append(Preformatted(src(_perform_pivot), styles["Code"]))
    story.append(Paragraph("5.4 El bucle que lo coordina", styles["Heading2"]))
    story.append(Paragraph(
        "Todo esto se coordina en solve() con un bucle de hasta MAX_PIVOTS pasadas (cortafuegos "
        "contra un ciclo degenerado casi imposible). Cada iteración se guarda con su tableau, "
        "ratios y pivote para mostrarlos después:",
        styles["Body"],
    ))
    story.append(Preformatted(trim_source(src(BigMSolver.solve),
                                           "for _ in range(MAX_PIVOTS):",
                                           "num_pivots += 1"),
                              styles["Code"]))


def build_chapter_6(story: list) -> None:
    story.append(Paragraph("6. Cómo decide el método que terminó", styles["Heading1"]))
    story.append(Paragraph(
        "El simplex siempre llega a un estado donde ninguna variable no básica mejora la solución, "
        "pero eso no siempre significa éxito. Hay tres desenlaces posibles:",
        styles["Body"],
    ))
    story.append(Paragraph(
        "• <b>Óptimo:</b> ningún costo reducido es favorable (todo zⱼ − cⱼ ≥ 0). El valor de la última "
        "celda es el Z óptimo.<br/>"
        "• <b>No acotado:</b> hay variable entrante, pero ninguna fila la limita (el cociente no existe).<br/>"
        "• <b>Infactible:</b> terminó con una variable artificial todavía en la base y con valor positivo.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "El caso infactible es la sutileza real del Big-M: la técnica artificial funciona, pero si "
        "las restricciones son contradictorias, la artificial 'no tiene salida' y queda en la base. "
        "Por eso la señal no es la presencia de la artificial, sino su valor:",
        styles["Body"],
    ))
    story.append(Preformatted(src(_artificial_remains_in_basis), styles["Code"]))
    story.append(Paragraph(
        "El 1e-6 indica 'valor efectivamente distinto de cero': si la artificial quedó con valor 0, "
        "la restricción se cumple al límite (degeneración legítima) y el problema sí es factible.",
        styles["Body"],
    ))


def build_chapter_7(story: list) -> None:
    story.append(Paragraph("7. Minimización sin reescribir el método", styles["Heading1"]))
    story.append(Paragraph(
        "El simplex descrito maximiza. Pero minimizar Z es lo mismo que maximizar −Z, así que el "
        "programa niega el vector de costos c de la función objetivo y resuelve un problema máximo "
        "equivalente. Al reportar el resultado, vuelve a negar el valor interno para entregar el Z "
        "de tu problema original.",
        styles["Body"],
    ))
    story.append(Preformatted(
        "costs_max = np.array(problem.objective_coeffs, dtype=float)\n"
        "if problem.objective_sense == 'min':\n"
        "    costs_max = -costs_max    # minimizar Z == maximizar -Z",
        styles["Code"],
    ))
    story.append(Preformatted(src(_display_objective), styles["Code"]))


def build_chapter_8(story: list) -> None:
    story.append(Paragraph("8. Ejemplo numérico completo", styles["Heading1"]))
    story.append(Paragraph(
        "Resolvamos con nuestro propio código el problema de la portada: "
        "<b>maximizar Z = 3·x₁ + 2·x₂</b> con x₁ + x₂ ≤ 4 y 2·x₁ + x₂ ≤ 5, x ≥ 0.",
        styles["Body"],
    ))
    story.append(Paragraph(
        "Las cifras de este capítulo no están escritas a mano: se generan ejecutando BigMSolver "
        "en vivo mientras se crea el PDF. Lo que ves abajo es la salida real del algoritmo.",
        styles["CodeNote"],
    ))

    result = BigMSolver(EXAMPLE_PROBLEM).solve()
    build = result.steps[0]
    iter_one = result.steps[1]
    iter_two = result.steps[2]
    final = result.steps[-1]

    story.append(Paragraph("8.1 Paso 0 — la tabla inicial", styles["Heading2"]))
    story.append(Paragraph(
        "El programa convierte cada ≤ en igualdad con su holgura (s₁ y s₂) y arma el tableau "
        "inicial. La última fila muestra los costos reducidos cⱼ − zⱼ; la base inicial es (s₁, s₂) "
        "con Z = 0. La columna del lado derecho (b) son los términos independientes.",
        styles["Body"],
    ))
    story.append(tableau(build))
    story.append(Paragraph(
        "En la fila de costos reducidos hay valores positivos (3 para x₁ y 2 para x₂): hay espacio "
        "para mejorar, así que el ciclo arranca.",
        styles["Body"],
    ))

    story.append(Paragraph("8.2 Iteración 1 — entra x₁", styles["Heading2"]))
    story.append(Paragraph(
        "x₁ tiene el costo reducido más alto (3): cada unidad que entra sube Z en 3. ¿Qué restricción "
        "lo limita? Aplicamos el test del cociente con la columna de x₁:",
        styles["Body"],
    ))
    story.append(Paragraph(ratio_text(iter_one), styles["Formula"]))
    story.append(Paragraph(
        "s₂ da el cociente mínimo (2.5), así que s₂ sale de la base y x₁ entra. El pivote es el "
        "elemento (fila s₂, columna x₁) = 2. Tras el pivote, la base pasa a ser (s₁, x₁):",
        styles["Body"],
    ))
    story.append(tableau(iter_two))
    story.append(Paragraph(
        "Ahora x₁ vale 2.5 (su lado derecho) y Z subió a 7.5. Pero la fila de costos reducidos "
        "todavía tiene un valor positivo (0.5 en x₂), así que podemos mejorar de nuevo.",
        styles["Body"],
    ))

    story.append(Paragraph("8.3 Iteración 2 — entra x₂", styles["Heading2"]))
    story.append(Paragraph(
        "Sobre la tabla nueva, entra x₂ (costo reducido +0.5). El cociente da 3 en s₁ y 5 en la fila "
        "de x₁, así que sale s₁; el pivote es 0.5.",
        styles["Body"],
    ))
    story.append(Paragraph(ratio_text(iter_two), styles["Formula"]))
    story.append(tableau(final))
    story.append(Paragraph(
        "La fila de costos reducidos ya no tiene valores positivos: <b>óptimo alcanzado</b>. "
        "Solución: x₁ = 1, x₂ = 3, con Z = 9. Comprobación: 1 + 3 = 4 (límite justo) y 2·1 + 3 = 5 "
        "(límite justo).",
        styles["Body"],
    ))

    story.append(Paragraph("8.4 En gráficas", styles["Heading2"]))
    story.append(Paragraph(
        "La región factible de este problema es el polígono con vértices (0,0), (2.5,0), (1,3) y "
        "(0,4). La línea de nivel de Z = 9 (más intensa) es la última que toca la región, en el "
        "vértice (1,3):",
        styles["Body"],
    ))
    story.append(embedded_image(region_image, 13.5))
    story.append(Paragraph("Región factible con el óptimo en rojo y la flecha de mejora.", styles["Caption"]))
    story.append(paragraph_note_if_not_infeasible(result))
    story.append(embedded_image(progress_image, 13.0))
    story.append(Paragraph(
        "Z nunca baja: en maximización cada iteración mejora (o iguala) la solución hasta converger "
        "a 9.",
        styles["Caption"],
    ))


def paragraph_note_if_not_infeasible(result):
    note = (
        "Nota: como el método caminó (0,0) → (2.5,0) → (1,3), el progreso de Z fue 0 → 7.5 → 9, "
        "monótono creciente."
    )
    return Paragraph(note, styles["FigureNote"])


def build_chapter_9(story: list) -> None:
    story.append(Paragraph("9. Las facilidades de Python que hicieron esto simple", styles["Heading1"]))
    story.append(Paragraph(
        "Vale la pena cerrar con el inventario de por qué escribir este método en Python (con "
        "NumPy) es notablemente más corto que en un lenguaje clásico:",
        styles["Body"],
    ))
    story.extend(build_facilities_content())


def build_facilities_content() -> list:
    items: list = []
    items.extend(paragraph_bullet(
        "dataclass — el modelo.",
        "Con <b>@dataclass</b> el problema, cada paso y el resultado se declaran en pocas líneas "
        "con tipos legibles (str | None) en vez de escribir getters, constructores y __repr__ a mano.",
        "from dataclasses import dataclass\n"
        "@dataclass\n"
        "class SimplexStep:\n"
        "    kind: str\n"
        "    entering: str | None",
    ))
    items.extend(paragraph_bullet(
        "Lectura de la fila objetivo como suma de productos.",
        "zⱼ = c_B · columnaⱼ es un producto punto; NumPy lo calcula para todas las columnas a la vez "
        "con @.",
        "implied_costs = basic_costs @ canonical.matrix",
    ))
    items.extend(paragraph_bullet(
        "Slicing del tableau.",
        "Con tableau[-1, :-1] se extrae la fila objetivo sin la última columna, y con matrix[row, -1] "
        "el lado derecho de cada fila. Sin bucles manuales.",
        "objective_row = tableau[-1, :-1]",
    ))
    items.extend(paragraph_bullet(
        "Operaciones por fila completas.",
        "Dividir una fila entre el pivote o restarle un múltiplo de otra es una línea porque NumPy "
        "opera sobre el vector completo.",
        "matrix[row] = matrix[row] - factor * matrix[other_row]",
    ))
    items.extend(paragraph_bullet(
        "min con key y tuplas (regla de Bland).",
        "Elegir el mejor candidato y al mismo tiempo desempatar por índice es una sola llamada:",
        "min(candidates, key=lambda i: (objective_row[i], i))",
    ))
    items.extend(paragraph_bullet(
        "Tolerancias para el punto flotante.",
        "Los ceros calculados suelen salir como 1e-17. Constantes con nombre distinguen 'es cero' "
        "(1e-9) de 'la artificial vale de verdad' (1e-6):",
        "NEGLIGIBLE = 1e-9\nINFEASIBLE_TOLERANCE = 1e-6",
    ))
    items.extend(paragraph_bullet(
        "copy() para la trazabilidad.",
        "Cada paso guarda matrix=tableau.copy() para que el pivote siguiente no corrompa la historia "
        "mostrada al usuario.",
        "matrix=tableau.copy()",
    ))
    items.extend(paragraph_bullet(
        "Listas por comprensión y f-strings para las etiquetas.",
        "Generar los nombres x1…xn, s1…, e1…, a1… es una expresión:",
        "labels = variable_labels + slack_labels + surplus_labels + artificial_labels_list",
    ))
    items.extend(paragraph_bullet(
        "Listas por comprensión para contar.",
        "Contar cuántas columnas de cada tipo se necesitan sin un solo if:",
        "slack_columns = sum(c.relation == '<=' for c in problem.constraints)",
    ))
    items.extend(paragraph_bullet(
        "La heurística de M.",
        "El valor de Big-M se deriva de los propios datos para que siempre domine a los costos reales:",
        "M = 1 + sum(abs(c)) + sum(abs(b)) + max(sum(abs(fila de A)))",
    ))
    return items


def paragraph_bullet(title: str, body: str, code: str):
    flowables = [
        Paragraph(f"<b>{title}</b> {body}", styles["Bullet"]),
        Preformatted(code, styles["Code"]),
    ]
    return flowables


def build_chapter_10(story: list) -> None:
    story.append(Paragraph("10. Para cerrar: cómo usar el proyecto", styles["Heading1"]))
    story.append(Paragraph(
        "La lógica de este documento vive en la carpeta <b>simplex/</b> del proyecto, separada de "
        "la interfaz:",
        styles["Body"],
    ))
    story.append(Preformatted(
        "simplex/problem.py   el modelo LPProblem\n"
        "simplex/validate.py  validación de entrada\n"
        "simplex/big_m.py     el algoritmo de este documento\n"
        "explain/             glosario y textos de explicación\n"
        "viz/plots.py         las gráficas\n"
        "gui/                 la interfaz Tkinter",
        styles["Code"],
    ))
    story.append(Paragraph(
        "Para probarlo tú mismo:",
        styles["Body"],
    ))
    story.append(Paragraph(
        "• <font name='Consolas' size='8.5'>pip install -r requirements.txt</font> — instala "
        "numpy y matplotlib.<br/>"
        "• <font name='Consolas' size='8.5'>python main.py</font> — abre la aplicación; eliges "
        "max/min, escribes las restricciones con ≤, ≥ o =, y cada iteración aparece con su tabla "
        "y su explicación.<br/>"
        "• <font name='Consolas' size='8.5'>python tests/test_simplex.py</font> — ejecuta las "
        "pruebas del algoritmo (el proyecto se validó contra scipy en más de 100 problemas aleatorios).",
        styles["Body"],
    ))
    story.append(Paragraph(
        "En la interfaz, la pestaña 'Paso a paso' muestra exactamente lo que se calcula en los "
        "capítulos 5 y 8: qué variable entra, el test del cociente con sus números reales, el "
        "pivote resaltado, y por qué se llega al óptimo.",
        styles["Body"],
    ))


def build_final_note(story: list) -> None:
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "Este documento se generó con el propio script docs/generate_pdf.py usando ReportLab, "
        "ejecutando el algoritmo real para producir los números del ejemplo.",
        styles["PortadaFooter"],
    ))


def main() -> None:
    global doc, styles, region_image, progress_image
    register_fonts()
    styles = build_styles()

    temp_dir = Path(tempfile.mkdtemp(prefix="simplex_pdf_"))
    try:
        result = BigMSolver(EXAMPLE_PROBLEM).solve()
        region_image, progress_image = make_images(result, temp_dir)

        doc = make_doc()
        story: list = []
        build_portada(story)
        build_toc(story)
        build_chapter_1(story)
        build_chapter_2(story)
        build_chapter_3(story)
        build_chapter_4(story)
        build_chapter_5(story)
        build_chapter_6(story)
        build_chapter_7(story)
        build_chapter_8(story)
        build_chapter_9(story)
        build_chapter_10(story)
        build_final_note(story)

        doc.multiBuild(story)
        print(f"PDF generado: {OUTPUT_PDF}  ({doc.page} paginas, {OUTPUT_PDF.stat().st_size} bytes)")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    main()