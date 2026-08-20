# 🩺 Dr. Código

Lê o seu código, **acha os erros e conserta pra você** usando inteligência
artificial. Também tira dúvidas de programação e tem um modo "código secreto".

---

## ⚡ Atalho pra quem já manja (terminal)

```bash
git clone https://github.com/Vitor-AM-IO/Dr.-Codigo.git
cd Dr.-Codigo
pip install .
export ANTHROPIC_API_KEY="sk-ant-suachave"   # Windows: set ANTHROPIC_API_KEY=...

code-doctor web                 # abre a interface no navegador
code-doctor arquivo.py --diff   # revisa e mostra o diff
code-doctor arquivo.py --apply  # aplica a correção (faz backup automático)
code-doctor hide arquivo.py     # camufla o código
```

Chave em https://platform.claude.com/settings/keys · Outros provedores (OpenAI,
Groq, Ollama local…) na seção [Trocar de IA](#-trocar-de-ia-openai-groq-ollama).

Não é técnico? Segue o guia abaixo, é tranquilo. 👇

---

# 🐣 Guia do zero (nunca programei)

São 4 partes. Faça uma vez; depois é só abrir e usar.

## Parte 1 — Instalar o Python (o motor do programa)

1. Abra: **https://www.python.org/downloads/**
2. Clique no botão amarelo escrito **"Download Python 3.x.x"** (no meio da página).
3. Abra o arquivo que baixou (fica na pasta **Downloads**, nome tipo
   `python-3.x.x-amd64.exe`).
4. Vai abrir uma janela de instalação. **Antes de clicar em qualquer coisa**, olhe
   na parte de **baixo** da janela e marque a caixinha:
   ☑️ **"Add python.exe to PATH"**  ← isto é o que mais gente esquece!
5. Agora clique em **"Install Now"** (o primeiro, o grande).
6. Espere a barrinha encher e clique em **"Close"**.

## Parte 2 — Baixar o Dr. Código

1. Abra a página do projeto: **https://github.com/Vitor-AM-IO/Dr.-Codigo**
2. Ache o botão **verde** escrito **`< > Code`** (fica no canto direito, um pouco
   acima da lista de arquivos). Clique nele.
3. No menuzinho que abre, clique na última opção: **"Download ZIP"**.
4. Vá na pasta **Downloads**. Clique com o **botão direito** no arquivo
   `Dr.-Codigo-main.zip` → **"Extrair tudo…"** → **"Extrair"**.
5. Abriu uma pasta chamada **`Dr.-Codigo-main`**. **Deixe essa janela aberta**,
   vamos voltar nela na Parte 4.

## Parte 3 — Pegar a chave da inteligência artificial

Essa "chave" é uma senha longa que deixa o programa conversar com o Claude.

1. Abra: **https://platform.claude.com/settings/keys**
2. **Entre na sua conta** (ou clique em **"Sign up"** pra criar — pode usar o
   Google). É a página já direto na parte de chaves.
3. 💳 Se for sua primeira vez, ele pode pedir pra **configurar pagamento antes**.
   Clique em **Settings** (à esquerda) → **Billing** → adicione um cartão e
   coloque uns poucos créditos (ex.: US$5). *A API cobra por uso e não tem plano
   grátis — mas cada revisão custa centavos.*
4. Volte pra página de chaves. No canto direito, clique no botão
   **"Create Key"**.
5. Dê um nome qualquer (ex.: `dr-codigo`) e confirme em **"Create Key"**.
6. Vai aparecer a chave, começando com **`sk-ant-`**. **Clique em "Copy" e copie
   agora** — ela só aparece **uma vez**! (Se perder, é só criar outra.)

## Parte 4 — Abrir o programa 🎉

Você **não precisa** editar nenhum arquivo. Na primeira vez, o próprio programa
pergunta a sua chave ali no terminal e guarda pra você.

1. Volte pra janela da pasta **`Dr.-Codigo-main`** (da Parte 2).
2. Clique na **barra de endereço** (a faixa no topo que mostra o caminho da
   pasta). O texto vai ficar selecionado.
3. Digite **`cmd`** por cima e aperte **Enter**. Vai abrir uma **janelinha preta**
   (é o terminal, tudo normal).
4. Nessa janela preta, digite exatamente e aperte Enter:
   ```
   python start.py
   ```
5. Na **primeira vez**, ele mostra: *"Cole sua chave e aperte Enter:"*.
   - Clique com o **botão direito** dentro da janela preta — isso **cola** a chave
     que você copiou na Parte 3.
   - Aperte **Enter**.
   - Ele salva a chave no seu computador e mostra *"✓ Chave salva"*.
6. Pronto! Em alguns segundos **a página abre sozinha no navegador**. 🩺

> ✅ **Deu certo se:** apareceu *"✓ Chave salva"* e a página abriu no navegador.
>
> 🔒 A chave fica **só no seu PC** (num arquivo chamado `.env`) e **nunca** é
> enviada pra internet nem pro GitHub.
>
> 🔁 Nas **próximas vezes**, ele **não pergunta mais** — é só repetir os passos 1
> a 4 e a página abre direto. Pra **fechar** o programa, feche a janelinha preta.

---

# 🖥️ Como usar a página

Três abas no topo:

| Aba | O que faz |
|-----|-----------|
| 🔍 **Revisar código** | Cole o código na caixa → botão **Revisar**. Ele lista os erros e mostra a versão corrigida (com botão **copiar**). |
| 💬 **Tirar dúvida** | Escreva a pergunta → botão **Perguntar**. |
| 🕵️ **Camuflar** | Cole o código, escolha um idioma secreto → **Camuflar** / **Revelar**. É só diversão, não gasta nada. |

### 📦 Projeto (.zip)
Envie o seu projeto inteiro compactado em `.zip` e escolha o que quer:
- **Resumo geral** — uma visão do todo numa única análise (mais barato);
- **Arquivo por arquivo** — revisão detalhada de cada arquivo (mais caro);
- **Só os problemas graves** — foco em segurança e bugs, saída curta (econômico).

Analisa até 20 arquivos de código por projeto (zip até 8 MB). Cada arquivo custa
tokens — a barrinha de gasto mostra o total. Pra manter tudo local e grátis, use
o modelo **Ollama**.

A **barrinha embaixo** mostra o quanto você já gastou na sessão, em **dólar e em
reais** (R$). É uma estimativa; a cotação pode ser ajustada na variável
`CODE_DOCTOR_USD_BRL`.

## Testar rápido

Tem um arquivo cheio de erros de propósito em **`exemplos/exemplo_bugs.py`**. Cole
o conteúdo dele na aba **Revisar código** (ou rode `code-doctor exemplos/exemplo_bugs.py --diff`)
pra ver o Dr. Código encontrando os problemas.

---

# 😵 Deu erro? (o que fazer em cada caso)

| Apareceu isto… | Faça isto |
|----------------|-----------|
| `'python' não é reconhecido…` na janela preta | O Python não entrou no PATH. Refaça a **Parte 1**, marcando a caixinha **"Add python.exe to PATH"**, e reinicie o PC. |
| Aviso amarelo **"chave não configurada"** na página | Feche a janela preta, apague o arquivo `.env` da pasta (se existir) e refaça a **Parte 4** colando a chave com atenção. |
| `authentication_error` / `401` | A chave está errada ou incompleta. Crie outra em platform.claude.com/settings/keys e cole de novo. |
| Erro falando de **billing/credits** | Falta crédito na conta. Vá em **Settings → Billing** no site da Anthropic e adicione. |
| A janela preta fecha sozinha na hora | Abra o `cmd` **pela barra de endereço** (Parte 4, passo 2-3), não dê dois cliques no `start.py`. |
| **No Linux:** `externally-managed-environment` | O Debian/Ubuntu bloqueia o pip do sistema (proteção). O programa já tenta contornar; se ainda falhar, rode: `pip install --user --break-system-packages anthropic` e depois `python3 start.py` de novo. |

---

# 💰 Escolher o modelo (e economizar)

Na página, no topo, tem um seletor **"Modelo:"** com 3 opções. Você troca na hora
e o gasto muda junto:

| Opção na tela | Custo | Quando usar |
|---------------|-------|-------------|
| **Melhor qualidade** | ~$2/$10 por 1 milhão de tokens | Revisões difíceis, quando quer o melhor resultado |
| **Mais econômico** | ~$1/$5 (metade do preço) | No dia a dia — corta o gasto pela metade |
| **Grátis (Ollama)** | **R$ 0** | Roda no seu próprio PC, sem pagar nada |

> A barrinha de gasto embaixo já mostra o custo estimado do modelo escolhido. Na
> opção grátis, ela fica em zero.

## Usar de graça com o Ollama (opcional)

Quer usar **sem pagar nada**? O Ollama roda um modelo de IA no seu próprio
computador. **Jeito fácil:** no terminal (a janelinha preta), rode:

```
code-doctor instalar-ollama
```

Ele detecta o seu sistema e instala sozinho (é só confirmar com "s"). Depois,
baixa o modelo e é só escolher **"Grátis (Ollama)"** no seletor da página.

> ⚠️ Um **botão na página** não consegue instalar programas (o navegador bloqueia
> isso por segurança). Por isso a instalação é por esse comando no terminal.

**Ou instale manualmente:**

1. Baixe o Ollama: **https://ollama.com** (Windows, Mac ou Linux).
2. No terminal, rode uma vez pra baixar um modelo:
   ```
   ollama pull llama3.1
   ```
3. Deixe o Ollama rodando e escolha **"Grátis (Ollama)"** na página.

> O Ollama roda **100% no seu PC**: não custa nada e o seu código **não é enviado
> pra internet**. Só é um pouco mais lento e exige um computador razoável.

---



Não quer usar a Anthropic? Dá pra usar **OpenAI, OpenRouter, Groq, DeepSeek,
Mistral** ou rodar **de graça no seu PC** com **Ollama**. Abra o arquivo
`.env.example` (na pasta do programa) — ele já tem todos os exemplos prontos, é só
descomentar um. Exemplos:

```bash
# OpenAI
CODE_DOCTOR_PROVIDER=openai
OPENAI_API_KEY=sk-...
CODE_DOCTOR_MODEL=gpt-4o-mini

# Ollama — roda no seu computador, sem chave e sem custo
CODE_DOCTOR_PROVIDER=ollama
CODE_DOCTOR_MODEL=llama3.1
```

---

# 🤖 Revisão automática no GitHub (Pull Requests)

Já vem pronto pra comentar a revisão sozinho em cada Pull Request. Para ligar:

1. No seu repositório: **Settings → Secrets and variables → Actions**.
2. Aba **Secrets** → botão **"New repository secret"**.
3. **Name:** `ANTHROPIC_API_KEY` — **Secret:** sua chave → **Add secret**.
4. Pronto. Ao abrir um Pull Request, o Dr. Código comenta os erros nele.

> Em PRs de **forks** (gente de fora), o GitHub não passa sua chave por segurança —
> a revisão é pulada de propósito nesses casos.

---

# 🔒 Segurança e privacidade

- Sua chave fica só no seu PC (arquivo `.env`, que **nunca** vai pro GitHub).
- O código enviado pra revisão vai pra IA que você escolher. Pra sigilo total, use
  **Ollama** (roda tudo local, não manda nada pra internet).
- As correções são de IA e podem errar — confira antes de usar em algo sério.

Detalhes em [SECURITY.md](SECURITY.md).

---

Criado por **Vitor** (@Vitor-AM-IO).
Licença MIT — veja [LICENSE](LICENSE) e [AUTHORS.md](AUTHORS.md).
