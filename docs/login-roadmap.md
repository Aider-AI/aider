# Roadmap: substituir o login do aider

Status: rascunho para aprovação. Escopo: fork sem usuários. Não há migração de credenciais.

## Objetivo e limites

Substituir o login OAuth atual do aider (`aider/onboarding.py`) por um fluxo que funcione em máquina local e em SSH, com armazenamento seguro e precedência clara entre credenciais.

Fora do escopo:
- Migração de `~/.aider/oauth-keys.env`. Não há usuários a migrar. O arquivo, se existir, fica sem uso.
- Alterações em `.env`, variáveis de ambiente e `--api-key`. Esses caminhos não mudam.
- Ports diretos do código TypeScript do FineCode. O desenho é portado para Python.

## Fatos verificados na documentação oficial

Fonte: https://openrouter.ai/docs/use-cases/oauth-pkce, lida em 2026-11-17 (página em Markdown, via `curl`).

- **Autorização:** `https://openrouter.ai/auth` com `callback_url`, `code_challenge` e `code_challenge_method=S256`. Os dois últimos são obrigatórios.
- **`state`:** suportado. É devolvido sem alteração no callback. Não é devolvido em negação de acesso nem no modo headless.
- **Localhost:** "supported on **any port**". A documentação não restringe o caminho do callback. Testar o caminho aleatório na prática.
- **Headless:** omitir `callback_url`. A página mostra o código na tela. O código é de uso único e expira em 10 minutos.
- **Troca:** `POST https://openrouter.ai/api/v1/auth/keys` com JSON `{code, code_verifier, code_challenge_method: "S256"}`. Resposta contém `key`.
- **Erros documentados:** 400 (`code_challenge_method` inválido), 403 (código ou verifier inválidos), 403 (código expirado), 405 (método ou protocolo errado). O formato do corpo de erro não é documentado.
- **Armazenamento:** a documentação recomenda cofre criptografado ou chaveiro do SO. Não define regras para arquivo local.
- **Opcionais úteis:** `key_label` (nome da chave criada, para rastreio) e `expiration`.

## Decisões confirmadas

- **D0 Portabilidade:** reimplementar em Python com a biblioteca padrão, sem dependência nova. O desenho do FineCode e do msal serve de especificação. Nenhum código é copiado.
- **D4 `state` no callback:** validar `state` no caminho de callback local, porque o OpenRouter o devolve. No caminho de colagem manual, `state` não existe, então a proteção é o PKCE.
- **D5 Caminho aleatório:** manter, como segunda camada. Não substitui `state`.

## Premissas verificadas no código

- `aider/onboarding.py` tem o fluxo OAuth: porta fixa entre 8484 e 8584, caminho fixo `/callback/aider`, sem `state`, sem colagem manual.
- `aider/main.py:381` carrega `.env` com `override=True`. Um `.env` do projeto sobrescreve variável do shell e a chave do login.
- `aider/onboarding.py:366` grava em `~/.aider/oauth-keys.env` em modo append, sem `chmod`.
- `aider/onboarding.py` tem `print()` direto (linha 313).
- `tests/basic/test_onboarding.py` (25 casos) e `tests/basic/test_main.py:1414` cobrem o comportamento atual.

## Fase 0: Linha de base

- Obter ambiente com acesso ao PyPI. Neste container `pypi.org` não resolve.
- Rodar `pytest` completo e registrar: número de testes, falhas, tempo. Comando e código de saída incluídos.
- **Saída:** baseline registrado.

## Fase 1: Decisões

- **D1 Precedência:** credencial salva vence `.env` e variável do shell. Muda o comportamento de `main.py:381`. Precisa de aprovação.
- **D2 Armazenamento:** arquivo único, modo `0600`, escrita atômica (arquivo temporário e `rename`), uma linha por provedor.
- **D3 Sem navegador:** colar código ou URL é obrigatório.
- **Saída:** D1 a D3 aprovadas.

## Fase 2: Armazenamento

- Módulo com leitura, escrita atômica e `0600`. Sem append.
- Testes: permissão do arquivo; escrita interrompida não corrompe o conteúdo; duas escritas seguidas deixam uma linha por provedor.
- **Saída:** L0 a L2 verdes.

## Fase 3: Precedência

- Aplicar D1 em `load_dotenv_files`.
- Substituir `test_main.py:1414`.
- Teste novo: `.env` com chave antiga não derruba a credencial salva. Este teste deve falhar no código atual.
- **Saída:** teste de regressão que falha antes e passa depois.

## Fase 4: Callback local

- Porta livre do sistema, caminho aleatório por login, `127.0.0.1`.
- Enviar `state` aleatório no `/auth` e rejeitar callback cujo `state` não bata (D4).
- Um código por callback; segundo acesso recebe 409.
- Prazo de 5 minutos; Ctrl-C libera o servidor.
- Testes com cliente HTTP local e endpoint de troca simulado. Nenhum teste acessa a rede.

## Fase 5: Colagem manual em corrida com o callback

- Quem chegar primeiro vence: callback ou código colado.
- Aceita código puro ou URL de redirecionamento.
- Testes: colagem vazia, código inválido, cancelamento, callback durante a colagem.

## Fase 6: Interface

- Mover URL e mensagens de `print()` para `io`.
- Mostrar a fonte da chave em uso e o modelo escolhido, sem imprimir a chave.

## Fase 7: Exclusão

Só depois das fases 2 a 6 verdes:
- Remover de `onboarding.py`: `start_openrouter_oauth_flow`, `exchange_code_for_key`, `find_available_port`, `generate_pkce_codes`.
- Remover de `main.py` o carregamento de `oauth-keys.env` e as chamadas de `offer_openrouter_oauth`.
- Manter `try_to_select_default_model`. Revisar o fallback de tier, que cai em "free" em caso de erro.
- Remover os testes de OAuth em `tests/basic/test_onboarding.py`.
- **Saída:** `grep` por `oauth-keys`, `offer_openrouter_oauth` e `start_openrouter_oauth_flow` retorna zero.

## Fase 8: Documentação

- Página de login em `aider/website/docs/llms/openrouter.md` e `docs/config/api-keys.md`.
- Atualizar "Known gaps" em `AGENTS.md` conforme cada item for resolvido.

## Fase 9: Validação operacional (L3)

1. `HOME` temporário, sem chave: `aider` abre o login e conclui pelo callback. Registrar comando, saída e código de saída.
2. Mesmo teste colando a URL de redirecionamento (simula SSH).
3. `.env` com chave antiga presente: a credencial salva é a que vale.
4. Fluxo interativo com `pexpect`, que já é dependência do aider.
5. Build Docker.

## Fase 10: Reversão

- `git revert` do commit da fase 7. As fases 2 a 6 continuam válidas.

## Riscos

| Risco | Detecção | Mitigação |
|---|---|---|
| Mudança de precedência surpreende quem usa `.env` | Teste da fase 3 | Documentar na fase 8 |
| Colagem manual aceita entrada inválida | Testes da fase 5 | Validar formato antes da troca |
| Porta ocupada | Teste de porta em uso | Porta livre do sistema |
| Build quebrado após exclusão | Fase 9, item 5 | Exclusão só depois da fase 6 |

## Estimativa

- Fases 2 a 6: 1 a 2 dias com testes.
- Fase 7 e 8: meio dia.
- Fase 9: depende de ambiente com PyPI e Docker.
