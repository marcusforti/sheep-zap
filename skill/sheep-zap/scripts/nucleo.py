"""Base comum: pastas, configuração, segredos, Evolution e chamadas ao Claude. Só biblioteca padrão."""
import base64
import copy
import http.client
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

for _fluxo in (sys.stdout, sys.stderr):
    if _fluxo and hasattr(_fluxo, "reconfigure"):
        _fluxo.reconfigure(encoding="utf-8", errors="replace")

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
MODELOS = SKILL / "modelos"
NO_WINDOWS = os.name == "nt"
SEM_JANELA = 0x08000000 if NO_WINDOWS else 0

# Tipos que nunca viram conversa: reação, recibo, enquete votada e o envelope vazio do álbum.
IGNORAR = ("reactionMessage", "protocolMessage", "encEventResponseMessage", "pollUpdateMessage", "senderKeyDistributionMessage",
           "secretEncryptedMessage", "editedMessage", "stickerMessage", "albumMessage")
# Formatos que embrulham a mensagem de verdade dentro de outra. Álbum chega assim, e sem abrir a foto se perde.
EMBRULHOS = ("associatedChildMessage", "ephemeralMessage", "viewOnceMessage", "viewOnceMessageV2", "viewOnceMessageV2Extension",
             "documentWithCaptionMessage")
TIPOS_MIDIA = ("audioMessage", "imageMessage", "videoMessage", "documentMessage")

PADRAO = {
    "agente": {"nome": "Sheep", "pronuncia": "", "emoji": "🐑", "instancia": "", "numero": ""},
    "dono": {"nome": "", "numero": "", "jids": [], "instancia": ""},
    "pasta_trabalho": "",
    "pastas_extras": [],
    "modelos": {"triagem": "haiku", "medio": "sonnet", "avancado": "opus", "grupo": "sonnet"},
    "limites": {"agentes_juntos": 2, "minutos_por_agente": 90, "pedidos_por_dia": 40, "grupo_por_hora": 6, "grupo_por_dia": 30,
                "grupo_caracteres": 1100, "segundos_entre_envios": 8},
    "intervalos": {"chat": 10, "grupo": 45, "rajada_grupo": 35, "avisos": 300},
    "voz": {"agente": "GM2UA3fbsIaLHcswCDX9", "dono": "", "modelo": "eleven_v4"},
    "whisper": "small",
    "grupos": [],
}


class ErroConfig(Exception):
    """Falta alguma coisa que só a instalação resolve. A mensagem é para gente, não para programador."""


class ErroEvolution(OSError):
    def __init__(self, mensagem, status=None):
        super().__init__(mensagem)
        self.status = status


def casa() -> Path:
    """Pasta do serviço: configuração, estado, registros e mídia. Nunca a pasta da skill."""
    if os.environ.get("SHEEP_ZAP_HOME"):
        p = Path(os.environ["SHEEP_ZAP_HOME"])
    else:
        sheep = Path(os.environ.get("SHEEP_HOME") or Path.home() / "Sheep")
        p = sheep / "zap" if sheep.is_dir() else Path.home() / "sheep-zap"
    p.mkdir(parents=True, exist_ok=True)
    return p


def sub(nome: str) -> Path:
    p = casa() / nome
    p.mkdir(parents=True, exist_ok=True)
    return p


def _fundir(base, novo):
    saida = copy.deepcopy(base)
    for k, v in novo.items():
        saida[k] = _fundir(saida[k], v) if isinstance(v, dict) and isinstance(saida.get(k), dict) else v
    return saida


def config() -> dict:
    arq = casa() / "zap.json"
    if not arq.exists():
        raise ErroConfig(f"Ainda não configurei o WhatsApp nesta máquina (falta {arq}). Rode a instalação da skill sheep-zap.")
    return _fundir(PADRAO, json.loads(arq.read_text(encoding="utf-8")))


def _procurar_segredo(nome: str):
    """O .env do serviço vem primeiro: uma variável antiga do computador não pode apontar para outra Evolution sem ninguém ver."""
    env = casa() / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            chave, sinal, resto = linha.partition("=")
            valor = resto.strip().strip("\"'")
            if sinal and chave.strip() == nome and valor:   # linha em branco não esconde as outras fontes
                return valor, ".env da pasta do serviço"
    valor = (os.environ.get(nome) or "").strip()
    if valor:
        return valor, "variável de ambiente do computador"
    cofre = Path(os.environ.get("SHEEP_HOME") or Path.home() / "Sheep").parent / ".sheep-cofre" / nome
    if cofre.is_file():
        valor = cofre.read_text(encoding="utf-8").strip()
        if valor:
            return valor, "Conexões do painel da Sheep"
    return None, None


