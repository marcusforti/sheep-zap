#!/usr/bin/env bash
# Instala a skill sheep-zap no Mac ou no Linux, sem sudo e sem Git.
# curl -fsSL https://raw.githubusercontent.com/marcusforti/sheep-zap/main/instalar.sh | bash
set -euo pipefail
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
repo="${SHEEP_ZAP_ORIGEM:-}"
if [ -z "$repo" ]; then
  curl -fsSL https://codeload.github.com/marcusforti/sheep-zap/tar.gz/refs/heads/main | tar -xz -C "$tmp"
  repo="$tmp/sheep-zap-main"
fi
origem="$repo/skill/sheep-zap"
[ -f "$origem/SKILL.md" ] || { echo "Nao achei a skill no pacote baixado." >&2; exit 1; }
casa="${SHEEP_HOME:-$HOME/Sheep}"
alvos=("$HOME/.claude/skills" "$HOME/.agents/skills")
if [ -d "$casa" ]; then alvos+=("$casa/.claude/skills" "$casa/.agents/skills"); fi
for alvo in "${alvos[@]}"; do
  mkdir -p "$alvo"
  rm -rf "$alvo/sheep-zap.novo" "$alvo/sheep-zap.velho"
  # Monta a pasta nova ao lado e troca no fim: se algo falhar no meio, a versao antiga continua inteira.
  cp -R "$origem" "$alvo/sheep-zap.novo"
  find "$alvo/sheep-zap.novo" -type d -name '__pycache__' -prune -exec rm -rf {} +
  if [ -e "$alvo/sheep-zap" ]; then mv "$alvo/sheep-zap" "$alvo/sheep-zap.velho"; fi
  mv "$alvo/sheep-zap.novo" "$alvo/sheep-zap"
  rm -rf "$alvo/sheep-zap.velho"
done
echo
echo "sheep-zap instalada."
echo "Abra o Claude Code e escreva: /sheep-zap"
echo "Se o servico ja estava ligado, peca para o agente reiniciar."
