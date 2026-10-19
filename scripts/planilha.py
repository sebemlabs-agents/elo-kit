#!/usr/bin/env python3
"""Le qualquer planilha CSV ou XLSX e descreve o que tem dentro.

Nao assume formato nenhum. Nao exige modelo. Le o arquivo que a pessoa tem e
devolve as colunas, os tipos e exemplos reais — para quem esta lendo decidir o
que e o que. Padronizar export de marketplace e briga perdida: cada um exporta
de um jeito, e o mapeamento e trabalho de quem entende a planilha.

Uso:
    python3 planilha.py vendas.xlsx              descreve o arquivo
    python3 planilha.py vendas.csv --linhas 5    mostra mais exemplos
    python3 planilha.py vendas.xlsx --aba 2      outra aba
    python3 planilha.py vendas.xlsx --json       saida para ler por programa

Nao depende de nada instalado: XLSX e um zip de XML, e a biblioteca padrao do
Python abre os dois.

Compatibilidade: Python 3.8+.
"""
import csv
import datetime as dt
import io
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree

BASE = Path(__file__).resolve().parent
EXEMPLOS = 3

# Formatos de numero que o Excel usa para data. Os 14-22 e 45-47 sao fixos.
FORMATOS_DE_DATA = set(range(14, 23)) | set(range(45, 48))
BASE_EXCEL = dt.datetime(1899, 12, 30)


class PlanilhaIlegivel(RuntimeError):
    """O arquivo existe mas nao deu para ler como planilha."""


# --------------------------------------------------------------------- comum

def _sem_ns(tag):
    return tag.split("}", 1)[-1]


def coluna_para_indice(ref):
    """'BC12' -> 54. Letra de coluna do Excel para posicao."""
    letras = re.match(r"([A-Z]+)", str(ref or "").upper())
    if not letras:
        return None
    n = 0
    for c in letras.group(1):
        n = n * 26 + (ord(c) - 64)
    return n - 1


def numero_br(texto):
    """'1.234,56' e '1,234.56' viram 1234.56. Texto que nao e numero volta None."""
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    t = re.sub(r"[R$\s ]", "", t)
    negativo = t.startswith("(") and t.endswith(")")
    if negativo:
        t = t[1:-1]
    if not re.match(r"^-?[\d.,]+$", t):
        return None
    if "," in t and "." in t:
        # o separador decimal e o que vem por ultimo
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(".", "").replace(",", ".")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if negativo else v


def _converter(texto):
    """Texto cru -> numero, data ISO ou o proprio texto. Nunca inventa."""
    if texto is None:
        return None
    t = str(texto).strip()
    if not t:
        return None
    n = numero_br(t)
    if n is not None:
        return int(n) if n == int(n) and "." not in t and "," not in t else n
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            return dt.datetime.strptime(t[:10], formato).date().isoformat()
        except ValueError:
            pass
    return t


# ----------------------------------------------------------------------- csv

def _abrir_texto(caminho):
    """Export brasileiro vem em utf-8, utf-8 com marca, ou latin-1."""
    bruto = Path(caminho).read_bytes()
    for codec in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return bruto.decode(codec), codec
        except UnicodeDecodeError:
            continue
    raise PlanilhaIlegivel("não consegui ler o texto deste arquivo")


def ler_csv(caminho):
    texto, codec = _abrir_texto(caminho)
    amostra = texto[:8000]
    try:
        dialeto = csv.Sniffer().sniff(amostra, delimiters=";,\t|")
        separador = dialeto.delimiter
    except csv.Error:
        separador = ";" if amostra.count(";") > amostra.count(",") else ","

    leitor = csv.reader(io.StringIO(texto), delimiter=separador)
    linhas = [l for l in leitor if any((c or "").strip() for c in l)]
    if not linhas:
        raise PlanilhaIlegivel("o arquivo está vazio")
    return linhas, {"separador": separador, "codificacao": codec}


# ---------------------------------------------------------------------- xlsx

def _strings_compartilhadas(z):
    try:
        raiz = ElementTree.fromstring(z.read("xl/sharedStrings.xml"))
    except KeyError:
        return []
    saida = []
    for si in raiz:
        pedacos = [n.text or "" for n in si.iter() if _sem_ns(n.tag) == "t"]
        saida.append("".join(pedacos))
    return saida


