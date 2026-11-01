"""Ouvido 3: de tempos em tempos vê quem escreveu no número do dono e avisa ele pelo número do agente. Sem IA.
Conversas individuais apenas. Grava terceiros.jsonl, que o agente usa para achar o endereço de quem o dono pede para responder.
Sem o número do dono conectado, olha o número do próprio agente.
Uso: python avisos.py [DESDE_TS]"""
import json
import sys
import time

from nucleo import (IGNORAR, ErroConfig, abrir, batimento, casa, config, digitos, evolution_agente, evolution_dono, gravar_json, ids_da_chave, ids_do_dono,
                    ler_json, registrar, sub, texto_puro, trava, ts, variantes)
from midia import conteudo, resumo


class Avisos:
    def __init__(self, cfg, leitor, carteiro, desde=None, relogio=time.time, numero="agente"):
        self.cfg, self.leitor, self.carteiro, self.agora, self.numero = cfg, leitor, carteiro, relogio, numero
        self.arq_estado = sub("run") / "avisos.json"
        e = ler_json(self.arq_estado, {})
        self.desde = desde if desde is not None else e.get("desde", int(self.agora()))
        self.vistos = e.get("vistos", [])
        self.emoji = cfg["agente"]["emoji"]
        self.meus = ids_do_dono(cfg) | variantes(cfg["agente"].get("numero"))

    def salvar(self):
        gravar_json(self.arq_estado, {"desde": self.desde, "vistos": self.vistos[-500:]})

    def ler_novas(self):
        saida = []
        for pagina in range(1, 8):
            regs = self.leitor.recentes(pagina, 200)
            saida += [x for x in regs if ts(x) >= self.desde and x["key"]["id"] not in self.vistos]
            if not regs or min(ts(x) for x in regs) < self.desde:
                break
        return saida

    def vale(self, x):
        k = x["key"]
        jid = k.get("remoteJid") or ""
        return (bool(jid) and not k.get("fromMe") and x.get("messageType") not in IGNORAR and not jid.endswith(("@g.us", "@broadcast", "@newsletter"))
                and not (ids_da_chave(k) & self.meus) and not texto_puro(x).startswith(self.emoji))

    def previa(self, x):
        # Só áudio é baixado, para virar texto. Arquivo de estranho não entra no computador sem o dono pedir.
        if abrir(x)[0] != "audioMessage":
            return resumo(x)[:90].replace("\n", " ")
        return conteudo(x, self.leitor)[:160].replace("\n", " ")

    def passo(self):
        tudo = self.ler_novas()
        msgs = sorted(filter(self.vale, tudo), key=ts)
        if msgs:
            por = {}
            for x in msgs:
                jid = x["key"]["remoteJid"]
                p = por.setdefault(jid, {"jid": jid, "alt": x["key"].get("remoteJidAlt"), "numero": self.numero, "nome": x.get("pushName") or digitos(jid), "qtd": 0, "msgs": []})
                p["qtd"] += 1
                p["msgs"].append(self.previa(x))
                p["ultima"] = ts(x)
            linhas = [f"• *{p['nome']}*" + (f" ({p['qtd']})" if p["qtd"] > 1 else "") + f": {p['msgs'][-1]}" for p in por.values()]
            texto = f"{self.emoji} Chegou mensagem pra você:\n" + "\n".join(linhas) + "\n\nSe quiser que eu responda alguém, é só me falar."
            self.carteiro.texto(self.cfg["dono"]["numero"], texto[:3500])
            with open(casa() / "terceiros.jsonl", "a", encoding="utf-8") as f:
                for p in por.values():
                    f.write(json.dumps({"ts": int(self.agora()), **p}, ensure_ascii=False) + "\n")
        # Só avança depois de avisar: se a rede cair, o próximo passo tenta de novo em vez de perder o recado.
        self.desde = max([self.desde] + [ts(x) for x in tudo])
        self.vistos += [x["key"]["id"] for x in tudo]
        self.salvar()


def main():
    tranca = trava("avisos", insistir=2)
    if tranca is None:
        sys.exit("Os avisos já estão rodando.")
    cfg = config()
    carteiro = evolution_agente(cfg)
    do_dono = evolution_dono(cfg)
    avisos = Avisos(cfg, do_dono or carteiro, carteiro, int(sys.argv[1]) if len(sys.argv) > 1 else None, numero="dono" if do_dono else "agente")
    avisos.salvar()
    while True:
        batimento("avisos")
        try:
            avisos.passo()
        except Exception as erro:
            registrar("avisos", erro=f"{type(erro).__name__}: {erro}"[:200])
        time.sleep(cfg["intervalos"]["avisos"])


if __name__ == "__main__":
    try:
        main()
    except ErroConfig as erro:
        sys.exit(str(erro))
