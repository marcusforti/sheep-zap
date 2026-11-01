"""Evolution de mentira, no formato medido na real (Evolution v2.3.7, 01/11/2026):
- o que o dono manda fica em <lid>@lid; o que sai para ele fica em <numero>@s.whatsapp.net;
- a situação de entrega mora em MessageUpdate, não em status;
- mídia de álbum vem em associatedChildMessage e getBase64 recusa quando vem só o id."""
import base64
import json
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Falsa:
    def __init__(self):
        self.mensagens, self.enviadas, self.pedidos = [], [], []
        self.estado = "open"
        self.falhas_de_envio = 0
        self.entrega = "DELIVERY_ACK"
        self.conversas, self.grupos = [], []
        falsa = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _responder(self, dados, codigo=200):
                corpo = json.dumps(dados).encode()
                self.send_response(codigo)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(corpo)))
                self.end_headers()
                self.wfile.write(corpo)

            def do_GET(self):
                falsa.pedidos.append(("GET", self.path, None))
                if self.headers.get("apikey") != "chave-de-teste":
                    return self._responder({"erro": "auth"}, 401)
                if self.path.startswith("/instance/connectionState/"):
                    return self._responder({"instance": {"instanceName": self.path.rsplit("/", 1)[1], "state": falsa.estado}})
                if self.path.startswith("/group/fetchAllGroups/"):
                    return self._responder(falsa.grupos)
                self._responder({"erro": "rota"}, 404)

            def do_POST(self):
                corpo = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
                falsa.pedidos.append(("POST", self.path, corpo))
                if self.headers.get("apikey") != "chave-de-teste":
                    return self._responder({"erro": "auth"}, 401)
                rota = self.path.rsplit("/", 1)[0]
                if rota == "/chat/findMessages":
                    return self._responder(falsa.buscar(corpo))
                if rota in ("/message/sendText", "/message/sendWhatsAppAudio", "/message/sendMedia", "/message/sendPoll"):
                    if rota == "/message/sendWhatsAppAudio" and str(corpo.get("number")).endswith("@lid"):
                        return self._responder({"erro": "Bad Request"}, 400)   # medido na real em 01/11/2026
                    if falsa.falhas_de_envio > 0:
                        falsa.falhas_de_envio -= 1
                        return self._responder({"erro": "fora do ar"}, 503)
                    return self._responder(falsa.enviar(rota, corpo), 201)
                if rota == "/chat/getBase64FromMediaMessage":
                    m = corpo.get("message") or {}
                    if not m.get("message"):
                        return self._responder({"erro": "Bad Request"}, 400)
                    return self._responder({"base64": base64.b64encode(b"arquivo-falso").decode(), "mimetype": "image/jpeg"})
                if rota == "/chat/findChats":
                    return self._responder(falsa.conversas)
                self._responder({"erro": "rota"}, 404)

        self.servidor = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.servidor.server_address[1]}"
        threading.Thread(target=self.servidor.serve_forever, daemon=True).start()

    def fechar(self):
        self.servidor.shutdown()
        self.servidor.server_close()

    def buscar(self, corpo):
        chave = ((corpo.get("where") or {}).get("key")) or {}
        regs = self.mensagens
        if "remoteJid" in chave:
            regs = [x for x in regs if (x.get("key") or {}).get("remoteJid") == chave["remoteJid"]]
        if "id" in chave:
            regs = [x for x in regs if (x.get("key") or {}).get("id") == chave["id"]]
        regs = sorted(regs, key=lambda x: x.get("messageTimestamp") or 0, reverse=True)
        n, p = int(corpo.get("offset") or 50), int(corpo.get("page") or 1)
        return {"messages": {"total": len(regs), "pages": 1, "currentPage": p, "records": regs[(p - 1) * n:p * n]}}

    def enviar(self, rota, corpo):
        destino = str(corpo.get("number"))
        jid = destino if "@" in destino else destino + "@s.whatsapp.net"
        mid = "SAIDA" + uuid.uuid4().hex[:10]
        tipo = {"/message/sendText": "conversation", "/message/sendWhatsAppAudio": "audioMessage", "/message/sendMedia": "imageMessage",
                "/message/sendPoll": "pollCreationMessage"}[rota]
        texto = corpo.get("text") or corpo.get("name") or ""
        registro = {"key": {"id": mid, "fromMe": True, "remoteJid": jid}, "pushName": "", "messageType": tipo,
                    "message": {"conversation": texto} if tipo == "conversation" else {tipo: {}},
                    "messageTimestamp": int(time.time()), "MessageUpdate": [{"status": "SERVER_ACK"}, {"status": self.entrega}]}
        self.mensagens.append(registro)
        self.enviadas.append({"para": destino, "rota": rota, "texto": texto, "id": mid})
        return {"key": {"id": mid, "fromMe": True, "remoteJid": jid}, "status": "PENDING"}

    def chega(self, jid, texto="", alt=None, nome="Pessoa", ts=None, tipo="conversation", mensagem=None, participante=None, participante_alt=None):
        chave = {"id": "ENTRA" + uuid.uuid4().hex[:10], "fromMe": False, "remoteJid": jid, "participant": participante or ""}
        if alt:
            chave["remoteJidAlt"] = alt
        if participante_alt:
            chave["participantAlt"] = participante_alt
        registro = {"key": chave, "pushName": nome, "messageType": tipo, "message": mensagem or {"conversation": texto},
                    "messageTimestamp": ts or int(time.time()), "MessageUpdate": []}
        self.mensagens.append(registro)
        return registro
