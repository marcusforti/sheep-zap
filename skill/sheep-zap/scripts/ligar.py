"""Liga, para e confere os serviços. Roda quantas vezes quiser: só liga o que estiver parado.

  python ligar.py                  liga o que faltar
  python ligar.py status           mostra o que está rodando
  python ligar.py parar            para tudo
  python ligar.py reiniciar        para e liga de novo
  python ligar.py login on|off     liga ou desliga o início automático ao entrar no computador"""
import os
import plistlib
import signal
import subprocess
import sys
import time
from pathlib import Path

from nucleo import NO_WINDOWS, SCRIPTS, ErroConfig, ambiente, casa, config, matar, rodando, segundos_sem_sinal, sub

SEM_SINAL = 900   # um laço de serviço nunca passa disso calado, nem transcrevendo


def servicos(cfg):
    nomes = ["chat", "avisos"]
    if any(g.get("ligado", True) for g in cfg["grupos"]):
        nomes.append("grupo")
    return nomes


def pid(nome):
    try:
        return int((sub("run") / f"{nome}.lock").read_text(encoding="utf-8").strip() or 0)
    except (OSError, ValueError):
        return 0


def subir(nome):
    """Sobe solto do processo que chamou. Roda a partir da pasta do serviço: no Windows, rodar de dentro da skill impediria atualizá-la."""
    log = open(sub("logs") / f"{nome}.saida.txt", "a", encoding="utf-8")
    comum = dict(cwd=str(casa()), stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=ambiente(), close_fds=True)
    cmd = [sys.executable, str(SCRIPTS / f"{nome}.py")]
    if NO_WINDOWS:
        base = 0x08000000 | 0x00000200   # sem janela, grupo próprio
        try:
            subprocess.Popen(cmd, creationflags=base | 0x01000000, **comum)   # e fora do job de quem chamou
        except OSError:
            subprocess.Popen(cmd, creationflags=base, **comum)
    else:
        subprocess.Popen(cmd, start_new_session=True, **comum)


def ligar(cfg):
    for nome in servicos(cfg):
        if rodando(nome):
            print(f"  {nome}: já estava ligado")
            continue
        subir(nome)
        for _ in range(20):
            time.sleep(0.25)
            if rodando(nome):
                break
        print(f"  {nome}: {'ligado' if rodando(nome) else 'NÃO LIGOU, veja logs/' + nome + '.saida.txt'}")


def parar():
    for nome in ("chat", "avisos", "grupo"):
        if not rodando(nome):
            continue
        alvo = pid(nome)
        if not NO_WINDOWS and alvo > 0:
            # No Mac e no Linux cada cópia do agente tem sessão própria: o chat precisa fechá-las antes de sair.
            try:
                os.kill(alvo, signal.SIGTERM)
            except OSError:
                pass
            for _ in range(30):
                time.sleep(0.1)
                if not rodando(nome):
                    break
        if rodando(nome):
            matar(alvo)
        print(f"  {nome}: parado")


def status(cfg):
    for nome in servicos(cfg):
        if not rodando(nome):
            print(f"  {nome}: parado")
            continue
        calado = segundos_sem_sinal(nome)
        alerta = f", mas sem sinal há {calado // 60} min: rode reiniciar" if calado is not None and calado > SEM_SINAL else ""
        print(f"  {nome}: ligado, processo {pid(nome)}{alerta}")


def login(ativar):
    casa_txt = str(casa())
    alvo = Path(sys.executable)
    ligar_py = str(SCRIPTS / "ligar.py")
    if NO_WINDOWS:
        pythonw = alvo.with_name("pythonw.exe")
        py = pythonw if pythonw.exists() else alvo
        arq = Path(os.environ["APPDATA"]) / "Microsoft/Windows/Start Menu/Programs/Startup/sheep-zap.vbs"
        linhas = ['Set s = CreateObject("WScript.Shell")', f's.Environment("PROCESS")("SHEEP_ZAP_HOME") = "{casa_txt}"',
                  f's.Run """{py}"" ""{ligar_py}""", 0, False']
        conteudo = "\r\n".join(linhas) + "\r\n"
    elif sys.platform == "darwin":
        arq = Path.home() / "Library/LaunchAgents/com.sheepzap.ligar.plist"
        conteudo = None
        dados = {"Label": "com.sheepzap.ligar", "ProgramArguments": [str(alvo), ligar_py], "RunAtLoad": True,
                 "EnvironmentVariables": {"SHEEP_ZAP_HOME": casa_txt, "PATH": os.environ.get("PATH", "")}}
    else:
        arq = Path.home() / ".config/autostart/sheep-zap.desktop"
        conteudo = f'[Desktop Entry]\nType=Application\nName=sheep-zap\nExec=env SHEEP_ZAP_HOME="{casa_txt}" "{alvo}" "{ligar_py}"\nX-GNOME-Autostart-enabled=true\n'
    if not ativar:
        arq.unlink(missing_ok=True)
        print("Início automático desligado.")
        return
    arq.parent.mkdir(parents=True, exist_ok=True)
    if conteudo is None:
        with open(arq, "wb") as f:
            plistlib.dump(dados, f)
    else:
        # O Windows lê .vbs em ANSI ou UTF-16: em UTF-8, uma pasta com acento quebraria o início automático.
        arq.write_text(conteudo, encoding="utf-16" if NO_WINDOWS else "utf-8")
    print("Início automático ligado:", arq)


def main(argv):
    acao = argv[0] if argv else "ligar"
    if acao == "login":
        if argv[1:] not in (["on"], ["off"]):
            sys.exit(__doc__)
        return login(argv[1] == "on")
    if acao == "parar":
        return parar()
    cfg = config()
    if acao == "status":
        status(cfg)
    elif acao == "reiniciar":
        parar()
        time.sleep(1)
        ligar(cfg)
    elif acao == "ligar":
        ligar(cfg)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except ErroConfig as erro:
        sys.exit(str(erro))
