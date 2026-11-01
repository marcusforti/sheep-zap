import json
import time
from pathlib import Path

from base import GRUPO, JID_NUM, LID, Mundo, NUM


class TestGrupo(Mundo):
    def vigia(self, d=None):
        from grupo import Vigia
        g = {"nome": "Turma Um", "jid": GRUPO, "ligado": True}
        self.cfg["grupos"] = [g]
        import configurar
        configurar.gravar_config(self.cfg)
        configurar.preparar(self.cfg)
        pensar = (lambda *a, **k: json.dumps(d)) if d is not None else None
        kw = {"pensar_": pensar} if pensar else {}
        v = Vigia(self.cfg, self.evo, g, esperar=lambda s: None, **kw)
        v.e["desde"] = int(time.time()) - 5
        return v

    def fala(self, texto="como faço?", **k):
        return self.falsa.chega(GRUPO, texto, nome="Ana", participante="777@lid", participante_alt="5500922222222@s.whatsapp.net", **k)

    def test_responde_no_grupo(self):
        v = self.vigia({"responder": True, "texto": "🐑 Ana, assim.", "avisar_dono": ""})
        self.fala()
        v.passo()
        self.assertEqual([(e["para"], e["texto"]) for e in self.falsa.enviadas], [(GRUPO, "🐑 Ana, assim.")])

    def test_fica_quieta_quando_decide_nao_responder(self):
        v = self.vigia({"responder": False, "texto": "", "avisar_dono": ""})
        self.fala("kkk")
        v.passo()
        self.assertEqual(self.falsa.enviadas, [])

    def test_texto_com_cara_de_chave_nao_sai(self):
        for ruim in ("toma sk-abc123456789", "ANTHROPIC_API_KEY=xx", "o servidor é 10.0.0.1:8080", "API_KEY: oi"):
            self.falsa.enviadas.clear()
            v = self.vigia({"responder": True, "texto": ruim, "avisar_dono": ""})
            self.fala()
            v.passo()
            self.assertEqual([e["para"] for e in self.falsa.enviadas], [NUM], ruim)

    def test_chave_com_sublinhado_e_ip_sem_porta_nao_saem(self):
        v = self.vigia({"responder": True, "texto": "x", "avisar_dono": ""})
        self.assertTrue(v.tem_dado_sensivel("sk_live_abc123456789"))
        self.assertTrue(v.tem_dado_sensivel("o ip é 10.0.0.1"))

    def test_texto_bloqueado_nao_fica_no_registro(self):
        v = self.vigia({"responder": True, "texto": "toma sk-abc123456789", "avisar_dono": ""})
        self.fala()
        v.passo()
        self.assertNotIn("sk-abc", (self.nucleo.casa() / "logs" / "grupo.jsonl").read_text(encoding="utf-8"))

    def test_rede_caiu_a_resposta_ao_grupo_tenta_de_novo(self):
        v = self.vigia({"responder": True, "texto": "🐑 Ana, assim.", "avisar_dono": ""})
        self.fala()
        self.falsa.falhas_de_envio = 1
        v.passo()
        self.assertEqual(self.falsa.enviadas, [])
        v.passo()
        self.assertEqual([e["para"] for e in self.falsa.enviadas], [GRUPO])

    def test_falha_no_aviso_nao_derruba_a_resposta_ao_grupo(self):
        v = self.vigia({"responder": True, "texto": "🐑 Ana, assim.", "avisar_dono": "olha isso"})
        self.fala()
        self.falsa.falhas_de_envio = 1
        v.passo()
        self.assertEqual([e["para"] for e in self.falsa.enviadas], [GRUPO])

    def test_avisos_ao_dono_tem_limite_por_hora(self):
        v = self.vigia()
        for i in range(10):
            v.avisar_dono(f"aviso {i}")
        self.assertEqual(len(self.falsa.enviadas), 6)

    def test_duas_mensagens_no_mesmo_segundo_nao_se_perdem(self):
        v = self.vigia({"responder": False, "texto": "", "avisar_dono": ""})
        agora = int(time.time())
        self.fala("primeira", ts=agora)
        v.passo()
        self.fala("segunda", ts=agora)
        self.assertEqual(len(v.filtrar(self.evo.mensagens(GRUPO, 40))), 1)

    def test_nome_so_de_emoji_nao_divide_regras(self):
        from grupo import slug
        self.assertNotEqual(slug("🔥🔥", "120000000000000001@g.us"), slug("🚀", "120000000000000002@g.us"))

    def test_endereco_da_evolution_nao_sai(self):
        v = self.vigia({"responder": True, "texto": "x", "avisar_dono": ""})
        v.proibido_extra = "meu-servidor.com"
        self.assertTrue(v.tem_dado_sensivel("abre meu-servidor.com aí"))

    def test_texto_grande_nao_sai(self):
        v = self.vigia({"responder": True, "texto": "a" * 1101, "avisar_dono": ""})
        self.fala()
        v.passo()
        self.assertNotIn(GRUPO, [e["para"] for e in self.falsa.enviadas])

    def test_limite_por_hora(self):
        v = self.vigia({"responder": True, "texto": "🐑 oi", "avisar_dono": ""})
        v.e["envios"] = [time.time() - 10] * 6
        self.fala()
        v.passo()
        self.assertNotIn(GRUPO, [e["para"] for e in self.falsa.enviadas])
        self.assertIn("limite", self.textos()[-1])

    def test_limite_por_dia(self):
        v = self.vigia({"responder": True, "texto": "🐑 oi", "avisar_dono": ""})
        v.e["envios"] = [time.time() - 7200] * 30
        self.fala()
        v.passo()
        self.assertNotIn(GRUPO, [e["para"] for e in self.falsa.enviadas])

    def test_chama_o_dono_quando_o_assunto_e_dele(self):
        v = self.vigia({"responder": True, "texto": "🐑 Vou verificar.", "avisar_dono": "Ana perguntou a data"})
        self.fala("quando é o encontro?")
        v.passo()
        self.assertEqual({e["para"] for e in self.falsa.enviadas}, {GRUPO, NUM})

    def test_reconhece_o_dono_no_grupo_por_lid_ou_numero(self):
        v = self.vigia({"responder": False, "texto": "", "avisar_dono": ""})
        x = self.falsa.chega(GRUPO, "oi", nome="Apelido", participante=LID)
        self.assertIn("Dona:", v.linha(x))
        y = self.falsa.chega(GRUPO, "oi", nome="Apelido", participante="000@lid", participante_alt=JID_NUM)
        self.assertIn("Dona:", v.linha(y))
        z = self.fala()
        self.assertIn("Ana:", v.linha(z))

    def test_resposta_fora_do_formato_pula_depois_de_3_tentativas(self):
        v = self.vigia()
        v.pensar = lambda *a, **k: "isso não é json"
        self.fala()
        for _ in range(3):
            v.passo()
        self.assertTrue(v.e["desde"] >= int(time.time()) - 2)
        self.assertIn("pulei", self.textos()[-1])
        v.passo()
        self.assertEqual(len(self.textos()), 1)

    def test_roda_sem_ferramentas_e_fora_da_casa_do_dono(self):
        v = self.vigia()
        self.fala()
        v.passo()
        c = self.chamadas_feitas()[0]
        self.assertEqual(c["args"][c["args"].index("--tools") + 1], "")
        self.assertIn("sheep-zap-neutra", c["cwd"])
        self.assertIn("<mensagens>", c["entrada"])
        self.assertTrue(c["args"][c["args"].index("--system-prompt-file") + 1].endswith("turma-um.md"))


