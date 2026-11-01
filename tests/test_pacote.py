"""Confere o pacote que vai para o GitHub: nada pessoal, instalador funcionando e serviço ligando de verdade."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from base import RAIZ, GRUPO, LID, Mundo, JID_NUM

PROIBIDOS = [
    (r"\b55\d{10,11}\b", "telefone real"),
    (r"\b\d{12,}@(lid|s\.whatsapp\.net|g\.us)\b", "jid real"),
    (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "ip"),
    (r"sk-[A-Za-z0-9_-]{16,}|xi-api-key:\s*[a-z0-9]{20,}", "chave"),
]
# Nomes de pessoas, contas e caminhos reais ficam num arquivo que não vai para o GitHub.
LOCAL = Path(__file__).with_name("proibidos.local.txt")
if LOCAL.exists():
    PROIBIDOS += [("(?i)" + l, "item da lista local") for l in LOCAL.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
# Só exemplos que não podem ser de ninguém: DDD 00 não existe, e o resto são os valores inventados dos testes e da documentação.
LIBERADOS = {"127.0.0.1", "10.0.0.1", "5511999999999", "5531999887766", "553199887766", "553199887766@s.whatsapp.net", "5531999887766@s.whatsapp.net",
             "111222333444555@lid", "120000000000000001@g.us", "120000000000000002@g.us"}
FALSO = re.compile(r"^5500\d{9}(@s\.whatsapp\.net)?$")


def arquivos():
    # Fonte, imagem e biblioteca de terceiros não têm texto nosso: varrer só daria falso alarme.
    for p in RAIZ.rglob("*"):
        if p.is_file() and not {"__pycache__", ".git", "graphify-out", "fontes", "img", "vendor"} & set(p.parts) and p.suffix != ".pyc":
            yield p


class TestSemDadosPessoais(unittest.TestCase):
    def test_nada_pessoal_no_pacote(self):
        achados = []
        for p in arquivos():
            if p.name in ("test_pacote.py", "proibidos.local.txt"):
                continue
            texto = p.read_text(encoding="utf-8", errors="replace")
            for padrao, nome in PROIBIDOS:
                for m in re.finditer(padrao, texto):
                    if m.group(0) not in LIBERADOS and not FALSO.match(m.group(0)):
                        achados.append(f"{p.relative_to(RAIZ)}: {nome}: {m.group(0)}")
        self.assertEqual(achados, [])

    def test_lista_local_fica_fora_do_git(self):
        self.assertIn("tests/proibidos.local.txt", (RAIZ / ".gitignore").read_text(encoding="utf-8"))
        texto = Path(__file__).read_text(encoding="utf-8").lower()
        for linha in (LOCAL.read_text(encoding="utf-8").splitlines() if LOCAL.exists() else []):
            if linha.strip() and not linha.startswith("#") and "\\" not in linha and "(" not in linha:
                self.assertNotIn(linha.lower(), texto)

    def test_pagina_aponta_para_o_que_existe(self):
        pasta = RAIZ / "docs"
        html = (pasta / "index.html").read_text(encoding="utf-8")
        for alvo in re.findall(r'(?:src|href)="([^"#:]+)"', html) + re.findall(r'url\(([^)#:]+?)\)', html):
            self.assertTrue((pasta / alvo).exists(), alvo)
        self.assertIn("marcusforti/sheep-zap/main/instalar.ps1", html)
        self.assertIn("marcusforti/sheep-zap/main/instalar.sh", html)

    def test_skill_tem_nome_e_descricao_validos(self):
        cabeca = (RAIZ / "skill/sheep-zap/SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertIn("name: sheep-zap", cabeca)
        descricao = re.search(r"description: (.+)", cabeca).group(1)
        self.assertLess(len(cabeca), 1024)
        self.assertTrue(descricao.startswith("Use quando"))

    def test_referencias_citadas_existem(self):
        pasta = RAIZ / "skill/sheep-zap"
        for nome in re.findall(r"`references/([a-z]+\.md)`", (pasta / "SKILL.md").read_text(encoding="utf-8")):
            self.assertTrue((pasta / "references" / nome).exists(), nome)

    def test_comandos_citados_existem(self):
        pasta = RAIZ / "skill/sheep-zap"
        textos = [(pasta / "SKILL.md").read_text(encoding="utf-8")] + [p.read_text(encoding="utf-8") for p in (pasta / "references").glob("*.md")]
        for nome in set(re.findall(r"SCRIPTS/([a-z]+\.py)", "\n".join(textos))):
            self.assertTrue((pasta / "scripts" / nome).exists(), nome)


@unittest.skipUnless(os.name == "nt", "instalador do Windows")
class TestInstaladorWindows(unittest.TestCase):
    def test_instala_e_reinstala_sem_tocar_na_pasta_do_servico(self):
        tmp = Path(tempfile.mkdtemp(prefix="szinst-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        (tmp / "Sheep").mkdir()
        env = {**os.environ, "USERPROFILE": str(tmp), "SHEEP_ZAP_ORIGEM": str(RAIZ), "SHEEP_HOME": str(tmp / "Sheep"), "TEMP": str(tmp)}
        servico = tmp / "Sheep" / "zap"
        servico.mkdir()
        (servico / "zap.json").write_text("{}", encoding="utf-8")
        for _ in range(2):
            r = subprocess.run(["pwsh", "-NoProfile", "-File", str(RAIZ / "instalar.ps1")], capture_output=True, text=True, env=env, timeout=120)
            self.assertIn("instalada", r.stdout, r.stdout + r.stderr)
        for alvo in (".claude/skills", ".agents/skills", "Sheep/.claude/skills", "Sheep/.agents/skills"):
            self.assertTrue((tmp / alvo / "sheep-zap" / "SKILL.md").exists(), alvo)
            self.assertTrue((tmp / alvo / "sheep-zap" / "scripts" / "chat.py").exists(), alvo)
        self.assertTrue((servico / "zap.json").exists())


class TestServicoDeVerdade(Mundo):
    """Liga os programas como processos soltos, igual em produção, contra a Evolution falsa."""

    def ligar(self, *args):
        return subprocess.run([sys.executable, str(RAIZ / "skill/sheep-zap/scripts/ligar.py"), *args], capture_output=True, text=True, encoding="utf-8", timeout=60, env=dict(os.environ, PYTHONIOENCODING="utf-8"))

    def test_liga_responde_nao_duplica_e_para(self):
        self.cfg["grupos"] = [{"nome": "Turma Um", "jid": GRUPO, "ligado": True}]
        self.cfg["intervalos"].update(chat=1, avisos=1, grupo=1, rajada_grupo=0)
        import configurar
        configurar.gravar_config(self.cfg)
        configurar.preparar(self.cfg)
        self.addCleanup(self.ligar, "parar")
        saida = self.ligar().stdout
        self.assertEqual(saida.count(": ligado"), 3, saida)
        self.assertEqual(self.ligar().stdout.count("já estava ligado"), 3)
        time.sleep(1.5)
        self.falsa.chega(LID, "tá aí?", alt=JID_NUM)
        self.assertTrue(self.esperar(lambda: "🐑 Tô aqui!" in self.textos(), 15), self.textos())
        self.assertEqual(self.ligar("status").stdout.count("ligado, processo"), 3)
        self.ligar("parar")
        self.assertTrue(self.esperar(lambda: self.ligar("status").stdout.count("parado") == 3, 10))

    @unittest.skipUnless(os.name == "nt", "atualizar por cima do serviço no Windows")
    def test_atualizar_com_o_servico_ligado_nao_destroi_a_skill(self):
        home = self.tmp / "home"
        home.mkdir()
        env = dict(os.environ, USERPROFILE=str(home), SHEEP_ZAP_ORIGEM=str(RAIZ), SHEEP_HOME=str(self.tmp / "sem-sheep"), TEMP=str(self.tmp))
        instalar = lambda: subprocess.run(["pwsh", "-NoProfile", "-File", str(RAIZ / "instalar.ps1")], capture_output=True, text=True, env=env, timeout=120).stdout
        self.assertIn("instalada", instalar())
        ligar = home / ".claude/skills/sheep-zap/scripts/ligar.py"
        self.cfg["intervalos"].update(chat=1, avisos=1)
        import configurar
        configurar.gravar_config(self.cfg)
        comando = lambda *a: subprocess.run([sys.executable, str(ligar), *a], capture_output=True, text=True, encoding="utf-8", timeout=60, env=dict(os.environ, PYTHONIOENCODING="utf-8")).stdout
        self.addCleanup(comando, "parar")
        self.assertEqual(comando().count(": ligado"), 2)
        self.assertIn("instalada", instalar())
        for nome in ("chat.py", "nucleo.py", "ligar.py"):
            self.assertTrue((ligar.parent / nome).exists(), nome)
        self.assertEqual(comando("status").count("ligado, processo"), 2)
        self.assertFalse((home / ".claude/skills/sheep-zap.velho").exists())

    def test_status_acusa_servico_vivo_mas_travado(self):
        import ligar
        tranca = self.nucleo.trava("chat")
        self.addCleanup(lambda: self.nucleo.soltar_trava(tranca))
        (self.nucleo.sub("run") / "chat.vivo").write_text(str(int(time.time()) - 3600), encoding="utf-8")
        import contextlib, io
        saida = io.StringIO()
        with contextlib.redirect_stdout(saida):
            ligar.status(self.cfg)
        self.assertIn("sem sinal há 60 min", saida.getvalue())

    @unittest.skipUnless(os.name == "nt", "autostart do Windows")
    def test_autostart_funciona_com_acento_e_espaco_no_caminho(self):
        casa = self.tmp / "João Çá" / "zap"
        casa.mkdir(parents=True)
        shutil.copy(Path(os.environ["SHEEP_ZAP_HOME"]) / "zap.json", casa / "zap.json")
        shutil.copytree(Path(os.environ["SHEEP_ZAP_HOME"]) / "prompts", casa / "prompts")
        os.environ.update(SHEEP_ZAP_HOME=str(casa), APPDATA=str(self.tmp / "appdata"))
        self.addCleanup(self.ligar, "parar")
        self.assertIn("ligado", self.ligar("login", "on").stdout)
        vbs = self.tmp / "appdata/Microsoft/Windows/Start Menu/Programs/Startup/sheep-zap.vbs"
        self.assertIn("João Çá", vbs.read_text(encoding="utf-16"))
        subprocess.run(["cscript", "//nologo", str(vbs)], capture_output=True, timeout=30, env=dict(os.environ))
        self.assertTrue(self.esperar(lambda: (casa / "run" / "chat.lock").exists() and self.nucleo.rodando("chat"), 15), "serviço não subiu pelo autostart")

    def test_sem_configurar_nenhum_comando_mostra_erro_tecnico(self):
        vazio = self.tmp / "vazio"
        vazio.mkdir()
        env = dict(os.environ, SHEEP_ZAP_HOME=str(vazio), PYTHONIOENCODING="utf-8")
        pasta = RAIZ / "skill/sheep-zap/scripts"
        for args in (["ligar.py", "status"], ["ligar.py"], ["zap.py", "dono", "texto", "oi"], ["voz.py", "a", "b"], ["grupo.py"], ["chat.py"], ["avisos.py"], ["configurar.py", "--ver"]):
            r = subprocess.run([sys.executable, str(pasta / args[0]), *args[1:]], capture_output=True, text=True, encoding="utf-8", timeout=30, env=env)
            self.assertNotIn("Traceback", r.stdout + r.stderr, args)
            self.assertIn("Ainda não configurei", r.stdout + r.stderr, args)

    def test_confere_aponta_o_que_falta_sem_mostrar_chave(self):
        r = subprocess.run([sys.executable, str(RAIZ / "skill/sheep-zap/scripts/confere.py"), "--envio"], capture_output=True, text=True, encoding="utf-8", timeout=90, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertNotIn("chave-de-teste", r.stdout + r.stderr)
        self.assertIn("Número do agente: conectado", r.stdout)
        self.assertIn("Teste de envio ao dono: entregue", r.stdout)
        self.assertIn("Chave da Evolution: variável de ambiente do computador", r.stdout)
        m = subprocess.run([sys.executable, str(RAIZ / "skill/sheep-zap/scripts/confere.py"), "--modelos"], capture_output=True, text=True, encoding="utf-8", timeout=90, env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        self.assertIn("Claude respondeu", m.stdout)
        self.assertEqual(self.falsa.enviadas[-1]["para"], self.cfg["dono"]["numero"])