def segredo(nome: str):
    """Nunca imprima o valor."""
    return _procurar_segredo(nome)[0]


def origem_segredo(nome: str):
    return _procurar_segredo(nome)[1]


def ler_json(p: Path, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return padrao


def gravar_json(p: Path, dados) -> None:
    temporario = p.with_suffix(p.suffix + ".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding="utf-8")
    os.replace(temporario, p)


def registrar(nome: str, **campos) -> None:
    with (sub("logs") / f"{nome}.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": int(time.time()), **campos}, ensure_ascii=False) + "\n")


def batimento(nome: str) -> None:
    """Prova de que o laço do serviço está andando. O processo pode estar vivo e travado."""
    (sub("run") / f"{nome}.vivo").write_text(str(int(time.time())), encoding="utf-8")


def segundos_sem_sinal(nome: str):
    try:
        return int(time.time()) - int((sub("run") / f"{nome}.vivo").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def trava(nome: str, insistir=0.0):
    """Garante um processo só por serviço: dois vigias no mesmo chat responderiam tudo em dobro.
    insistir: segundos tentando, porque quem confere se está ligado segura a trava por um instante."""
    arq = open(sub("run") / f"{nome}.lock", "a+", encoding="utf-8")
    fim = time.time() + insistir
    while True:
        try:
            if NO_WINDOWS:
                import msvcrt
                arq.seek(1 << 20)  # trava um byte bem longe para o PID continuar legível
                msvcrt.locking(arq.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(arq, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except OSError:
            if time.time() >= fim:
                arq.close()
                return None
            time.sleep(0.1)
    arq.seek(0)
    arq.truncate()
    arq.write(str(os.getpid()))
    arq.flush()
    return arq


def soltar_trava(arq) -> None:
    if NO_WINDOWS:
        import msvcrt
        arq.seek(1 << 20)
        msvcrt.locking(arq.fileno(), msvcrt.LK_UNLCK, 1)
    arq.close()


def rodando(nome: str) -> bool:
    arq = trava(nome)
    if arq is None:
        return True
    soltar_trava(arq)
    return False


def matar(pid: int) -> None:
    """Derruba o processo e os filhos dele: no Windows o claude pode nascer de um .cmd."""
    if not pid or pid <= 0:   # no Mac e no Linux, grupo 0 seria o próprio grupo de quem chamou
        return
    if NO_WINDOWS:
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(pid)], capture_output=True, creationflags=SEM_JANELA)
        return
    import signal
    try:
        os.killpg(pid, signal.SIGKILL)
    except OSError:
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            pass


def e_o_processo(pid: int, nome: str) -> bool:
    """Confere o nome antes de matar por PID guardado: depois de reiniciar, o número pode ser de outro programa."""
    if not pid or pid <= 0 or not nome:
        return False
    if NO_WINDOWS:
        r = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"], capture_output=True, text=True, errors="replace", creationflags=SEM_JANELA)
    else:
        r = subprocess.run(["ps", "-p", str(pid), "-o", "comm="], capture_output=True, text=True, errors="replace")
    return nome.lower() in r.stdout.lower()


# ---------- Mensagens ----------

def ts(x) -> int:
    try:
        return int(x.get("messageTimestamp") or 0)
    except (TypeError, ValueError):
        return 0


def abrir(x):
    """Devolve (tipo, conteúdo) de verdade, tirando embrulhos como o de álbum."""
    tipo, m = x.get("messageType"), x.get("message") or {}
    for _ in range(4):
        if tipo not in EMBRULHOS:
            break
        dentro = (m.get(tipo) or {}).get("message") or {}
        m = dentro
        tipo = next((k for k in TIPOS_MIDIA + EMBRULHOS + ("conversation", "extendedTextMessage") if k in dentro), tipo)
        if tipo not in dentro:
            break
    return tipo, m


def texto_puro(x) -> str:
    tipo, m = abrir(x)
    t = m.get("conversation") or (m.get("extendedTextMessage") or {}).get("text")
    if t:
        return t
    return ((m.get(tipo) or {}).get("caption") or "") if isinstance(m.get(tipo), dict) else ""


def digitos(jid) -> str:
    return str(jid or "").split("@")[0].split(":")[0]


def variantes(numero) -> set:
    """No Brasil, o WhatsApp tira o nono dígito do endereço em muitos DDDs: o mesmo número aparece de dois jeitos."""
    n = digitos(numero)
    if n.startswith("55") and len(n) == 13 and n[4] == "9":
        return {n, n[:4] + n[5:]}
    if n.startswith("55") and len(n) == 12:
        return {n, n[:4] + "9" + n[4:]}
    return {n} if n else set()


def ids_da_chave(key: dict) -> set:
    return {digitos(key.get(c)) for c in ("participant", "participantAlt", "remoteJid", "remoteJidAlt") if key.get(c)}


def ids_do_dono(cfg) -> set:
    return {digitos(j) for j in cfg["dono"]["jids"]} | variantes(cfg["dono"]["numero"])


def status_entrega(registro: dict) -> str:
    """lido, entregue, no servidor, erro ou aceito. Só lido e entregue provam que chegou."""
    estados = {str(u.get("status")) for u in registro.get("MessageUpdate") or []} | {str(registro.get("status"))}
    if estados & {"READ", "PLAYED"}:
        return "lido"
    if "DELIVERY_ACK" in estados:
        return "entregue"
    if "ERROR" in estados:
        return "erro"
    if "SERVER_ACK" in estados:
        return "no servidor"
    return "aceito"


class Evolution:
    def __init__(self, instancia: str, url=None, chave=None):
        self.instancia = instancia
        self.url = (url or segredo("EVOLUTION_URL") or "").rstrip("/")
        self.chave = chave or segredo("EVOLUTION_API_KEY")
        if not self.url or not self.chave:
            raise ErroConfig("Faltam EVOLUTION_URL e EVOLUTION_API_KEY. Cadastre em Conexões no painel da Sheep ou no arquivo .env da pasta do serviço.")
        if not instancia:
            raise ErroConfig("Falta o nome da instância da Evolution.")

    def _pedido(self, metodo, rota, corpo=None, tempo=60):
        pedido = urllib.request.Request(self.url + rota, method=metodo,
                                        data=json.dumps(corpo).encode("utf-8") if corpo is not None else None,
                                        headers={"Content-Type": "application/json", "apikey": self.chave})
        try:
            with urllib.request.urlopen(pedido, timeout=tempo) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raise ErroEvolution(f"A Evolution respondeu HTTP {e.code} em {rota.split('?')[0]}", e.code) from None
        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as e:
            raise ErroEvolution(f"Não consegui falar com a Evolution: {getattr(e, 'reason', type(e).__name__)}") from None

    def _rota(self, caminho):
        return f"{caminho}/{urllib.parse.quote(self.instancia, safe='')}"

    def post(self, caminho, corpo, tempo=60):
        return self._pedido("POST", self._rota(caminho), corpo, tempo)

    def get(self, caminho, consulta="", tempo=60):
        return self._pedido("GET", self._rota(caminho) + consulta, None, tempo)

    def estado(self) -> str:
        return ((self.get("/instance/connectionState") or {}).get("instance") or {}).get("state", "desconhecido")

    def _registros(self, corpo):
        r = self.post("/chat/findMessages", corpo)
        caixa = r.get("messages", r) if isinstance(r, dict) else r
        regs = caixa.get("records") if isinstance(caixa, dict) else caixa
        # Um registro torto não pode travar quem está esperando a resposta.
        return [x for x in regs or [] if isinstance(x, dict) and isinstance(x.get("key"), dict) and x["key"].get("id")]

    def mensagens(self, jid, n=20):
        return sorted(self._registros({"where": {"key": {"remoteJid": jid}}, "page": 1, "offset": n}), key=ts)

    def recentes(self, pagina=1, n=200):
        return self._registros({"page": pagina, "offset": n})

    def por_id(self, mid):
        regs = self._registros({"where": {"key": {"id": mid}}, "page": 1, "offset": 1})
        return next((x for x in regs if x["key"]["id"] == mid), None)

    def texto(self, destino, texto):
        return self.post("/message/sendText", {"number": destino, "text": texto})

    def audio(self, destino, arquivo):
        return self.post("/message/sendWhatsAppAudio", {"number": destino, "audio": _b64(arquivo)}, 300)

    def midia(self, destino, tipo, arquivo, legenda=""):
        import mimetypes
        mime = {"image": "image/jpeg", "video": "video/mp4"}.get(tipo) or mimetypes.guess_type(str(arquivo))[0] or "application/octet-stream"
        return self.post("/message/sendMedia", {"number": destino, "mediatype": tipo, "mimetype": mime, "caption": legenda,
                                                "fileName": Path(arquivo).name, "media": _b64(arquivo)}, 300)

    def enquete(self, destino, pergunta, opcoes):
        return self.post("/message/sendPoll", {"number": destino, "name": pergunta, "selectableCount": 1, "values": opcoes})

    def baixar(self, x) -> bytes:
        # Vai a mensagem já aberta: só com o id, a Evolution recusa o que veio dentro de álbum (HTTP 400).
        _, conteudo = abrir(x)
        r = self.post("/chat/getBase64FromMediaMessage", {"message": {"key": x["key"], "message": conteudo}, "convertToMp4": False}, 300)
        return base64.b64decode(r["base64"])

    def conversas(self):
        r = self.post("/chat/findChats", {})
        return r if isinstance(r, list) else []

    def grupos(self):
        r = self.get("/group/fetchAllGroups", "?getParticipants=false", 180)
        return r if isinstance(r, list) else []


def _b64(arquivo) -> str:
    return base64.b64encode(Path(arquivo).read_bytes()).decode()


def evolution_agente(cfg) -> Evolution:
    return Evolution(cfg["agente"]["instancia"])


def evolution_dono(cfg):
    """O número do dono é opcional. Sem ele, os avisos olham o próprio número do agente."""
    instancia = cfg["dono"].get("instancia")
    if not instancia:
        return None
    url, chave = segredo("DONO_EVOLUTION_URL"), segredo("DONO_EVOLUTION_API_KEY")
    if bool(url) != bool(chave):   # senão a chave do agente iria para o servidor do dono
        raise ErroConfig("Preencha DONO_EVOLUTION_URL e DONO_EVOLUTION_API_KEY juntas, ou deixe as duas em branco.")
    return Evolution(instancia, url, chave)


# ---------- Claude ----------

def claude_cmd() -> list:
    if os.environ.get("SHEEP_ZAP_CLAUDE"):
        return [p.strip('"') for p in shlex.split(os.environ["SHEEP_ZAP_CLAUDE"], posix=not NO_WINDOWS)]
    achado = shutil.which("claude.exe") or shutil.which("claude") or shutil.which("claude.cmd")
    for extra in (Path.home() / ".local" / "bin" / "claude.exe", Path.home() / ".local" / "bin" / "claude"):
        achado = achado or (str(extra) if extra.exists() else None)
    if not achado:
        raise ErroConfig("Não achei o Claude Code neste computador. Instale e faça login antes de ligar o WhatsApp.")
    return [achado]


def pasta_neutra() -> Path:
    """Fora de qualquer projeto: sem CLAUDE.md por perto, quem só decide não leva a vida do dono no contexto."""
    p = Path(tempfile.gettempdir()) / "sheep-zap-neutra"
    p.mkdir(exist_ok=True)
    return p


def ambiente() -> dict:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "SHEEP_ZAP_HOME": str(casa())}
    # --setting-sources local ignora o settings.json do usuário, onde pode estar a chave de API: trago só o bloco env.
    bloco = ler_json(Path.home() / ".claude" / "settings.json", {})
    if isinstance(bloco, dict) and isinstance(bloco.get("env"), dict):
        env.update({k: str(v) for k, v in bloco["env"].items()})
    return env


def pensar(entrada: str, regras: Path, modelo: str, tempo=120) -> str:
    """Modelo só para decidir: sem ferramentas, sem memória, sem CLAUDE.md. Devolve o texto puro."""
    cmd = claude_cmd() + ["-p", "--strict-mcp-config", "--no-session-persistence", "--model", modelo, "--tools", "",
                          "--setting-sources", "local", "--system-prompt-file", str(regras)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace",
                         cwd=pasta_neutra(), env=ambiente(), creationflags=SEM_JANELA, start_new_session=not NO_WINDOWS)
    try:
        saida, _ = p.communicate(entrada, timeout=tempo)
        return saida or ""
    except subprocess.TimeoutExpired:
        matar(p.pid)   # derruba a árvore toda: um neto do claude.cmd seguraria o pipe e congelaria este laço
        try:
            p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise


def extrair_json(texto: str) -> dict:
    achado = re.search(r"\{.*\}", texto or "", re.S)
    if not achado:
        raise ValueError("resposta sem JSON")
    return json.loads(achado.group(0))
