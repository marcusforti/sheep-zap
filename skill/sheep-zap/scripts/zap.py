"""Manda e lê no WhatsApp pela Evolution. Sai pelo número do agente; com --de dono, pelo número do dono.

  python zap.py DESTINO texto "mensagem"
  python zap.py DESTINO audio arquivo.mp3
  python zap.py DESTINO imagem|video|documento arquivo "legenda"
  python zap.py DESTINO enquete "pergunta" "opção 1|opção 2"
  python zap.py DESTINO novas DESDE_TS        lê a conversa desde esse horário, as duas pontas
  python zap.py conversas [filtro]            lista conversas para achar o endereço de alguém
  python zap.py grupos                        lista os grupos
  python zap.py confere ID                    diz se a mensagem chegou

DESTINO: dono, número com DDI ou endereço (jid). Depois de enviar, espero o WhatsApp confirmar.
"aceito" e "no servidor" não provam entrega; só "entregue" e "lido" provam. --sem-conferir não espera."""
import sys
import time

from nucleo import (ErroConfig, ErroEvolution, IGNORAR, config, evolution_agente, evolution_dono, gravar_json, ler_json, sub,
                    status_entrega, ts)
from midia import conteudo, resumo


def _destino(cfg, valor):
    return cfg["dono"]["numero"] if valor == "dono" else valor


def enderecos(evo, jid):
    """A mesma pessoa pode ter dois endereços: o que ela escreve fica em um, e o que sai para ela, em outro."""
    achados = {jid}
    for x in evo.recentes(1, 200) + evo.mensagens(jid, 20):
        k = x["key"]
        par = {j for j in (k.get("remoteJid"), k.get("remoteJidAlt")) if j}
        if achados & par:
            achados |= par
    return achados


def destino_real(evo, destino, modo):
    """A Evolution recusa áudio para endereço @lid (HTTP 400): manda para o número da pessoa."""
    if modo == "texto" or not destino.endswith("@lid"):
        return destino
    numero = next((j for j in enderecos(evo, destino) if j.endswith("@s.whatsapp.net")), None)
    return numero.split("@")[0] if numero else destino


def conversa(evo, jid, desde):
    vistos, regs = set(), []
    for endereco in enderecos(evo, jid):
        for x in evo.mensagens(endereco, 50):
            if x["key"]["id"] not in vistos and ts(x) > desde and x.get("messageType") not in IGNORAR:
                vistos.add(x["key"]["id"])
                regs.append(x)
    linhas = []
    for x in sorted(regs, key=ts):
        quem = "EU" if x["key"].get("fromMe") else (x.get("pushName") or "pessoa")
        texto = resumo(x) if x["key"].get("fromMe") else conteudo(x, evo)
        linhas.append(f"{ts(x)} | {quem} | " + texto.replace("\n", " / "))
    return linhas


def _no_ritmo(cfg, evo):
    """Envia picado: número que dispara em sequência toma bloqueio."""
    arq = sub("run") / f"ultimo-envio-{evo.instancia}.json"
    espera = ler_json(arq, 0) + cfg["limites"]["segundos_entre_envios"] - time.time()
    if espera > 0:
        time.sleep(espera)
    gravar_json(arq, time.time())


def conferir(evo, mid, tentativas=8, pausa=3):
    situacao = "aceito"
    for _ in range(tentativas):
        time.sleep(pausa)
        registro = evo.por_id(mid)
        situacao = status_entrega(registro) if registro else situacao
        if situacao in ("entregue", "lido", "erro"):
            break
    return situacao


def enviar(cfg, evo, destino, modo, args, verificar=True):
    estado = evo.estado()
    if estado != "open":
        sys.exit(f"Não enviei: a instância {evo.instancia} está {estado}. Reconecte lendo o QR Code.")
    _no_ritmo(cfg, evo)
    destino = destino_real(evo, destino, modo)
    if modo == "texto":
        r = evo.texto(destino, args[0])
    elif modo == "audio":
        r = evo.audio(destino, args[0])
    elif modo in ("imagem", "video", "documento"):
        r = evo.midia(destino, {"imagem": "image", "video": "video", "documento": "document"}[modo], args[0], args[1] if len(args) > 1 else "")
    elif modo == "enquete":
        r = evo.enquete(destino, args[0], args[1].split("|"))
    else:
        sys.exit(__doc__)
    mid = ((r or {}).get("key") or {}).get("id")
    if not verificar or not mid:
        print("aceito", mid, "(aceito não prova entrega)")
    elif destino.endswith("@g.us"):
        print("aceito", mid, "(grupo não confirma entrega: confira no celular)")
    else:
        situacao = conferir(evo, mid)
        print(situacao, mid, "" if situacao in ("entregue", "lido") else "(ainda sem prova de entrega)")
        if situacao == "erro":
            sys.exit(1)


def main(argv):
    dono = "--de" in argv and argv[argv.index("--de") + 1:argv.index("--de") + 2] == ["dono"]
    verificar = "--sem-conferir" not in argv
    if dono:
        i = argv.index("--de")
        argv = argv[:i] + argv[i + 2:]
    argv = [a for a in argv if a != "--sem-conferir"]
    if not argv:
        sys.exit(__doc__)
    cfg = config()
    evo = evolution_dono(cfg) if dono else evolution_agente(cfg)
    if evo is None:
        sys.exit("O número do dono não está conectado nesta instalação (dono.instancia em zap.json).")
    if argv[0] == "conversas":
        filtro = (argv[1] if len(argv) > 1 else "").lower()
        for c in evo.conversas():
            nome, jid = c.get("pushName") or "", c.get("remoteJid") or ""
            if filtro in nome.lower() or filtro in jid:
                print(jid, "|", nome)
    elif argv[0] == "grupos":
        grupos = evo.grupos()
        print("\n".join(f"{g.get('id')} | {g.get('subject')}" for g in grupos) or "Este número não está em nenhum grupo. Adicione o número do agente ao grupo pelo WhatsApp e rode de novo.")
    elif argv[0] == "confere":
        registro = evo.por_id(argv[1])
        print(status_entrega(registro) if registro else "não achei essa mensagem")
    elif len(argv) >= 3 and argv[1] == "novas":
        jid = _destino(cfg, argv[0])
        print("\n".join(conversa(evo, jid if "@" in jid else jid + "@s.whatsapp.net", int(argv[2]))))
    elif len(argv) >= 3:
        enviar(cfg, evo, _destino(cfg, argv[0]), argv[1], argv[2:], verificar)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (ErroConfig, ErroEvolution) as erro:
        sys.exit(str(erro))
