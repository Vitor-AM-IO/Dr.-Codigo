# 🩺 Code Doctor

Revisor de código com IA usando a **API da Anthropic (Claude)**. Ele lê seus
arquivos, **aponta falhas** (bugs, segurança, casos de borda, más práticas),
**sugere a correção** e, se você quiser, **aplica direto no arquivo**.

Funciona de dois jeitos:

- **CLI no terminal** — rode num arquivo ou numa pasta inteira.
- **GitHub Action** — revisa automaticamente os arquivos alterados em cada Pull Request.

Cada pessoa usa a **própria chave** da Anthropic, então cada um gasta os próprios créditos.

---

## Instalação

Clone o repositório e instale:

```bash
git clone https://github.com/Vitor-AM-IO/Dr.-Codigo.git
cd Dr.-Codigo
pip install .
```

> Requer Python 3.10+.

## Configurar a chave da API

Pegue sua chave em <https://console.anthropic.com/settings/keys> e defina a
variável de ambiente:

```bash
export ANTHROPIC_API_KEY="sua-chave-aqui"
```

Ou copie o arquivo de exemplo e preencha:

```bash
cp .env.example .env
# edite o .env e coloque sua chave
```

## Como usar (CLI)

```bash
# Só analisar e listar os problemas (não altera nada):
code-doctor caminho/do/arquivo.py

# Analisar uma pasta inteira:
code-doctor ./src

# Ver o diff das correções propostas:
code-doctor arquivo.py --diff

# Aplicar as correções no arquivo (backup automático em .code-doctor/backups):
code-doctor arquivo.py --apply
```

Também funciona via módulo, sem instalar:

```bash
python -m code_doctor arquivo.py
```

### Opções

| Flag            | O que faz                                                      |
|-----------------|----------------------------------------------------------------|
| `--apply`       | Aplica as correções (backup automático em `.code-doctor/backups`) |
| `--diff`        | Mostra o diff das mudanças propostas                          |
| `--provider`    | Escolhe o provedor (anthropic, openai, groq, ollama…)        |
| `--model`       | Escolhe o modelo (padrão do anthropic: `claude-sonnet-5`)    |
| `--ext`         | Extensões extras, ex.: `--ext .toml,.cfg`                     |
| `--no-cache`    | Ignora a memória e reanalisa tudo (gasta mais tokens)        |
| `--clear-cache` | Apaga a memória de revisões e sai                            |
| `--fail-on`     | Em CI, sai com erro se houver problema deste nível ou pior   |
| `--version`     | Mostra a versão                                              |

O modo padrão é **seguro**: sem `--apply`, ele nunca escreve no seu arquivo —
só lista os problemas. Use `--diff` para revisar antes e `--apply` para aplicar.




## Usar outro provedor (não só a Anthropic)

Nem todo mundo usa a Anthropic — o Code Doctor funciona com **qualquer API no
formato OpenAI**, então dá pra escolher o que você preferir. Basta definir
`CODE_DOCTOR_PROVIDER` (no `.env` ou como variável de ambiente) e a chave/modelo
correspondentes.

| Provedor      | `CODE_DOCTOR_PROVIDER` | Chave                | Exemplo de modelo                  |
|---------------|------------------------|----------------------|------------------------------------|
| Anthropic     | `anthropic` (padrão)   | `ANTHROPIC_API_KEY`  | `claude-sonnet-5`                  |
| OpenAI        | `openai`               | `OPENAI_API_KEY`     | `gpt-4o-mini`                      |
| OpenRouter    | `openrouter`           | `OPENROUTER_API_KEY` | `meta-llama/llama-3.1-8b-instruct` |
| Groq          | `groq`                 | `GROQ_API_KEY`       | `llama-3.1-70b-versatile`          |
| Together      | `together`             | `TOGETHER_API_KEY`   | `meta-llama/Llama-3-70b-chat-hf`   |
| DeepSeek      | `deepseek`             | `DEEPSEEK_API_KEY`   | `deepseek-chat`                    |
| Mistral       | `mistral`              | `MISTRAL_API_KEY`    | `mistral-large-latest`             |
| Ollama (local)| `ollama`               | — (sem chave)        | `llama3.1`                         |
| LM Studio     | `lmstudio`             | — (sem chave)        | (o que estiver carregado)          |
| Endpoint próprio | `custom`            | `CODE_DOCTOR_API_KEY`| definido por você                  |

Exemplos:

```bash
# OpenAI
CODE_DOCTOR_PROVIDER=openai OPENAI_API_KEY=sk-... \
  code-doctor arquivo.py --model gpt-4o-mini

# 100% local e de graça com Ollama (nenhuma chave, nenhum custo)
CODE_DOCTOR_PROVIDER=ollama code-doctor arquivo.py --model llama3.1

# Endpoint compatível com OpenAI que você mesmo hospeda
CODE_DOCTOR_PROVIDER=custom \
  CODE_DOCTOR_BASE_URL=https://seu-endpoint/v1 \
  CODE_DOCTOR_API_KEY=... \
  code-doctor arquivo.py --model seu-modelo
```

Também dá pra escolher direto na linha de comando com `--provider`:

```bash
code-doctor arquivo.py --provider groq --model llama-3.1-70b-versatile
```

> O provedor vale para tudo: CLI, interface web e GitHub Action. A memória (cache)
> guarda a revisão por provedor+modelo, então trocar de modelo não reaproveita
> resultado antigo por engano.
>
> **Local com Ollama = custo zero.** Se você não quer gastar nada nem depender de
> nuvem, rode um modelo local com o Ollama e aponte o Code Doctor pra ele.

## Interface web (para quem não é de terminal)

Prefere clicar em vez de digitar comandos? O Code Doctor tem uma página local:

```bash
code-doctor web
```

Isso abre no navegador uma tela simples onde você:

- **cola o código** e clica em *Revisar* (ele aponta as falhas e mostra o código corrigido pra copiar/baixar), ou
- troca para **Tirar dúvida** e pergunta em português sobre qualquer código;
- acompanha uma **barra de consumo** com os tokens usados e o **custo estimado** da
  sessão, com um orçamento que você mesmo define.

Quem não conhece terminal pode simplesmente rodar o atalho:

```bash
python start.py
```

que instala o necessário na primeira vez e abre a página sozinho.

> **Seguro para iniciantes:** no modo web o Code Doctor trabalha só com o código
> que você **cola** — ele nunca altera os arquivos do seu computador. Não tem como
> "quebrar o projeto".
>
> A barra de custo é uma **estimativa** (tokens × preço do modelo), não o saldo
> real da sua conta — a API não expõe esse saldo. Serve como guia de gasto.


## 🕵️ Camuflar código (modo secreto — só por diversão)

Um extra divertido: transforme seu código em glifos de outro "idioma" e revele
de volta o original, sem perder nada.

```bash
# camuflar em runas (padrão), katakana, braille ou emoji
code-doctor hide app.py --style katakana --out app.secret

# revelar de volta (detecta o idioma sozinho)
code-doctor reveal app.secret --out app.py
```

Exemplo — `senha = "1234"` vira:

```
runas:    ᚼᛖᚵᛎᚺᚦᚤᛀᚯᚲᚠᛂᚬᚳᚨᛓᚭᚢᚨᛠ
katakana: ソプザハセェゥチグコァッキゴォピギィォメ
emoji:    😜😶😕😮😚😆😄😠😏😒😀😢😌😓😈😳😍😂😈🙀
```

Também está na interface web, na aba **🕵️ Camuflar** — cola, escolhe o idioma,
clica em *Camuflar* ou *Revelar*.

> É **100% local** (não usa a API, não gasta nada) e **reversível**. Mas é
> **camuflagem, não criptografia**: qualquer pessoa com esta ferramenta reverte.
> Serve para disfarçar/brincar, não para proteger segredos de verdade.

## Memória e economia (novidade)

O Code Doctor guarda uma **memória do projeto** na pasta `.code-doctor/` (estilo
`.git`), e isso é o que o deixa econômico:

- **Cache por hash:** cada arquivo revisado é guardado por um hash do seu
  conteúdo. Se você rodar de novo e o arquivo **não mudou**, ele reaproveita a
  revisão anterior e **não chama a API** — zero tokens. Só arquivos que mudaram
  gastam créditos.
- **Backup automático:** ao usar `--apply`, o original é salvo automaticamente em
  `.code-doctor/backups/` com data e hora. Você nunca perde a versão anterior.
- **Prompt caching:** o prompt de sistema é marcado como cacheável, barateando
  chamadas repetidas.
- **Relatório de uso real:** ao final, o tool mostra quantos arquivos vieram da
  memória (0 tokens) e quantos tokens de verdade foram gastos via API — números
  reais vindos da resposta da API, não estimativa.
- **Guarda-arquivos grandes:** arquivos acima de ~120 KB são pulados por padrão
  para não estourar tokens.

Flags relacionadas:

```bash
code-doctor ./src              # usa a memória automaticamente
code-doctor ./src --no-cache   # ignora a memória e reanalisa tudo
code-doctor --clear-cache      # apaga a memória de revisões
```

> A pasta `.code-doctor/` já está no `.gitignore` — cache e backups ficam locais,
> não vão para o repositório.

## Como usar (GitHub Action)

O repositório já vem com o workflow `.github/workflows/code-doctor.yml`. Para
ativá-lo no seu projeto:

1. Copie a pasta `.github/` para o seu repositório.
2. No GitHub, vá em **Settings → Secrets and variables → Actions** e crie um
   secret chamado `ANTHROPIC_API_KEY` com a sua chave.
3. Abra um Pull Request — o Code Doctor comenta a revisão dos arquivos alterados.

> A Action **nunca aplica** mudanças; ela só revisa e comenta. Para bloquear o
> merge quando houver algo grave, adicione `--fail-on high` no passo de revisão.

## Como funciona

Cada arquivo é enviado ao modelo com um prompt de revisão. O modelo responde em
JSON estruturado (resumo, lista de problemas com severidade e linha, e o código
corrigido completo). O CLI formata isso no terminal, gera o diff e, com
`--apply`, grava a versão corrigida.

## Aviso

A revisão é gerada por IA e pode errar — trate como um segundo par de olhos,
não como verdade absoluta. Sempre revise o diff antes de aplicar, especialmente
em código de produção.


## Segurança e autoria

Antes de publicar, vale ler o [SECURITY.md](SECURITY.md). Resumo do que já está
protegido de fábrica:

- Chaves de API só em `.env` (que está no `.gitignore`) — nunca no código, cache,
  backups ou logs.
- Servidor web só em `127.0.0.1`, com checagem de `Host` (anti DNS-rebinding) e de
  `Origin` (anti-CSRF), então outros sites do seu navegador não conseguem usá-lo.
- `--apply` sempre faz backup automático antes de sobrescrever.
- A ferramenta nunca executa o código analisado nem a resposta do modelo.
- Na GitHub Action, PRs de forks não recebem secrets (e a revisão é pulada) — não
  habilite o envio de secrets para forks.

Para privacidade total, use um provedor **local** (`CODE_DOCTOR_PROVIDER=ollama`):
nada sai da sua máquina.

Autoria em [AUTHORS.md](AUTHORS.md). Veja a assinatura com:

```bash
code-doctor --about
```

## Licença

MIT — veja [LICENSE](LICENSE).
