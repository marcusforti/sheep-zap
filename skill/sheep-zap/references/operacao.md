# Operação do dia a dia

`SCRIPTS` é a pasta `scripts` da skill. A pasta do serviço aparece em `python "SCRIPTS/configurar.py" --ver` e no `confere.py`.

## O dono, pelo WhatsApp

| Escreve no número do agente | Acontece |
|---|---|
| `status` | Lista o que está rodando e o que espera |
| `cancela tudo` | Para as cópias e zera o que espera |
| `solta o freio` | Libera o limite do dia por 3 horas |
| A palavra `opus` ou `sonnet` no pedido | Força esse modelo naquele pedido |
| "responde lá, NOME, a pessoa X" | Áudio como o agente |
| "responde a msg da pessoa X" | Texto como o agente |
| "responde pra mim a pessoa X" | Áudio na voz do dono |
| "responde a msg pra mim da pessoa X" | Texto como o dono |

## Comandos

| Quero | Comando |
|---|---|
| Ver o que está ligado | `python "SCRIPTS/ligar.py" status` |
| Ligar o que faltar | `python "SCRIPTS/ligar.py"` |
| Parar tudo | `python "SCRIPTS/ligar.py" parar` |
| Aplicar mudança de configuração | `python "SCRIPTS/ligar.py" reiniciar` |
| Voltar sozinho no login, ou parar de voltar | `python "SCRIPTS/ligar.py" login on` ou `off` |
| Pausar só os grupos | Criar o arquivo `grupos/pausado.flag` na pasta do serviço |
| Provar que o envio funciona | `python "SCRIPTS/confere.py" --envio` |

## O que dá para mudar em `zap.json`

Reinicie depois de mudar. Esse arquivo não tem chave nenhuma.

| Campo | Para quê |
|---|---|
| `modelos.medio`, `modelos.avancado` | Modelo de cada nível. Para Opus em tudo, ponha `opus` nos dois |
| `limites.agentes_juntos` | Quantas cópias ao mesmo tempo. Computador fraco: deixe 1 ou 2 |
| `limites.minutos_por_agente` | Tempo máximo de um pedido |
| `limites.pedidos_por_dia` | Freio do dia, para não estourar o plano ou a chave |
| `limites.grupo_por_hora`, `limites.grupo_por_dia` | Quantas respostas no grupo |
| `pastas_extras` | Outras pastas que as cópias podem abrir |
| `voz.agente`, `voz.dono`, `voz.modelo` | Vozes da ElevenLabs |
| `whisper` | Modelo de transcrição. Computador lento: troque `small` por `base` ou `tiny`. Ouve pior, mas usa bem menos CPU |
| `grupos[].ligado` | `false` desliga um grupo sem apagar |

## Onde ficam as coisas (pasta do serviço)

| Arquivo | O que é |
|---|---|
| `prompts/AGENTE.md` | Como cada cópia trabalha. Edite à vontade: a reinstalação não mexe |
| `prompts/TRIAGEM.md` | Como o modelo pequeno separa recado de trabalho |
| `grupos/<nome>.md` | Regras de cada grupo. Vale na mensagem seguinte |
| `HANDOFF.md` | Pendências com pessoas, escritas pelas cópias |
| `terceiros.jsonl` | Quem escreveu, para achar o endereço de alguém |
| `pronuncia.json` | Palavras que a voz lê errado: `{"Sheep": "Xíp"}` |
| `logs/` | Registros de cada serviço |
| `agentes/` | Saída de cada cópia: `.txt` é a resposta, `.err` são avisos técnicos |
| `midia/`, `audios/` | Arquivos recebidos e áudios gerados. Limpe de tempos em tempos |

## Quando o dono corrigir o agente

Se ele disser "nunca faça isso" ou "faça sempre assim", grave uma linha com a data em `casa/como-trabalho.md`, na pasta de trabalho. Sem isso, a próxima cópia comete o mesmo erro. Cada cópia nasce do zero e só sabe o que está escrito.

## Atualizar

Rode de novo a linha de instalação do README e depois `python "SCRIPTS/ligar.py" reiniciar`. A pasta do serviço não é tocada. Prompts novos só entram com `configurar.py --refazer-prompts`, que apaga as edições feitas neles.