class TestAvisos(Mundo):
    def avisos(self):
        from avisos import Avisos
        return Avisos(self.cfg, self.evo, self.evo, desde=int(time.time()) - 5)

    def test_avisa_quem_escreveu_sem_ia(self):
        a = self.avisos()
        self.falsa.chega("777@lid", "preciso de um orçamento", alt="5500922222222@s.whatsapp.net", nome="Ana")
        self.falsa.chega("777@lid", "é urgente", alt="5500922222222@s.whatsapp.net", nome="Ana")
        a.passo()
        self.assertEqual(self.chamadas_feitas(), [])
        self.assertEqual(len(self.falsa.enviadas), 1)
        self.assertEqual(self.falsa.enviadas[0]["para"], NUM)
        self.assertIn("*Ana* (2): é urgente", self.textos()[0])
        linha = json.loads((Path(self.nucleo.casa()) / "terceiros.jsonl").read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(linha["jid"], "777@lid")
        self.assertEqual(linha["alt"], "5500922222222@s.whatsapp.net")

    def test_nao_avisa_grupo_nem_dono_nem_a_propria_voz(self):
        a = self.avisos()
        self.falsa.chega(GRUPO, "oi grupo", participante="777@lid")
        self.falsa.chega(LID, "sou o dono", alt=JID_NUM)
        self.falsa.chega("888@lid", "🐑 eco do agente", alt="5500933333333@s.whatsapp.net")
        self.falsa.chega("status@broadcast", "stories")
        a.passo()
        self.assertEqual(self.falsa.enviadas, [])

    def test_nao_avisa_o_dono_sobre_o_proprio_agente(self):
        self.cfg["agente"]["numero"] = "5500955555555"
        a = self.avisos()
        self.falsa.chega("555@lid", tipo="audioMessage", alt="5500955555555@s.whatsapp.net", mensagem={"audioMessage": {}})
        self.falsa.chega("5500955555555@s.whatsapp.net", "segunda parte de uma resposta longa, sem emoji")
        a.passo()
        self.assertEqual(self.falsa.enviadas, [])

    def test_arquivo_de_estranho_nao_e_baixado_pelos_avisos(self):
        a = self.avisos()
        self.falsa.chega("777@lid", tipo="documentMessage", mensagem={"documentMessage": {"fileName": "contrato.bat"}}, nome="Ana")
        a.passo()
        self.assertFalse(any("getBase64" in p[1] for p in self.falsa.pedidos))
        self.assertEqual(len(self.falsa.enviadas), 1)

    def test_mesmo_segundo_nao_perde_recado(self):
        a = self.avisos()
        agora = int(time.time())
        self.falsa.chega("777@lid", "primeiro", nome="Ana", ts=agora)
        a.passo()
        self.falsa.chega("888@lid", "segundo", nome="Bia", ts=agora)
        a.passo()
        self.assertIn("segundo", self.textos()[-1])

    def test_registro_sem_endereco_nao_trava_os_avisos(self):
        a = self.avisos()
        self.falsa.mensagens.append({"key": {"id": "X", "remoteJid": None}, "messageType": "conversation", "message": {"conversation": "oi"}, "messageTimestamp": int(time.time())})
        self.falsa.chega("777@lid", "oi", nome="Ana")
        a.passo()
        self.assertEqual(len(self.textos()), 1)

    def test_rede_caiu_o_recado_nao_se_perde(self):
        a = self.avisos()
        self.falsa.chega("777@lid", "oi", nome="Ana")
        self.falsa.falhas_de_envio = 1
        with self.assertRaises(OSError):
            a.passo()
        a.passo()
        self.assertEqual(len(self.textos()), 1)


class TestZap(Mundo):
    def test_ler_conversa_junta_lid_e_numero_da_pessoa(self):
        import zap
        self.falsa.chega("777@lid", "oi, tudo bem?", alt="5500922222222@s.whatsapp.net", nome="Ana", ts=int(time.time()) - 10)
        self.evo.texto("5500922222222", "tudo sim")
        achados = zap.enderecos(self.evo, "5500922222222@s.whatsapp.net")
        self.assertEqual(achados, {"777@lid", "5500922222222@s.whatsapp.net"})
        self.assertEqual(zap.enderecos(self.evo, "777@lid"), achados)
        linhas = zap.conversa(self.evo, "777@lid", 0)
        self.assertEqual(len(linhas), 2)
        self.assertIn("oi, tudo bem?", linhas[0])
        self.assertIn("tudo sim", linhas[1])

    def test_situacao_de_entrega_le_message_update(self):
        s = self.nucleo.status_entrega
        self.assertEqual(s({"MessageUpdate": [{"status": "SERVER_ACK"}, {"status": "DELIVERY_ACK"}, {"status": "READ"}], "status": None}), "lido")
        self.assertEqual(s({"MessageUpdate": [{"status": "DELIVERY_ACK"}]}), "entregue")
        self.assertEqual(s({"MessageUpdate": [{"status": "SERVER_ACK"}]}), "no servidor")
        self.assertEqual(s({"MessageUpdate": [{"status": "ERROR"}]}), "erro")
        self.assertEqual(s({"status": "PENDING", "MessageUpdate": []}), "aceito")

    def test_envio_confere_entrega_de_verdade(self):
        import zap
        self.cfg["limites"]["segundos_entre_envios"] = 0
        import builtins
        saida = []
        velho = builtins.print
        builtins.print = lambda *a, **k: saida.append(" ".join(map(str, a)))
        try:
            velho_conf = zap.conferir
            zap.conferir = lambda e, m, **k: velho_conf(e, m, tentativas=2, pausa=0)
            zap.enviar(self.cfg, self.evo, "5500922222222", "texto", ["oi"])
            self.falsa.entrega = "SERVER_ACK"
            zap.enviar(self.cfg, self.evo, "5500922222222", "texto", ["oi 2"])
        finally:
            builtins.print = velho
            zap.conferir = velho_conf
        self.assertTrue(saida[0].startswith("entregue"))
        self.assertTrue(saida[1].startswith("no servidor"))
        self.assertIn("sem prova", saida[1])

    def test_nao_envia_com_instancia_desconectada(self):
        import zap
        self.falsa.estado = "close"
        with self.assertRaises(SystemExit) as c:
            zap.enviar(self.cfg, self.evo, "5500922222222", "texto", ["oi"])
        self.assertIn("close", str(c.exception))
        self.assertEqual(self.falsa.enviadas, [])

    def test_envia_picado(self):
        import zap
        self.cfg["limites"]["segundos_entre_envios"] = 1
        inicio = time.time()
        zap._no_ritmo(self.cfg, self.evo)
        zap._no_ritmo(self.cfg, self.evo)
        self.assertGreaterEqual(time.time() - inicio, 0.9)

    def test_grupo_nao_finge_confirmacao(self):
        import builtins
        import zap
        self.cfg["limites"]["segundos_entre_envios"] = 0
        saida = []
        velho = builtins.print
        builtins.print = lambda *a, **k: saida.append(" ".join(map(str, a)))
        try:
            zap.enviar(self.cfg, self.evo, GRUPO, "texto", ["oi"])
        finally:
            builtins.print = velho
        self.assertIn("confira no celular", saida[0])

    def test_mesmo_processo_nao_duplica_servico(self):
        a = self.nucleo.trava("chat")
        self.addCleanup(lambda: self.nucleo.soltar_trava(a))
        self.assertIsNotNone(a)
        self.assertIsNone(self.nucleo.trava("chat"))
        self.assertTrue(self.nucleo.rodando("chat"))

    def test_chave_da_api_vinda_do_painel_da_sheep(self):
        import os
        cofre = Path(os.environ["SHEEP_HOME"]).parent / ".sheep-cofre"
        cofre.mkdir(exist_ok=True)
        (cofre / "ELEVENLABS_API_KEY").write_text("do-painel", encoding="utf-8")
        self.assertEqual(self.nucleo.segredo("ELEVENLABS_API_KEY"), "do-painel")

    def test_env_do_servico_vence_variavel_do_computador(self):
        (self.nucleo.casa() / ".env").write_text("EVOLUTION_API_KEY=do-arquivo\n", encoding="utf-8")
        self.assertEqual(self.nucleo.segredo("EVOLUTION_API_KEY"), "do-arquivo")
        self.assertEqual(self.nucleo.origem_segredo("EVOLUTION_API_KEY"), ".env da pasta do serviço")
        self.assertEqual(self.nucleo.origem_segredo("EVOLUTION_URL"), "variável de ambiente do computador")
        self.assertIsNone(self.nucleo.origem_segredo("NAO_EXISTE"))

    def test_settings_do_usuario_passa_a_chave_sem_o_arquivo(self):
        import os
        home = Path(os.environ["SHEEP_ZAP_HOME"]).parent / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "settings.json").write_text(json.dumps({"env": {"ANTHROPIC_BASE_URL": "https://revenda"}}), encoding="utf-8")
        velho = Path.home
        Path.home = classmethod(lambda c: home)
        try:
            self.assertEqual(self.nucleo.ambiente()["ANTHROPIC_BASE_URL"], "https://revenda")
        finally:
            Path.home = velho


