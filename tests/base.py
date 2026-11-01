"""Monta um mundo de teste: pasta própria, Evolution falsa e Claude falso. Nada sai daqui."""
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skill" / "sheep-zap" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from evolution_falsa import Falsa  # noqa: E402

LID, NUM = "111222333444555@lid", "5500900000001"
JID_NUM = NUM + "@s.whatsapp.net"
GRUPO = "120000000000000001@g.us"


class Mundo(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="sheepzap-"))
        self.falsa = Falsa()
        self.chamadas = self.tmp / "chamadas.jsonl"
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.addCleanup(self.falsa.fechar)
        self.velho = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.velho)))
        os.environ.update({"SHEEP_ZAP_HOME": str(self.tmp / "zap"), "SHEEP_HOME": str(self.tmp / "sem-sheep"), "EVOLUTION_URL": self.falsa.url, "EVOLUTION_API_KEY": "chave-de-teste",
                           "SHEEP_ZAP_CHAMADAS": str(self.chamadas), "SHEEP_ZAP_CLAUDE": f"{sys.executable} {Path(__file__).resolve().parent / 'claude_falso.py'}"})
        for nome in ("ELEVENLABS_API_KEY",):
            os.environ.pop(nome, None)
        import configurar
        import nucleo
        self.nucleo = nucleo
        self.cfg = nucleo._fundir(nucleo.PADRAO, {"agente": {"nome": "Sheep", "pronuncia": "Xíp", "emoji": "🐑", "instancia": "agente"},
                                                  "dono": {"nome": "Dona", "numero": NUM, "jids": [LID, JID_NUM]},
                                                  "pasta_trabalho": str(self.tmp / "trabalho")})
        (self.tmp / "trabalho").mkdir()
        configurar.gravar_config(self.cfg)
        configurar.preparar(self.cfg)
        self.evo = nucleo.Evolution("agente")

    def chamadas_feitas(self):
        if not self.chamadas.exists():
            return []
        return [json.loads(l) for l in self.chamadas.read_text(encoding="utf-8").splitlines() if l.strip()]

    def textos(self):
        return [e["texto"] for e in self.falsa.enviadas]

    def esperar(self, condicao, segundos=8):
        fim = time.time() + segundos
        while time.time() < fim:
            if condicao():
                return True
            time.sleep(0.05)
        return False
