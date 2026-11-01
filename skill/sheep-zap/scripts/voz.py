"""Gera áudio com a voz do agente pela ElevenLabs e devolve o caminho do arquivo.
Uso: python voz.py nome "texto"  |  python voz.py --dono nome "texto" (voz clonada do dono, só com autorização dele)
Tags como [whispers] e [laughs] funcionam. pronuncia.json, na pasta do serviço, troca palavras antes de gerar."""
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

from nucleo import ErroConfig, casa, config, ler_json, segredo, sub


def falar(nome: str, texto: str, dono=False):
    cfg = config()
    chave = segredo("ELEVENLABS_API_KEY")
    if not chave:
        sys.exit("Falta ELEVENLABS_API_KEY. Cadastre em Conexões no painel da Sheep ou no arquivo .env da pasta do serviço.")
    voz = cfg["voz"]["dono"] if dono else (segredo("ELEVENLABS_VOZ") or cfg["voz"]["agente"])
    if not voz:
        sys.exit("Falta a voz clonada do dono em zap.json (voz.dono).")
    for palavra, fala in ler_json(casa() / "pronuncia.json", {}).items():
        texto = re.sub(rf"\b{re.escape(palavra)}\b", fala, texto)
    ajuste = dict(stability=0.7, similarity_boost=0.8, style=0.05) if dono else dict(stability=0.3, similarity_boost=0.8, style=0.55)
    corpo = json.dumps({"text": texto, "model_id": cfg["voz"]["modelo"], "voice_settings": ajuste}).encode("utf-8")
    pedido = urllib.request.Request("https://api.elevenlabs.io/v1/text-to-speech/" + urllib.parse.quote(voz, safe=""), data=corpo, method="POST",
                                    headers={"xi-api-key": chave, "Content-Type": "application/json"})
    saida = sub("audios") / f"{re.sub(r'[^A-Za-z0-9_-]', '_', nome)}.mp3"
    try:
        with urllib.request.urlopen(pedido, timeout=180) as r:
            saida.write_bytes(r.read())
    except urllib.error.HTTPError as e:
        dica = {401: "a chave foi recusada", 402: "acabaram os créditos ou esta voz exige plano pago", 404: "essa voz não está na sua conta: adicione em Minhas Vozes ou troque voz.agente em zap.json"}.get(e.code, "")
        sys.exit(f"A ElevenLabs recusou o áudio (HTTP {e.code}). {dica}")
    return saida


if __name__ == "__main__":
    args = sys.argv[1:]
    dono = "--dono" in args
    args = [a for a in args if a != "--dono"]
    if len(args) != 2:
        sys.exit(__doc__)
    try:
        print(falar(args[0], args[1], dono))
    except ErroConfig as erro:
        sys.exit(str(erro))