class TestMidia(Mundo):
    def test_arquivo_de_estranho_nao_escapa_da_pasta_nem_vira_executavel(self):
        import midia
        x = self.falsa.chega("777@lid", tipo="documentMessage", mensagem={"documentMessage": {"fileName": "contrato.bat"}})
        x["key"]["id"] = "..\\..\\evil"
        arq = midia.baixar(x, self.evo)
        self.assertEqual(arq.parent, (self.nucleo.casa() / "midia").resolve())
        self.assertEqual(arq.suffix, ".bin")

    def test_pdf_continua_pdf(self):
        import midia
        x = self.falsa.chega("777@lid", tipo="documentMessage", mensagem={"documentMessage": {"fileName": "Proposta Final.PDF"}})
        self.assertEqual(midia.baixar(x, self.evo).suffix, ".pdf")


class TestConfigurar(Mundo):
    def test_dono_com_nono_digito_tirado_pelo_whatsapp_consegue_instalar(self):
        import configurar
        self.cfg["dono"].update(numero="5531999887766", jids=[])
        configurar.gravar_config(self.cfg)
        self.falsa.chega("123123@lid", "ZAP-1234", alt="553199887766@s.whatsapp.net")
        configurar.achar_dono("ZAP-1234")
        jids = self.nucleo.config()["dono"]["jids"]
        self.assertIn("123123@lid", jids)
        self.assertIn("553199887766@s.whatsapp.net", jids)
        self.assertIn("5531999887766@s.whatsapp.net", jids)

    def test_variantes_do_numero(self):
        v = self.nucleo.variantes
        self.assertEqual(v("5531999887766"), {"5531999887766", "553199887766"})
        self.assertEqual(v("553199887766@s.whatsapp.net"), {"5531999887766", "553199887766"})
        self.assertEqual(v("14155550100"), {"14155550100"})

    def test_agente_sem_pronuncia_nao_herda_a_da_sheep(self):
        import configurar
        cfg = self.nucleo._fundir(self.nucleo.PADRAO, {"agente": {"nome": "Bento"}, "dono": {"nome": "Dona"}})
        self.assertEqual(cfg["agente"]["pronuncia"], "")
        self.assertNotIn("fala-se", configurar.trocar("{{AGENTE}}{{FALA}}", cfg))

    def test_chave_do_agente_nao_vai_para_o_servidor_do_dono(self):
        import os
        self.cfg["dono"]["instancia"] = "dono"
        os.environ["DONO_EVOLUTION_URL"] = "http://outro-servidor"
        with self.assertRaises(self.nucleo.ErroConfig):
            self.nucleo.evolution_dono(self.cfg)

    def test_acha_o_dono_pela_palavra_e_guarda_os_dois_enderecos(self):
        import configurar
        self.falsa.chega(LID, "ZAP-1234", alt=JID_NUM)
        configurar.achar_dono("ZAP-1234")
        self.assertEqual(self.nucleo.config()["dono"]["jids"][:2], [LID, JID_NUM])

    def test_palavra_vinda_de_outro_numero_e_recusada(self):
        import configurar
        self.falsa.chega("999@lid", "ZAP-1234", alt="5500944444444@s.whatsapp.net")
        with self.assertRaises(SystemExit):
            configurar.achar_dono("ZAP-1234")

    def test_palavra_postada_em_grupo_nunca_vira_chat_do_dono(self):
        import configurar
        self.cfg["dono"]["jids"] = []
        configurar.gravar_config(self.cfg)
        self.falsa.chega(GRUPO, "ZAP-1234", participante=LID, participante_alt=JID_NUM)
        self.falsa.chega("status@broadcast", "ZAP-1234")
        with self.assertRaises(SystemExit):
            configurar.achar_dono("ZAP-1234")
        self.assertEqual(self.nucleo.config()["dono"]["jids"], [])

    def test_palavra_sem_numero_alternativo_nao_e_aceita_no_escuro(self):
        import configurar
        self.cfg["dono"]["jids"] = []
        configurar.gravar_config(self.cfg)
        self.falsa.chega("999@lid", "ZAP-1234")
        with self.assertRaises(SystemExit):
            configurar.achar_dono("ZAP-1234")
        self.assertEqual(self.nucleo.config()["dono"]["jids"], [])

    def test_prompts_ficam_sem_marcador_pendente(self):
        casa = self.nucleo.casa()
        for nome in ("AGENTE.md", "TRIAGEM.md"):
            self.assertNotIn("{{", (casa / "prompts" / nome).read_text(encoding="utf-8"), nome)

    def test_pasta_de_trabalho_nunca_cai_num_lugar_amplo(self):
        import configurar
        casa = self.nucleo.casa()
        self.assertEqual(configurar.pasta_padrao(casa), str(casa))
        (casa.parent / "CLAUDE.md").write_text("identidade", encoding="utf-8")
        self.assertEqual(configurar.pasta_padrao(casa), str(casa.parent))

    def test_nenhum_texto_assume_o_genero_do_agente_nem_manda_negar_ia(self):
        pasta = Path(__file__).resolve().parent.parent / "skill/sheep-zap/modelos"
        for nome in ("AGENTE.md", "GRUPO.md", "TRIAGEM.md"):
            texto = (pasta / nome).read_text(encoding="utf-8").lower()
            for ruim in ("dona das", "engraçada", "engraçadinha", "quieta", "carinhosa", "nunca diga que é ia"):
                self.assertNotIn(ruim, texto, nome)

    def test_nao_apaga_o_que_o_dono_editou(self):
        import configurar
        arq = self.nucleo.casa() / "prompts" / "AGENTE.md"
        arq.write_text("meu combinado", encoding="utf-8")
        configurar.preparar(self.cfg)
        self.assertEqual(arq.read_text(encoding="utf-8"), "meu combinado")

    def test_nao_sobrescreve_claude_md_existente(self):
        import configurar
        trabalho = Path(self.cfg["pasta_trabalho"])
        (trabalho / "CLAUDE.md").unlink(missing_ok=True)
        (trabalho / "AGENTS.md").write_text("casa existente", encoding="utf-8")
        configurar.preparar(self.cfg)
        self.assertFalse((trabalho / "CLAUDE.md").exists())
