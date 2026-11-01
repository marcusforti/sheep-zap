# Problemas

Comece sempre por `python "SCRIPTS/confere.py"` e `python "SCRIPTS/ligar.py" status`. Os registros ficam em `logs/`, na pasta do serviço.

| O que acontece | Causa provável | O que fazer |
|---|---|---|
| Agente não responde nada | Serviço parado ou computador dormiu | `ligar.py status`, depois `ligar.py`. Veja `logs/chat.saida.txt` |
| Aparece conectado, mas nada chega | A Evolution mostra `open` depois de cair com 401. Já aconteceu por horas | Rode `confere.py --envio`. Se não vier `entregue`, leia o QR Code de novo na Evolution |
| `HTTP 401` | Chave errada, ou o WhatsApp derrubou a sessão | Veja no `confere.py` de onde a chave veio. O `.env` da pasta do serviço vale mais que variável do computador e que Conexões. Se a chave estiver certa, leia o QR Code de novo |
| `no servidor` ou `aceito` por muito tempo | A pessoa está sem internet, ou o número está com problema | Não diga que foi entregue. Mande um teste ao dono: se também não chegar, o problema é do número |
| Respostas em dobro | Dois serviços no mesmo número, geralmente o WhatsApp do painel da Sheep também ligado | Desligue um deles |
| "Vi N mensagens de quando eu estava fora" | Computador ficou desligado. Mensagem com mais de 30 minutos não vira trabalho sozinha | É proteção. Mande de novo o que ainda precisar |
| Serviço "ligado", mas "sem sinal há X min" | O programa travou | `ligar.py reiniciar` |
| Mensagem no meio de uma queda de internet | Resposta pronta fica guardada e insiste por até um dia | Espere voltar. O texto também fica em `agentes/` |
| "Peguei", mas a resposta não vem | Cópia ainda rodando, travada ou freada | Mande `status`. Veja a pasta `agentes/` |
| "Deu ruim no pedido" | A cópia saiu com erro | Abra o `.err` mais novo em `agentes/`. Costuma ser login, plano no limite ou chave sem crédito |
| Freio ligado | Bateu `pedidos_por_dia` | Mande `solta o freio`, ou aumente o limite |
| Não acha o Claude | Instalado sem PATH | Abra `claude` no terminal uma vez. Veja se existe em `~/.local/bin` |
| Claude "not logged in" no serviço | Login expirou | Rode `claude` no terminal e entre de novo |
| Código do dono não encontrado | Mandou de outro número, num grupo, ou a mensagem ainda não chegou | Espere 1 minuto e tente de novo. Precisa ser conversa direta, do número informado |
| Áudio não transcreve | Sem faster-whisper e sem ElevenLabs | Veja a etapa 7 da instalação |
| Computador lento, CPU em 100% | Transcrição de muitos áudios, porque os avisos transcrevem o que chega | Troque `whisper` por `base` ou `tiny` em `zap.json` e reinicie |
| Voz dá HTTP 402 ou 404 | Sem crédito, ou a voz não está na conta | Adicione a voz em Minhas Vozes ou troque `voz.agente` em `zap.json` |
| Palavra falada errado | Faltou no dicionário | Acrescente em `pronuncia.json` |
| Foto de álbum não abre | Versão antiga da Evolution | Atualize a Evolution. Testado na v2.3.7 |
| Grupo não responde | Regras muito fechadas, `pausado.flag`, limite por hora ou número fora do grupo. A resposta leva mais de 1 minuto, de propósito | Veja `logs/grupo.jsonl`. Teste com `grupo.py --simular` |
| Grupo responde demais | Regras muito abertas | Aperte "Quando responder" em `grupos/<nome>.md` |
| Resposta do grupo segurada | Texto com cara de chave ou grande demais | É a trava funcionando. Veja `logs/grupo.jsonl` |
| Número bloqueado | Mensagem em massa ou número novo muito ativo | Fale com o suporte do WhatsApp. Daí em diante, responda só a quem chamou, com intervalo |
| Janela preta piscando no Windows | Python antigo no autostart | Rode `ligar.py login off` e depois `login on` |

## Se nada resolver

1. Pare tudo: `ligar.py parar`.
2. Rode `confere.py --envio --modelos` e leia linha por linha.
3. Mostre ao dono o que falhou, sem mostrar chave nem conversa de terceiros.
