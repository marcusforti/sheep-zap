"""Transforma mensagem em texto: baixa foto, vídeo e documento, e transcreve áudio.
Áudio usa o faster-whisper no computador, de graça. Sem ele, usa a ElevenLabs se houver chave.
Uso direto, para conferir um áudio antes de mandar: python midia.py arquivo.mp3"""
import json
import mimetypes
import re
import sys
import urllib.request
import uuid
from pathlib import Path

from nucleo import abrir, config, segredo, sub, texto_puro

EXT = {"audioMessage": ".ogg", "imageMessage": ".jpg", "videoMessage": ".mp4", "stickerMessage": ".webp"}
ROTULO = {"imageMessage": "📷 foto", "videoMessage": "🎬 vídeo"}
# Id e nome de arquivo vêm de quem mandou: nada de .bat na pasta do dono nem caminho que sai de midia/.
SEGURAS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".csv", ".jpg", ".jpeg", ".png", ".webp", ".heic", ".gif",
           ".mp3", ".m4a", ".ogg", ".oga", ".wav", ".opus", ".mp4", ".mov", ".webm", ".zip"}
_modelo = None


def caminho_seguro(x, tipo, corpo) -> Path:
    pasta = sub("midia").resolve()
    nome = re.sub(r"[^A-Za-z0-9_-]", "", str(x["key"]["id"]))[:80] or uuid.uuid4().hex
    ext = EXT.get(tipo) or Path(str(corpo.get("fileName") or "")).suffix.lower()
    arq = (pasta / f"{nome}{ext if ext in SEGURAS else '.bin'}").resolve()
    if arq.parent != pasta:
        raise ValueError("nome de arquivo inválido")
    return arq


def baixar(x, evo) -> Path:
    tipo, m = abrir(x)
    corpo = m.get(tipo) if isinstance(m.get(tipo), dict) else {}
    arq = caminho_seguro(x, tipo, corpo)
    if not arq.exists():
        arq.write_bytes(evo.baixar(x))
    return arq


def _whisper(arq: Path) -> str:
    global _modelo
    from faster_whisper import WhisperModel
    try:
        tamanho = config()["whisper"]
    except Exception:
        tamanho = "small"
    _modelo = _modelo or WhisperModel(tamanho, device="cpu", compute_type="int8")
    trechos, _ = _modelo.transcribe(str(arq), language="pt")
    return " ".join(t.text.strip() for t in trechos).strip()


def _elevenlabs(arq: Path, chave: str) -> str:
    limite = "sheepzap" + uuid.uuid4().hex
    partes = [f'--{limite}\r\nContent-Disposition: form-data; name="{n}"\r\n\r\n{v}\r\n'.encode() for n, v in (("model_id", "scribe_v1"), ("language_code", "por"))]
    mime = mimetypes.guess_type(arq.name)[0] or "application/octet-stream"
    partes.append(f'--{limite}\r\nContent-Disposition: form-data; name="file"; filename="audio{arq.suffix}"\r\nContent-Type: {mime}\r\n\r\n'.encode())
    partes += [arq.read_bytes(), f"\r\n--{limite}--\r\n".encode()]
    pedido = urllib.request.Request("https://api.elevenlabs.io/v1/speech-to-text", data=b"".join(partes),
                                    headers={"xi-api-key": chave, "Content-Type": "multipart/form-data; boundary=" + limite})
    with urllib.request.urlopen(pedido, timeout=180) as r:
        return (json.loads(r.read()).get("text") or "").strip()


def transcrever(arq: Path) -> str:
    arq = Path(arq)
    txt = arq.with_suffix(".txt")
    if txt.exists():
        return txt.read_text(encoding="utf-8")
    try:
        texto = _whisper(arq)
    except ImportError:
        chave = segredo("ELEVENLABS_API_KEY")
        if not chave:
            raise RuntimeError("não sei ouvir áudio ainda: falta o faster-whisper ou a chave da ElevenLabs") from None
        texto = _elevenlabs(arq, chave)
    texto = texto or "(áudio sem fala)"
    txt.write_text(texto, encoding="utf-8")
    return texto


def conteudo(x, evo) -> str:
    """Texto da mensagem. Áudio vira transcrição; mídia vira o caminho do arquivo, para o agente abrir."""
    tipo, m = abrir(x)
    texto = texto_puro(x)
    try:
        if tipo == "audioMessage":
            return "🎤 " + transcrever(baixar(x, evo))
        if tipo in ROTULO or tipo == "documentMessage":
            corpo = m.get(tipo) or {}
            nome = ROTULO.get(tipo) or "📄 " + (corpo.get("fileName") or "arquivo")
            return f"{nome}{': ' + texto if texto else ''} [arquivo: {baixar(x, evo)}]"
    except Exception as erro:
        return f"[{tipo} que não consegui abrir: {erro}]" + (f" {texto}" if texto else "")
    return texto or f"[{tipo}]"


def resumo(x) -> str:
    """Só para contexto: não baixa nada."""
    tipo, _ = abrir(x)
    return texto_puro(x) or {"audioMessage": "[áudio]", "imageMessage": "[foto]", "videoMessage": "[vídeo]", "documentMessage": "[arquivo]"}.get(tipo, f"[{tipo}]")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(transcrever(Path(sys.argv[1]).resolve()))