def _estilos_de_data(z):
    """Indice do estilo -> True quando o formato e de data."""
    try:
        raiz = ElementTree.fromstring(z.read("xl/styles.xml"))
    except KeyError:
        return {}
    personalizados = {}
    for n in raiz.iter():
        if _sem_ns(n.tag) == "numFmt":
            codigo = (n.get("formatCode") or "").lower()
            # tira o que esta entre aspas antes de procurar y/m/d
            limpo = re.sub(r'"[^"]*"', "", codigo)
            if re.search(r"[ymd]", limpo):
                personalizados[int(n.get("numFmtId"))] = True
    saida = {}
    for n in raiz.iter():
        if _sem_ns(n.tag) != "cellXfs":
            continue
        for i, xf in enumerate(n):
            fid = int(xf.get("numFmtId") or 0)
            saida[i] = fid in FORMATOS_DE_DATA or personalizados.get(fid, False)
    return saida


def _planilhas(z):
    """Nomes das abas, na ordem do arquivo, com o caminho de cada uma."""
    rels = {}
    try:
        raiz = ElementTree.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        for n in raiz:
            rels[n.get("Id")] = n.get("Target")
    except KeyError:
        pass
    abas = []
    raiz = ElementTree.fromstring(z.read("xl/workbook.xml"))
    for n in raiz.iter():
        if _sem_ns(n.tag) != "sheet":
            continue
        rid = next((v for k, v in n.attrib.items() if k.endswith("}id")), None)
        alvo = rels.get(rid) or "worksheets/sheet%d.xml" % (len(abas) + 1)
        if not alvo.startswith("xl/"):
            alvo = "xl/" + alvo.lstrip("/")
        abas.append({"nome": n.get("name"), "caminho": alvo})
    return abas


def ler_xlsx(caminho, aba=1):
    try:
        z = zipfile.ZipFile(caminho)
    except zipfile.BadZipFile:
        raise PlanilhaIlegivel(
            "este .xlsx não abriu. Se ele veio de um sistema antigo, pode ser um .xls "
            "de verdade — abra no Excel ou no Google Sheets e salve como .xlsx ou .csv")
    with z:
        abas = _planilhas(z)
        if not abas:
            raise PlanilhaIlegivel("não achei nenhuma aba neste arquivo")
        if aba < 1 or aba > len(abas):
            raise PlanilhaIlegivel(
                "este arquivo tem %d aba(s): %s"
                % (len(abas), ", ".join("%d=%s" % (i + 1, a["nome"])
                                        for i, a in enumerate(abas))))
        escolhida = abas[aba - 1]
        compartilhadas = _strings_compartilhadas(z)
        datas = _estilos_de_data(z)
        raiz = ElementTree.fromstring(z.read(escolhida["caminho"]))

        linhas = []
        for linha in raiz.iter():
            if _sem_ns(linha.tag) != "row":
                continue
            celulas = {}
            for c in linha:
                if _sem_ns(c.tag) != "c":
                    continue
                i = coluna_para_indice(c.get("r"))
                if i is None:
                    continue
                tipo = c.get("t")
                valor = None
                for filho in c:
                    nome = _sem_ns(filho.tag)
                    if nome == "v":
                        valor = filho.text
                    elif nome == "is":
                        valor = "".join(n.text or "" for n in filho.iter()
                                        if _sem_ns(n.tag) == "t")
                if valor is None:
                    continue
                if tipo == "s":
                    try:
                        valor = compartilhadas[int(valor)]
                    except (ValueError, IndexError):
                        pass
                elif tipo == "b":
                    valor = "sim" if valor == "1" else "não"
                elif datas.get(int(c.get("s") or 0)):
                    try:
                        valor = (BASE_EXCEL + dt.timedelta(days=float(valor))).date().isoformat()
                    except (ValueError, OverflowError):
                        pass
                celulas[i] = valor
            if celulas:
                largura = max(celulas) + 1
                linhas.append([celulas.get(i) for i in range(largura)])

    linhas = [l for l in linhas if any((c or "") != "" and c is not None for c in l)]
    if not linhas:
        raise PlanilhaIlegivel("a aba '%s' está vazia" % escolhida["nome"])
    return linhas, {"aba": escolhida["nome"],
                    "abas": [a["nome"] for a in abas]}


# -------------------------------------------------------------------- leitura

def _nome_de_coluna(bruto, posicao, usados):
    nome = re.sub(r"\s+", " ", str(bruto or "").strip())
    if not nome:
        nome = "coluna_%d" % (posicao + 1)
    base, n = nome, 2
    while nome in usados:
        nome, n = "%s (%d)" % (base, n), n + 1
    usados.add(nome)
    return nome


