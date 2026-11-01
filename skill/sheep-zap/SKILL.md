---
name: sheep-zap
description: Use quando a pessoa quiser ligar o agente dela no WhatsApp para atender sozinho, no jeito da Sheep: instalar o workflow da Sheep no zap, falar com o agente por um número próprio, responder grupo, ser avisada de quem escreveu, responder em áudio ou com /sheep-zap. Use também para operar ou consertar esse serviço depois de instalado: status, pausar, mudar as regras de um grupo, agente que parou de responder, mensagem que não chegou, resposta em dobro.
---

# sheep-zap

Faz o agente do dono atender o WhatsApp como a Sheep atende: três ouvidos, um cérebro por pedido e uma saída só. Roda no computador do dono, usa o Claude Code dele e fala com o WhatsApp pela Evolution.

## Primeiro passo, sempre

Nos comandos, `SCRIPTS` é a pasta `scripts` ao lado deste arquivo, com caminho completo. No Mac e no Linux, use `python3`.

```
python "SCRIPTS/confere.py"
```

| O que aparecer | O que fazer |
|---|---|
| "Ainda não configurei o WhatsApp" | Leia `references/instalacao.md` e siga uma etapa por vez |
| Tudo certo, e a pessoa quer usar ou mudar algo | Leia `references/operacao.md` |
| Algo quebrado, ou ela diz que parou | Leia `references/problemas.md` |

## Como funciona

| Ouvido | Quem escuta | Com que frequência | Quem decide |
|---|---|---|---|
| Dono no número do agente | `chat.py` | 10 s | Modelo pequeno separa recado de trabalho. Trabalho vira um agente temporário com ferramentas |
| Grupo | `grupo.py` | 45 s + 35 s de espera | Modelo sem ferramentas e sem memória. Travas fora da IA seguram o que sai |
| Alguém no número do dono (ou no do agente, se o do dono não estiver conectado) | `avisos.py` | 5 min | Ninguém. Sem IA: avisa o dono, e ele decide |

O agente é um só para o dono. Cada pedido de trabalho abre uma cópia temporária, com a mesma identidade e as mesmas regras, que faz aquilo, responde e é encerrada. No máximo 2 ao mesmo tempo. Foi um agente único esperando a própria fila que travou a primeira versão.

Quem parece lembrar do dono é a pasta, não o modelo. Cada cópia nasce do zero, lendo `CLAUDE.md`, os combinados e a memória da pasta de trabalho. Por isso os combinados são a parte mais importante da instalação: quando o dono corrigir algo, a correção precisa virar uma linha nesses arquivos.

## Regras para você, enquanto instala ou conserta

1. Uma etapa por vez, em português simples, esperando o dono confirmar.
2. Chave nunca passa pelo chat. Quem usa o painel da Sheep cadastra em Conexões. Os outros preenchem o `.env`. Se o dono colar uma chave aqui, peça para trocar depois.
3. Não mande mensagem para ninguém além do dono sem o sim dele. Teste de envio é só para o número dele.
4. "Conectado" não prova que envia, e "aceito" não prova que chegou. Só diga que funcionou depois de ver `entregue` ou `lido`, ou depois de o dono confirmar que recebeu.
5. Nunca ligue dois serviços no mesmo número. Se o painel da Sheep estiver com o WhatsApp ligado, peça para desligar lá primeiro: senão tudo sai em dobro.
6. Ao terminar, diga o que funcionou, o que não foi testado e onde as chaves ficaram.
