# Segurança

## Como reportar uma vulnerabilidade

Encontrou um problema de segurança? Abra uma *issue* marcada como sensível ou
entre em contato com o mantenedor (@Vitor-AM-IO). Evite publicar
detalhes de exploração antes de uma correção.

## Modelo de segurança e boas práticas

- **Suas chaves de API** ficam em variáveis de ambiente ou num arquivo `.env`
  **que já está no `.gitignore`** — nunca são gravadas no repositório, no cache
  ou nos backups, e nunca aparecem em logs. Confira antes de commitar.
- **Servidor web local:** escuta apenas em `127.0.0.1` (não fica exposto na
  rede). Além disso, valida o cabeçalho `Host` (proteção contra DNS-rebinding) e
  a `Origin` das requisições POST (proteção básica contra CSRF), para que outros
  sites abertos no seu navegador não consigam usar o servidor.
- **Aplicar correções (`--apply`)** sempre gera um **backup automático** com
  data/hora em `.code-doctor/backups/` antes de sobrescrever qualquer arquivo.
- **Nada de execução de código:** a ferramenta nunca executa (`eval`/`exec`) o
  código analisado nem a resposta do modelo. A camuflagem usa apenas base64.
- **GitHub Action:** em Pull Requests vindos de **forks**, o GitHub não expõe
  secrets — por isso a revisão é pulada nesses casos, de propósito. **Não
  habilite** o envio de secrets para PRs de forks: isso permitiria que um PR
  malicioso executasse código com a sua chave. PRs de branches do próprio
  repositório são considerados confiáveis.

## Privacidade

O código que você envia para revisão é transmitido ao **provedor de IA que você
escolher** (Anthropic, OpenAI, etc.). Se isso for sensível, use um provedor
**local** como o Ollama (`CODE_DOCTOR_PROVIDER=ollama`), que roda 100% na sua
máquina e não envia nada para a nuvem. A camuflagem de código é sempre local.

## Aviso

As revisões e correções são geradas por IA e podem conter erros. Sempre revise o
*diff* antes de aplicar, especialmente em código de produção.