def ler(caminho, aba=1):
    """Devolve {colunas, linhas, formato, ...}. Linhas sao dicionarios."""
    p = Path(caminho)
    if not p.exists():
        raise FileNotFoundError("não achei o arquivo %s" % p.name)

    if p.suffix.lower() in (".xlsx", ".xlsm"):
        cruas, extra = ler_xlsx(p, aba)
        formato = "xlsx"
    elif p.suffix.lower() in (".csv", ".txt", ".tsv"):
        cruas, extra = ler_csv(p)
        formato = "csv"
    elif p.suffix.lower() == ".xls":
        raise PlanilhaIlegivel(
            ".xls é o formato antigo do Excel e não abre aqui. Abra no Excel ou no "
            "Google Sheets e salve como .xlsx ou .csv — leva dez segundos")
    else:
        raise PlanilhaIlegivel(
            "não sei ler '%s'. Exporte como .csv ou .xlsx" % (p.suffix or "sem extensão"))

    cabecalho, corpo = cruas[0], cruas[1:]
    usados = set()
    colunas = [_nome_de_coluna(c, i, usados) for i, c in enumerate(cabecalho)]
    linhas = []
    for l in corpo:
        item = {}
        for i, nome in enumerate(colunas):
            item[nome] = _converter(l[i]) if i < len(l) else None
        linhas.append(item)

    d = {"arquivo": p.name, "formato": formato, "colunas": colunas,
         "linhas": linhas, "total_de_linhas": len(linhas),
         "capturado_em": dt.datetime.fromtimestamp(p.stat().st_mtime).astimezone()
                           .isoformat(timespec="seconds")}
    d.update(extra)
    return d


def perfil(dado, exemplos=EXEMPLOS):
    """Descreve cada coluna: tipo, quanto veio preenchido, exemplos reais."""
    saida = []
    for nome in dado["colunas"]:
        valores = [l.get(nome) for l in dado["linhas"]]
        cheios = [v for v in valores if v is not None and v != ""]
        tipos = set()
        for v in cheios:
            if isinstance(v, bool):
                tipos.add("sim/não")
            elif isinstance(v, (int, float)):
                tipos.add("número")
            elif isinstance(v, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                tipos.add("data")
            else:
                tipos.add("texto")
        saida.append({
            "coluna": nome,
            "tipo": "/".join(sorted(tipos)) if tipos else "sempre vazia",
            "preenchidas": len(cheios),
            "vazias": len(valores) - len(cheios),
            "exemplos": cheios[:exemplos],
        })
    return saida


def _main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0

    caminho = Path(args[0])
    if not caminho.is_absolute():
        caminho = BASE / args[0]

    def opcao(nome, padrao):
        if nome in args:
            pos = args.index(nome)
            if pos + 1 < len(args):
                try:
                    return int(args[pos + 1])
                except ValueError:
                    pass
        return padrao

    dado = ler(caminho, aba=opcao("--aba", 1))
    p = perfil(dado, exemplos=opcao("--linhas", EXEMPLOS))

    if "--json" in args:
        print(json.dumps({"arquivo": dado["arquivo"], "formato": dado["formato"],
                          "aba": dado.get("aba"), "abas": dado.get("abas"),
                          "total_de_linhas": dado["total_de_linhas"],
                          "capturado_em": dado["capturado_em"], "colunas": p},
                         ensure_ascii=False, indent=2))
        return 0

    print("%s · %s · %d linha(s)" % (dado["arquivo"], dado["formato"],
                                     dado["total_de_linhas"]))
    if dado.get("abas") and len(dado["abas"]) > 1:
        print("abas: %s (lendo '%s')" % (", ".join(dado["abas"]), dado.get("aba")))
    print("dado capturado em: %s" % dado["capturado_em"])
    print()
    for c in p:
        exemplos = ", ".join(str(e)[:28] for e in c["exemplos"]) or "—"
        vazio = "  (%d vazia(s))" % c["vazias"] if c["vazias"] else ""
        print("  %-32s %-12s %s%s" % (c["coluna"][:32], c["tipo"], exemplos, vazio))
    print("\nNada foi gravado. Esta leitura so descreve o arquivo.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(_main())
    except (PlanilhaIlegivel, FileNotFoundError) as e:
        sys.exit("PARADO: %s" % e)
