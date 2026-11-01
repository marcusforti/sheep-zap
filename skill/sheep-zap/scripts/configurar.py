"""Prepara a pasta do serviço e grava a configuração. Nunca recebe nem mostra chave: elas ficam no .env ou nas Conexões do painel.

  python configurar.py --dono "Nome" --numero 5511999999999 --instancia meu-agente --numero-agente 5511999999999
       [--agente Sheep --pronuncia Xíp --emoji 🐑 --instancia-dono meu-whats --pasta-trabalho CAMINHO]
  python configurar.py --novo-codigo             gera o código que o dono manda para o agente
  python configurar.py --achar-dono CODIGO       acha o chat do dono pelo código e guarda os endereços dele
  python configurar.py --grupo "Nome" --jid X@g.us
  python configurar.py --refazer-prompts         regera os prompts a partir dos modelos (perde edições feitas neles)
  python configurar.py --ver"""
import argparse
import json
import os
import random
import sys
from pathlib import Path

from nucleo import MODELOS, PADRAO, SCRIPTS, ErroConfig, ErroEvolution, _fundir, casa, config, digitos, evolution_agente, ler_json, texto_puro, variantes
from grupo import slug


def trocar(texto, cfg, grupo=""):
    py = f'"{Path(sys.executable).as_posix()}"'
    scripts = SCRIPTS.as_posix()
    nome, fala = cfg["agente"]["nome"], cfg["agente"]["pronuncia"]
    valores = {"AGENTE": nome, "FALA": f' (fala-se "{fala}")' if fala and fala != nome else "", "EMOJI": cfg["agente"]["emoji"], "DONO": cfg["dono"]["nome"], "GRUPO": grupo,
               "ZAP": f'{py} "{scripts}/zap.py"', "VOZ": f'{py} "{scripts}/voz.py"', "MIDIA": f'{py} "{scripts}/midia.py"',
               "CASA": casa().as_posix(), "TRABALHO": Path(cfg["pasta_trabalho"] or casa()).as_posix()}
    for chave, valor in valores.items():
        texto = texto.replace("{{" + chave + "}}", valor)
    return texto


def escrever(destino: Path, texto: str, refazer=False):
    if refazer or not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        return True
    return False


def gravar_config(cfg):
    (casa() / "zap.json").write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def preparar(cfg, refazer=False):
    base = casa()
    for nome in ("AGENTE", "TRIAGEM"):
        escrever(base / "prompts" / f"{nome}.md", trocar((MODELOS / f"{nome}.md").read_text(encoding="utf-8"), cfg), refazer)
    for g in cfg["grupos"]:
        escrever(base / "grupos" / f"{slug(g['nome'], g['jid'])}.md", trocar((MODELOS / "GRUPO.md").read_text(encoding="utf-8"), cfg, g["nome"]), refazer)
    escrever(base / ".env", (MODELOS / "env.exemplo").read_text(encoding="utf-8"))
    escrever(base / ".gitignore", "*\n")
    escrever(base / "HANDOFF.md", f"# Pendências com pessoas ({cfg['agente']['nome']})\n\nUma linha por assunto, com a data exata. O mais recente no topo.\n")
    nome, fala = cfg["agente"]["nome"], cfg["agente"]["pronuncia"]
    escrever(base / "pronuncia.json", json.dumps({nome: fala} if fala and fala != nome else {}, ensure_ascii=False, indent=2))
    trabalho = Path(cfg["pasta_trabalho"] or base)
    trabalho.mkdir(parents=True, exist_ok=True)
    if not any((trabalho / n).exists() for n in ("CLAUDE.md", "AGENTS.md")):
        escrever(trabalho / "CLAUDE.md", trocar((MODELOS / "CASA.md").read_text(encoding="utf-8"), cfg))
    os.makedirs(trabalho / "casa", exist_ok=True)


def pasta_padrao(servico: Path) -> str:
    """Só sobe um nível se ali já mora a identidade do agente. Nunca adivinha uma pasta ampla."""
    pai = servico.parent
    return str(pai if any((pai / n).exists() for n in ("CLAUDE.md", "AGENTS.md")) else servico)


