# Roadmap: editar o login do aider para o padrão do Pi

Status: em execução. Escopo: fork sem usuários, sem migração de credenciais antigas.

## Objetivo

O login atual do aider é editado para incorporar o modo de login do Pi (`packages/ai/src/auth/` e `packages/coding-agent` no FineCode), em Python. Parte do código atual é aproveitada. A maior parte é reescrita para o modelo do Pi. Os dois modos de login do Pi entram: pelo navegador (OAuth) e por API key.

Padrão do Pi que deve estar presente no aider:

1. **Credencial por provedor.** Cada provedor declara `apiKey` e/ou `oauth`.
2. **Armazenamento como interface.** `read`, `list`, `modify` (leitura e escrita serializadas por provedor) e `delete`.
3. **Resolução no uso.** `resolve()` decide a credencial. Uma credencial salva é dona do provedor. Variável de ambiente só é consultada se nada estiver salvo.
4. **OAuth como objeto.** `login(interaction)`, `refresh(credential)` e `to_auth(credential)`.
5. **Interação de login por eventos.** Um objeto recebe `notify` (URL, progresso, informação) e `prompt` (código manual ou API key).
6. **Dois métodos de login por provedor:** pelo navegador (quando o provedor tem OAuth) e por API key digitada.
7. **Comando de login com seleção de provedor e de método.**

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
- **D11 Edição, não substituição:** o que hoje está em `credential_store.py`, `openrouter_login.py` e `main.py` é reaproveitado quando serve (escrita atômica, PKCE, callback, troca). O restante é reescrito para o modelo do Pi.
- **D12 Login por API key:** qualquer provedor que o aider já reconhece pela variável de ambiente (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GEMINI_API_KEY`, `OPENROUTER_API_KEY` e outros do `models.py`) pode ser configurado por API key. A chave digitada é salva como `api_key` no mesmo armazenamento e tem a mesma precedência (D1).
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

### P2 Armazenamento no formato do Pi (edita `credential_store.py`)
- Reaproveitar a escrita atômica e a permissão `0600`.
- Trocar a API para `read`, `list`, `modify`, `delete`, com serialização por provedor. `get`, `set` e `providers` viram wrappers ou são removidos, conforme os usos.
- Formato do Pi: `{"type": "oauth", "access": ...}` e `{"type": "api_key", "key": ...}`.
- Formato OAuth e API key do Pi (D2).
- Testes: round trip, `modify` atômico, falha no meio não corrompe, formato.

### P3 `resolve()`
- Regra D1: salvo vence; senão variável de ambiente; senão nada.
- Testes: salvo com `.env` diferente; sem salvo com variável; nada.

### P4 OpenRouter como `OAuthAuth` (edita `openrouter_login.py`)
- Reaproveitar PKCE, callback com `state`, colagem e troca de código.
- Expor como objeto: `login(interaction)`, `refresh` (credencial permanente) e `to_auth` (`{"apiKey": access}`).
- Local → callback. Headless → colagem (D10).
- Remover `run_login` e as funções que duplicam o objeto.
- Os testes atuais são adaptados à nova interface, e os casos continuam os mesmos.

### P5 Comando de login (edita `run_login_command` e a flag `--login`)
- `--login` sem argumento: lista provedores e pede a escolha.
- Depois de escolher o provedor, pede o método quando houver mais de um: navegador (OAuth) ou API key.
- `--login PROVIDER` vai direto para o método padrão do provedor (navegador quando houver OAuth, senão API key), com `--method browser|key` para forçar.
- Testes: seleção, provedor inválido, método inválido, falha de login, API key salva.

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

- Commit `3cfa81d`: login atual do aider (flag `--login`, callback, colagem, `credential_store.py`, `openrouter_login.py`). É a base a ser editada. Parte fica, parte é reescrita, conforme D11.
- Não há substituição integral. Cada fase diz o que é reaproveitado e o que é reescrito.
