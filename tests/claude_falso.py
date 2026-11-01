"""Claude de mentira. Sem ferramentas decide como a triagem ou o grupo; com ferramentas age como agente de pedido.
Grava cada chamada em SHEEP_ZAP_CHAMADAS para os testes conferirem opções, pasta e entrada.
Palavras na mensagem mudam o comportamento: DEMORA, QUEBRA, TRIAGEMRUIM."""
import json
import os
import re
import sys
import time

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
args = sys.argv[1:]
if args == ["--version"]:
    print("2.1.316 (Claude Code)")
    sys.exit(0)
entrada = sys.stdin.read()
with open(os.environ["SHEEP_ZAP_CHAMADAS"], "a", encoding="utf-8") as f:
    f.write(json.dumps({"args": args, "cwd": os.getcwd(), "entrada": entrada, "pid": os.getpid()}, ensure_ascii=False) + "\n")

ultima = entrada.rsplit("mensagem de", 1)[-1] if "ÚLTIMA" in entrada else entrada
sem_ferramentas = "--tools" in args
if sem_ferramentas:
    if any(a.endswith("teste-modelos.md") for a in args):
        print(json.dumps({"ok": True, "contexto": "NAO"}))
    elif "TRIAGEMRUIM" in entrada:
        print("não sei responder em JSON")
    elif re.search(r"\bbom dia\b|tá aí", ultima, re.I):
        print(json.dumps({"nivel": "simples", "resposta": "Tô aqui!", "resumo": "cumprimento", "frente": "geral"}))
    elif "<mensagens>" in entrada:
        print(json.dumps({"responder": True, "texto": "🐑 Ana, é assim.", "avisar_dono": ""}))
    else:
        frente = (re.search(r"frente:(\S+)", ultima) or [None, "geral"])[1]
        print(json.dumps({"nivel": "avancado", "resumo": ultima.strip().splitlines()[-1][:40], "frente": frente}))
    sys.exit(0)

print("aviso: SessionEnd hook [python3 'medida.py'] failed: Hook cancelled", file=sys.stderr)
if "DEMORA" in entrada:
    time.sleep(40)
if "QUEBRA" in entrada:
    sys.exit(1)
print("Feito o pedido.")