def achar_dono(codigo):
    cfg = config()
    evo = evolution_agente(cfg)
    numero = cfg["dono"]["numero"]
    for x in evo.recentes(1, 200):
        k = x["key"]
        # Este chat vira quem manda no computador: grupo nunca, e o número tem de bater com o informado.
        if not k.get("fromMe") and codigo.lower() in texto_puro(x).lower() and str(k.get("remoteJid")).endswith(("@lid", "@s.whatsapp.net")):
            enderecos = [j for j in (k.get("remoteJid"), k.get("remoteJidAlt")) if j]
            if not variantes(numero) & {digitos(j) for j in enderecos}:
                sys.exit("Achei o código, mas não consegui provar que veio do número do dono. Confira o número informado e mande de novo.")
            cfg["dono"]["jids"] = list(dict.fromkeys(enderecos + [f"{n}@s.whatsapp.net" for n in sorted(variantes(numero))]))
            gravar_config(cfg)
            print(f"Pronto: achei o chat de {cfg['dono']['nome']} ({len(cfg['dono']['jids'])} endereços guardados).")
            return
    sys.exit(f'Ainda não vi o código "{codigo}" chegar no número do agente. Peça para mandar de novo, numa conversa direta, e rode outra vez.')


def main():
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for nome in ("--dono", "--numero", "--numero-agente", "--instancia", "--agente", "--pronuncia", "--emoji", "--instancia-dono", "--pasta-trabalho", "--achar-dono", "--grupo", "--jid"):
        a.add_argument(nome)
    a.add_argument("--novo-codigo", action="store_true")
    a.add_argument("--refazer-prompts", action="store_true")
    a.add_argument("--ver", action="store_true")
    o = a.parse_args()
    if o.novo_codigo:
        print(f"ZAP-{random.randint(1000, 9999)}")
        return
    if o.ver:
        print(json.dumps(config(), ensure_ascii=False, indent=2))
        return
    if o.achar_dono:
        return achar_dono(o.achar_dono)
    cfg = _fundir(PADRAO, ler_json(casa() / "zap.json", {}))
    trocas = {("dono", "nome"): o.dono, ("agente", "instancia"): o.instancia, ("agente", "nome"): o.agente,
              ("agente", "pronuncia"): o.pronuncia, ("agente", "emoji"): o.emoji, ("dono", "instancia"): o.instancia_dono}
    for (bloco, campo), valor in trocas.items():
        if valor is not None:
            cfg[bloco][campo] = valor
    if o.numero:
        cfg["dono"]["numero"] = "".join(c for c in o.numero if c.isdigit())
    if o.numero_agente:
        cfg["agente"]["numero"] = "".join(c for c in o.numero_agente if c.isdigit())
    if cfg["agente"]["nome"] == "Sheep" and not cfg["agente"]["pronuncia"]:
        cfg["agente"]["pronuncia"] = "Xíp"
    if o.pasta_trabalho:
        cfg["pasta_trabalho"] = str(Path(o.pasta_trabalho).expanduser().resolve())
    if not cfg["pasta_trabalho"]:
        cfg["pasta_trabalho"] = pasta_padrao(casa())
    if o.grupo:
        if not o.jid or not o.jid.endswith("@g.us"):
            sys.exit("Passe também --jid com o endereço do grupo (termina em @g.us). Veja em: python zap.py grupos")
        cfg["grupos"] = [g for g in cfg["grupos"] if g["jid"] != o.jid] + [{"nome": o.grupo, "jid": o.jid, "ligado": True}]
    if not cfg["dono"]["nome"] or not cfg["dono"]["numero"] or not cfg["agente"]["instancia"]:
        sys.exit("Faltam dados: --dono, --numero e --instancia.")
    gravar_config(cfg)
    preparar(cfg, o.refazer_prompts)
    print("Pasta do serviço:", casa())
    print("Pasta de trabalho, onde as cópias do agente trabalham:", cfg["pasta_trabalho"])
    if o.grupo:
        regras = casa() / "grupos" / f"{slug(o.grupo, o.jid)}.md"
        print("Regras do grupo em", regras, "(preencha antes de ligar)" if "[Preencher" in regras.read_text(encoding="utf-8") else "")


if __name__ == "__main__":
    try:
        main()
    except (ErroConfig, ErroEvolution) as erro:
        sys.exit(str(erro))
