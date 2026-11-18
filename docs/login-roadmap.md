# Roadmap: migrar a autenticação do aider para o padrão do Pi

Status: em execução. Escopo: fork sem usuários, sem migração de credenciais antigas.

## Objetivo

O aider passa a usar a arquitetura de autenticação do Pi (`packages/ai/src/auth/` no FineCode), reescrita em Python. O objetivo não é consertar o login atual do aider. O login atual é substituído por essa arquitetura.

Padrão do Pi que deve estar presente no aider:

1. **Credencial por provedor.** Cada provedor declara `apiKey` e/ou `oauth`.
2. **Armazenamento como interface.** `read`, `list`, `modify` (leitura e escrita serializadas por provedor) e `delete`.
3. **Resolução no uso.** `resolve()` decide a credencial. Uma credencial salva é dona do provedor. Variável de ambiente só é consultada se nada estiver salvo.
4. **OAuth como objeto.** `login(interaction)`, `refresh(credential)` e `to_auth(credential)`.
5. **Interação de login por eventos.** Um objeto recebe `notify` (URL, progresso, informação) e `prompt` (código manual).
6. **Comando de login com seleção de provedor.**

Fora do escopo:
- Copiar código TypeScript. Só o desenho é portado.
- Provedores além do OpenRouter, até passarem pelos gates abaixo.

## Decisões

- **D0 Portabilidade:** Python, biblioteca padrão, sem dependência nova. Nada copiado do FineCode.
- **D1 Precedência (regra do Pi):** credencial salva vence `.env` e shell. Variável de ambiente só vale quando nada estiver salvo. Explícitos (`--api-key`) continuam vencendo, como hoje.
- **D2 Armazenamento:** `CredentialStore` com `modify` serializado. Arquivo único, modo `0600`, escrita atômica. Formato do Pi: `{"type": "oauth", "access": ...}` ou `{"type": "api_key", "key": ...}`.
- **D3 Interação:** objeto com `notify(event)` e `prompt_manual_code(message)`. A camada OAuth não conhece o terminal.
- **D4 `state`:** validado no callback local. Na colagem manual, não há `state`, e a proteção é o PKCE.
- **D5 Caminho aleatório:** segunda camada, além do `state`.
- **D6 Escopo por fases:** OpenRouter primeiro. Outros provedores entram um por vez, pelos gates.
- **D7 Arquitetura do Pi:** a estrutura de camadas do Pi é o alvo, não só o comportamento. Substitui a decisão anterior de "arquitetura própria".
- **D8 Nomes e caminhos (a confirmar):** mantemos `~/.aider/auth.json` e `--login [PROVIDER]`, porque o produto é o aider. O Pi usa `~/.pi/agent/auth.json` e `login`. Se você preferir os nomes do Pi, muda-se só a constante.
- **D9 Entrega ao litellm (adaptação):** o litellm do aider lê chaves de variáveis de ambiente. Por isso `resolve()` escreve a chave resolvida em `os.environ` no início da execução, em vez de passar a chave a cada chamada. Essa é a única diferença estrutural em relação ao Pi, e fica registrada.
- **D10 Colagem manual só no modo headless:** o Pi corre callback e colagem em paralelo. No aider isso não é seguro, porque a leitura do terminal não pode ser cancelada e roubaria a próxima linha digitada. Localmente, só o callback. Em SSH ou sem display, só a colagem. Desvio consciente.

## Gates para cada provedor além do OpenRouter

1. **Documentação pública** do fluxo OAuth, sem endpoints privados.
2. **Client ID próprio** do aider, ou autorização escrita. Pelo código do FineCode, Anthropic, GitHub Copilot, Kimi, Meta e OpenAI usam IDs fixos de outros aplicativos (`anthropic.ts:14`, `github-copilot.ts:11`, `kimi-coding.ts:14`, `meta.ts:20`, `openai-chatgpt.ts:16`). Termos a verificar.
3. **Conta disponível para validação L3.**

## Fatos verificados na documentação oficial

Fonte: https://openrouter.ai/docs/use-cases/oauth-pkce, lida em 2026-11-17.

