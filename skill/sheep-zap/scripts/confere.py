"""Confere se está tudo pronto.
  python confere.py                  não manda nada para ninguém
  python confere.py --envio          manda uma mensagem de teste ao dono e espera o WhatsApp confirmar a entrega
  python confere.py --modelos        faz uma chamada curta ao Claude para testar o login e o isolamento"""
import subprocess
import sys
from pathlib import Path

from nucleo import (ErroConfig, ErroEvolution, SEM_JANELA, ambiente, casa, claude_cmd, config, evolution_agente, evolution_dono, origem_segredo, pensar,
                    rodando, segredo, sub)
from grupo import slug

OK, AVISO, ERRO = "OK     ", "ATENÇÃO", "FALTA  "
problemas, avisos = [], [0]


def linha(marca, texto):
    print(marca, texto)
    if marca == ERRO:
        problemas.append(texto)
    avisos[0] += marca == AVISO


def checar_evolution(rotulo, evo):
    try:
        estado = evo.estado()
    except ErroEvolution as e:
        linha(ERRO, f"{rotulo}: {e}")
        return False
    if estado == "open":
        linha(OK, f"{rotulo}: conectado (instância {evo.instancia}). Conectado não prova que envia: faça o teste --envio.")
        return True
    linha(ERRO, f"{rotulo}: {estado}. Leia o QR Code de novo na Evolution.")
    return False


def checar_envio(cfg, evo):
    from zap import conferir
    r = evo.texto(cfg["dono"]["numero"], f"{cfg['agente']['emoji']} Teste do sheep-zap: se isto chegou, o envio funciona.")
    mid = ((r or {}).get("key") or {}).get("id")
    situacao = conferir(evo, mid) if mid else "sem id"
    linha(OK if situacao in ("entregue", "lido") else ERRO, f"Teste de envio ao dono: {situacao}")


def checar_modelos(cfg):
    regras = sub("run") / "teste-modelos.md"
    regras.write_text('Responda só com um JSON: {"ok": true, "contexto": "SIM ou NAO"}. Em "contexto", diga SIM se existir no seu contexto qualquer arquivo de instruções ou memória além desta mensagem.', encoding="utf-8")
    try:
        saida = pensar("Teste técnico.", regras, cfg["modelos"]["triagem"], 120)
    except subprocess.TimeoutExpired:
        return linha(ERRO, "Claude não respondeu em 2 minutos.")
    if not saida.strip():
        return linha(ERRO, "Claude não respondeu. Abra o Claude Code uma vez e confira o login.")
    if '"ok"' not in saida:
        return linha(ERRO, "Claude respondeu fora do combinado. Costuma ser login vencido ou plano no limite: abra o Claude Code uma vez para ver a mensagem.")
    linha(OK, "Claude respondeu pelo modelo de triagem")
    isolado = "SIM" not in saida.upper()
    linha(OK if isolado else AVISO, "Isolamento: " + ("quem responde grupo não leva a sua memória" if isolado else "o modelo diz ver outros arquivos, confira se há CLAUDE.md na pasta temporária"))


def main(argv):
    v = sys.version_info
    linha(OK if v >= (3, 9) else ERRO, f"Python {v.major}.{v.minor}")
    try:
        r = subprocess.run(claude_cmd() + ["--version"], capture_output=True, text=True, timeout=30, env=ambiente(), creationflags=SEM_JANELA)
        linha(OK, "Claude Code " + r.stdout.strip().split(" ")[0])
    except ErroConfig as e:
        linha(ERRO, str(e))
    except (OSError, subprocess.SubprocessError) as e:
        linha(ERRO, f"Claude Code não abriu: {type(e).__name__}")
    try:
        cfg = config()
    except ErroConfig as e:
        linha(ERRO, str(e))
        return 1
    linha(OK, f"Pasta do serviço: {casa()}")
    linha(OK if Path(cfg["pasta_trabalho"] or casa()).is_dir() else ERRO, f"Pasta de trabalho: {cfg['pasta_trabalho']}")
    linha(OK if cfg["dono"]["jids"] else ERRO, "Chat do dono identificado" if cfg["dono"]["jids"] else "Chat do dono ainda não identificado: rode configurar.py --novo-codigo, peça para o dono mandar o código ao agente e rode --achar-dono CODIGO")
    url = segredo("EVOLUTION_URL")
    if not url or not segredo("EVOLUTION_API_KEY"):
        linha(ERRO, f"Faltam EVOLUTION_URL e EVOLUTION_API_KEY (Conexões do painel ou {casa() / '.env'})")
        return 1
    linha(OK, f"Chave da Evolution: {origem_segredo('EVOLUTION_API_KEY')}")
    if url.startswith("http://") and not any(h in url for h in ("localhost", "127.0.0.1")):
        linha(AVISO, "A Evolution está em http, sem cadeado: a chave e as conversas passam abertas na internet. Em Wi-Fi público, alguém poderia ler ou falsificar. Para uso sério, coloque um domínio com https.")
    agente = evolution_agente(cfg)
    envia = checar_evolution("Número do agente", agente)
    dono = evolution_dono(cfg)
    if dono:
        checar_evolution("Número do dono", dono)
    else:
        linha(AVISO, "Número do dono não conectado: o agente não responde como você, e os avisos mostram só quem escreveu para o número do agente")
    try:
        import faster_whisper  # noqa: F401
        linha(OK, "Áudio: transcrição no computador (faster-whisper)")
    except ImportError:
        linha(OK if segredo("ELEVENLABS_API_KEY") else AVISO, "Áudio: transcrição pela ElevenLabs" if segredo("ELEVENLABS_API_KEY") else "Áudio: ainda não ouço áudio. Instale faster-whisper ou cadastre a ElevenLabs.")
    linha(OK if segredo("ELEVENLABS_API_KEY") else AVISO, "Voz: ElevenLabs cadastrada" if segredo("ELEVENLABS_API_KEY") else "Voz: sem ElevenLabs, respondo só em texto")
    for g in cfg["grupos"]:
        regras = casa() / "grupos" / f"{slug(g['nome'], g['jid'])}.md"
        pendente = not regras.exists() or "[Preencher" in regras.read_text(encoding="utf-8")
        linha(ERRO if pendente else OK, f"Grupo {g['nome']}: " + ("faltam partes [Preencher] nas regras" if pendente else "ligado" if g.get("ligado", True) else "desligado"))
    for nome in ("chat", "avisos", "grupo"):
        if rodando(nome):
            linha(OK, f"Serviço {nome} rodando")
    if "--modelos" in argv:
        checar_modelos(cfg)
    if "--envio" in argv and envia:
        checar_envio(cfg, agente)
    print(f"\n{len(problemas)} coisa(s) para resolver." if problemas else f"\nTudo certo{', com ' + str(avisos[0]) + ' ponto(s) de atenção acima' if avisos[0] else ''}.")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
