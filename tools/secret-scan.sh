#!/usr/bin/env bash
# secret-scan.sh — the required check, in the same place and with the same name as
# on every sibling site. This repository is public.
#
# THE ONE THAT MATTERS HERE. This is the estate's first site with a checkout on it,
# so it is the first one where a leaked credential is a payment credential. The
# payment provider's secret key, a webhook signing secret and a marketplace
# credential are all shapes that must never enter this repository — not in a brief,
# not in a comment, not in a test fixture, not in docs/.
#
#   sk_live_… / sk_test_…   the payment provider's SECRET key. Never publishable.
#   pk_live_… / pk_test_…   its publishable key. Not matched below, on purpose:
#                           publishing it is what it is for.
#   whsec_…                 the webhook signing secret. Never publishable.
#   sgit_private_read_…     publishable. It is how a vault is shared, the same way
#                           sgit.ai/llms.txt shares one. Not matched, on purpose.
#   sgit_private_vault_…    the write key. Never publishable.
#   <passphrase>:<uuid>     the other shape an sgit vault key takes.
#
# A payment LINK is not a credential — it is a URL meant to be printed on a card
# and read by a stranger's phone camera. Those belong here. The key that could
# create one, refund against one, or read a customer off one does not.
#
# Runs over the working tree. Exits non-zero on a match, and prints the file and line.
set -uo pipefail
cd "$(dirname "$0")/.."

PATTERNS=(
  'sk_live_[A-Za-z0-9]{16,}'            # payment provider secret key, live
  'sk_test_[A-Za-z0-9]{16,}'            # payment provider secret key, test
  'rk_live_[A-Za-z0-9]{16,}'            # payment provider restricted key
  'whsec_[A-Za-z0-9]{16,}'              # webhook signing secret
  'sgit_private_vault_[A-Za-z0-9]+'     # sgit vault WRITE key
  'sgit_private_write_[A-Za-z0-9]+'     # ditto, alternate spelling
  '[A-Za-z0-9_-]{20,}:[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'  # passphrase:uuid
  'sk-or-v1-[A-Za-z0-9]{16,}'           # OpenRouter
  'sk-[A-Za-z0-9]{32,}'                 # OpenAI-shaped
  'hf_[A-Za-z0-9]{20,}'                 # Hugging Face
  'AKIA[0-9A-Z]{16}'                    # AWS — the marketplace rail runs on this one
  'ASIA[0-9A-Z]{16}'                    # AWS, temporary
  'ghp_[A-Za-z0-9]{36}'                 # GitHub PAT
  'github_pat_[A-Za-z0-9_]{22,}'        # GitHub fine-grained PAT
  'AIza[0-9A-Za-z_-]{35}'               # Google
  'xox[baprs]-[A-Za-z0-9-]{10,}'        # Slack
  '-----BEGIN [A-Z ]*PRIVATE KEY-----'
  'X-API-Key:[[:space:]]*[A-Za-z0-9_-]{16,}'
  # A credential named by its FIELD rather than by a prefix this list knows.
  # sgit.ai's site-pages brief: "a credential scan built for sgit shapes will not
  # catch other secrets. We nearly published an OpenRouter key sitting in a vault
  # file, in a field called openrouter_key, that matched none of the sgit patterns.
  # Scan for what the vault holds, not only for what sgit issues."
  #
  # JSON and YAML shapes only, and a length floor, so empty placeholders and short
  # enum values stay out.
  '"[A-Za-z0-9_]*(_key|apikey|secret|password|passphrase|token)"[[:space:]]*:[[:space:]]*"[A-Za-z0-9_.+/=-]{20,}"'
)

status=0
for p in "${PATTERNS[@]}"; do
  # --exclude-dir keeps the scanner out of git internals; everything else,
  # including the built site under docs/, is in scope on purpose.
  if hits=$(grep -rInE --binary-files=without-match \
        --exclude-dir=.git --exclude="$(basename "$0")" \
        "$p" . 2>/dev/null); then
    echo "SECRET SCAN FAILED — pattern /$p/ matched:"
    echo "$hits" | head -20
    status=1
  fi
done

if [ "$status" = 0 ]; then
  echo "secret-scan: clean (${#PATTERNS[@]} patterns, whole tree including docs/)."
fi
exit $status