- `https://openrouter.ai/auth` com `callback_url`, `code_challenge`, `code_challenge_method=S256` e `state` (opcional, devolvido no callback).
- Localhost em qualquer porta. Caminho do callback não restrito pela documentação.
- Headless: omitir `callback_url`. Código de uso único, expira em 10 minutos.
- Troca: `POST https://openrouter.ai/api/v1/auth/keys` com `{code, code_verifier, code_challenge_method: "S256"}`. Resposta com `key`.
- Erros documentados: 400, 403 (código/verifier inválido), 403 (expirado), 405. Formato do corpo de erro não documentado.

## Fases

### P0 Linha de base
- `pytest` completo no ambiente do projeto, antes das mudanças (`de3d1f5`).
- Estado: 11 falhas, 5 erros, 472 aprovados, 5 pulados. Causas classificadas por mensagem: ambiente (extras e rede) para 12 ocorrências, Windows para 1, pendente para 3 (`sonnet` e `None != '3'`).
- Saída: classificação fechada com nome de teste.

### P1 Tipos e registro de provedores
- `aider/auth.py`: `ProviderAuth`, `OAuthAuth`, `ApiKeyAuth`, interação, registro.
- Testes: registro do OpenRouter com `oauth` e `apiKey`.

### P2 Armazenamento no formato do Pi (novo módulo, substitui `credential_store.py`)
- Novo `CredentialStore` com `read`, `list`, `modify`, `delete`. Serialização por provedor.
- O `credential_store.py` atual é removido, junto com `get`, `set` e `providers`. Não é adaptado.
- Formato OAuth e API key do Pi (D2).
- Testes: round trip, `modify` atômico, falha no meio não corrompe, formato.

### P3 `resolve()`
- Regra D1: salvo vence; senão variável de ambiente; senão nada.
- Testes: salvo com `.env` diferente; sem salvo com variável; nada.

### P4 OpenRouter como `OAuthAuth` (novo módulo, substitui `openrouter_login.py`)
- `login(interaction)`: local → callback; headless → colagem (D10).
- `refresh`: credencial permanente, devolve a mesma.
- `to_auth`: `{"apiKey": access}`.
- O PKCE, o callback e a troca são reescritos dentro do módulo novo. O `openrouter_login.py` atual é removido, não é reaproveitado como estão as funções.
- Testes novos, escritos para a interface nova. Os testes atuais só servem como referência de casos.

### P5 Comando de login (substitui `run_login_command` e a flag atual)
- `--login` sem argumento: lista provedores com OAuth e pede a escolha.
- `--login openrouter`: vai direto.
- Testes: seleção, provedor inválido, falha de login.

### P6 Integração no início da execução
- `resolve()` antes de escolher o modelo; escreve em `os.environ` (D9).
- `--api-key` continua vencendo.
- Testes: `test_main` sem chaves, com credencial salva, com `--api-key`.

### P7 Limpeza
- `grep` por `get(`, `set(`, `providers()` antigos e por `apply_stored_credentials` sem uso.
- Remover resíduos do fluxo antigo.

### P8 Documentação
- `aider/website/docs/llms/openrouter.md`, `docs/config/api-keys.md`.
- `AGENTS.md`: atualizar "Known gaps".

### P9 Validação operacional (L3)
1. Local, Windows: `aider --login openrouter` conclui pelo callback. Confirmar se o OpenRouter aceita `127.0.0.1`.
2. SSH ou sem display: colagem concluída.
3. Credencial salva vence `.env`.
4. Suíte completa e `flake8` sem aviso novo em relação a `de3d1f5`.

## Riscos

| Risco | Detecção | Mitigação |
|---|---|---|
| Migração vira reforma do aider | Revisão do roteiro a cada fase | Cada fase cita o padrão do Pi que implementa |
| `resolve()` em `os.environ` vaza para subprocessos | Teste de P6 | Documentar em D9 |
| Colagem local rouba entrada do chat | Desligada localmente (D10) | — |
| `127.0.0.1` rejeitado pelo OpenRouter | P9 item 1 | Trocar para `localhost` |

## Estado atual (registro)

- Commit `3cfa81d`: login atual do aider (flag `--login`, callback, colagem, `credential_store.py` antigo). Esse código é descartável: será substituído pelas fases P1 a P6, não ajustado.
- Não há mais edição do login atual como objetivo. Qualquer alteração nesses arquivos é só para remover ou para não quebrar a suíte até a substituição.
