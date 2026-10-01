<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/banner-dark.png">
  <img alt="Figma Maxxing. Agent skills for real Figma files, by Thiago Xikota." src="../assets/banner-light.png">
</picture>

# Figma Maxxing

**Skills de agente para arquivos reais do Figma: inspecionar antes de editar, provar o que mudou e pegar as lacunas do handoff.**

[![Tests](https://github.com/thiagoxikota/figma-maxxing/actions/workflows/test.yml/badge.svg)](https://github.com/thiagoxikota/figma-maxxing/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-black.svg)](../LICENSE)

[English](../README.md) · [Instalar](#instalar) · [O que você precisa](#o-que-você-precisa) · [As skills](#as-skills) · [Gotchas](#alguns-dos-gotchas)

## Cole na sua IA

Você não precisa instalar nada para receber uma checklist do seu trabalho. Copie o texto abaixo, cole na IA que você usa (Claude, ChatGPT, Gemini, Cursor) e preencha os colchetes.

```text
Leia https://raw.githubusercontent.com/thiagoxikota/figma-maxxing/main/llms.txt
Se não conseguir abrir, me avise e não invente.
Sou designer. [Tenho / Não tenho] um agente de IA conectado ao Figma.
Meu contexto: [plano do Figma, se meus arquivos têm design system, se trabalho
sozinho ou em time]. Escolha no máximo cinco regras para o meu trabalho. Para
cada uma, me dê uma checagem que eu consiga fazer no Figma hoje. Depois, diga se
alguma skill vale a pena instalar no meu caso.
```

Se alguma regra te poupar uma tarde e você tiver conta no GitHub, deixe uma estrela. É assim que outros designers encontram o repositório.

## Por que existe

Sou o Thiago Xikota, AI Product Designer. Este é o conjunto de skills que eu uso quando um agente edita meus arquivos no Figma: arquivos que já têm design system, comentário do time e um dev esperando o handoff.

A tela pode parecer certa e o arquivo estar errado. A cor está num hex solto, mesmo existindo uma variável igual. O ícone foi desenhado à mão porque ninguém procurou na biblioteca. O handoff mostra como adicionar e nunca como remover. Você só descobre quando clica na camada, ou quando o dev pergunta.

Estas skills orientam o agente a inspecionar o arquivo antes de editar e a conferir o que mudou antes de dizer que terminou. A maior parte das regras nasceu de algo que quebrou num arquivo real.

As skills estão escritas em inglês, para servir também a quem não fala português. Você conversa com o agente em português normalmente.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="../assets/flow-dark.png">
  <img alt="Como as skills se encaixam: 01 mapear o arquivo com figma-orient, 02 conferir antes de editar com figma-preflight, 03 editar com figma_execute, 04 conferir depois com figma-slop-check, 05 entregar com figma-handoff-gate. O figma-canon guarda as regras que todo passo lê; o figma-comment-fix-loop roda os passos 02 a 04 uma vez por comentário." src="../assets/flow-light.png">
</picture>

## Instalar

```bash
npx skills add thiagoxikota/figma-maxxing
```

Isso instala as skills no seu agente (Claude Code, Codex, Cursor e outros compatíveis com a [CLI `skills`](https://skills.sh)). A CLI é de terceiros e envia contagem anônima de instalação; `DISABLE_TELEMETRY=1` desliga. Isso não conecta o agente ao Figma: esse é [o próximo passo](#o-que-você-precisa).

<details>
<summary>Outras formas de instalar</summary>

**Plugin do Claude Code**

```text
/plugin marketplace add thiagoxikota/figma-maxxing
/plugin install figma-maxxing@figma-maxxing-skills
```

As skills ficam disponíveis como `/figma-maxxing:figma-preflight` e assim por diante. O plugin só tem skills. Não instala hook nem servidor MCP.

**Cópia manual**

```bash
git clone https://github.com/thiagoxikota/figma-maxxing.git
cd figma-maxxing
python3 install.py --dry-run                      # mostra o que seria copiado
python3 install.py --scope user                   # Claude Code, todos os projetos: ~/.claude/skills
python3 install.py --target agents --scope user   # Codex e outros: ~/.agents/skills
```

O instalador copia pastas e mais nada. Ele se recusa a sobrescrever uma skill que já existe.

</details>

## Comece pela tarefa

Com a configuração de [O que você precisa](#o-que-você-precisa) pronta, diga ao agente, do seu jeito, o que precisa fazer. Sem essa configuração, use o texto de [Cole na sua IA](#cole-na-sua-ia).

- **Aplicar o feedback que deixaram no arquivo.** Diga: "Corrige o que comentaram nessa página". O `figma-comment-fix-loop` lê os comentários abertos, corrige cada um no frame onde o pino está e te entrega a evidência.
- **Conferir uma tela antes de dizer que está pronta.** Diga: "Essa tela tá pronta?" O `figma-slop-check` procura sinais de geração automática e falhas de precisão; depois `figma-handoff-gate` confere o que o dev precisa.
- **Criar ou editar sem quebrar o arquivo.** Diga: "Adiciona um estado vazio nessa tela". O `figma-preflight` confirma o alvo, os tokens e os componentes que já existem antes de escrever um nó.
- **Entender um arquivo que você acabou de abrir.** Cole a URL do Figma. O `figma-orient` mapeia páginas, componentes e variáveis e guarda o mapa para a próxima vez.

## O que dá errado e o que evita

**1. Parece certo até você clicar na camada.**
Sem orientação, o agente usa valor solto e desenha do zero o que já existe na biblioteca. Em poucas sessões, uma feature pode acumular dezenas de ícones desenhados à mão. Cada edição parecia inofensiva. O `figma-preflight` faz o agente procurar o componente e o ícone de verdade antes de editar qualquer coisa.

**2. O agente disse que funcionou. Nada mudou.**
Uma camada dentro de um grupo bloqueado ignora a alteração sem dar erro. Num lote grande de vínculos de variável, alguns não foram aplicados, e mesmo assim a conferência de cor passou, porque nada tinha mudado. A regra que saiu disso: depois de editar, leia de volta a propriedade que você mudou, nunca um sinal indireto dela.

**3. A Plugin API não se comporta como você imagina.**
O `figma-canon` carrega a lista do que me surpreendeu, cada item com sintoma, causa e correção. Tem [alguns deles](#alguns-dos-gotchas) mais abaixo.

**4. Você vira o intermediário entre cada comentário e cada correção.**
O `figma-comment-fix-loop` puxa os comentários abertos, trata cada um no frame onde o pino está e devolve uma lista que liga cada comentário à mudança e a uma captura, ou ao motivo de ter ficado aberto.

**5. O handoff desenha o "adicionar" e esquece o "remover".**
O dev constrói o que está desenhado e adivinha o resto. O `figma-handoff-gate` lista cada elemento interativo e pergunta para onde ele leva. Se uma direção existe, o caminho de volta também tem que existir.

**6. A bridge caiu de novo.**
O `figma-bridge-doctor` cuida da conexão entre o agente e o Figma Desktop. Ele tenta primeiro o menor conserto e pergunta antes de fechar o Figma.

## As skills

- **[`figma-canon`](../skills/figma-canon/SKILL.md)** · Sempre que o assunto é Figma. A base de conhecimento: regras da Plugin API, gotchas, auto layout, nomes, cobertura de estados, formato de handoff. Carrega só o pedaço que a tarefa pede.
- **[`figma-preflight`](../skills/figma-preflight/SKILL.md)** · Antes de toda edição. Conferência que não edita nada. Libera a edição ou devolve a lista do que falta. Também audita fluxo: tela órfã e botão que não leva a lugar nenhum.
- **[`figma-orient`](../skills/figma-orient/SKILL.md)** · Primeiro contato com um arquivo. Monta o mapa do arquivo e salva no seu projeto.
- **[`figma-slop-check`](../skills/figma-slop-check/SKILL.md)** · Depois de editar. Pega design com cara de máquina e design impreciso.
- **[`figma-handoff-gate`](../skills/figma-handoff-gate/SKILL.md)** · Antes do handoff. Ação completa, qualidade da anotação, prova na escala certa, arquivo sem rastro do processo.
- **[`figma-comment-fix-loop`](../skills/figma-comment-fix-loop/SKILL.md)** · Quando chega feedback. Do comentário à correção, com evidência.
- **[`figma-click-flow`](../skills/figma-click-flow/SKILL.md)** · "Vira isso em fluxo". Desenha as setas do elemento clicável até a tela de destino.
- **[`figma-bridge-doctor`](../skills/figma-bridge-doctor/SKILL.md)** · Problema de conexão. Diagnostica e recupera a conexão da Desktop Bridge (macOS).

## Alguns dos gotchas

De [`plugin-api-anomalies.md`](../skills/figma-canon/references/plugin-api-anomalies.md) e [`field-notes.md`](../skills/figma-canon/references/field-notes.md):

- [Uma section vinculada a uma variável de cor mostra a cor que você passou, não a da variável.](../skills/figma-canon/references/field-notes.md#a-section-fill-bound-to-a-variable-renders-the-base-color-you-passed) Resolva a variável antes de vincular.
- [Alteração dentro de um grupo bloqueado falha sem aviso.](../skills/figma-canon/references/field-notes.md#writes-to-descendants-of-a-locked-node-fail-silently) O nó diz `locked: false`, o editor recusa mesmo assim e nada dá erro.
- [O `instance.resize()` deixa o ícone no tamanho cheio dentro de uma caixa pequena.](../skills/figma-canon/references/plugin-api-anomalies.md#instanceresize-does-not-scale-the-children-use-rescale) Use `rescale()`.
- [Trocar um nó dentro do componente principal apaga o override de todas as instâncias.](../skills/figma-canon/references/plugin-api-anomalies.md#replacing-a-node-inside-a-master-wipes-the-override-on-every-instance) Guarde os overrides antes da troca e aplique de volta depois.
- [O `clone()` de um filho de section vai parar na página, não na section.](../skills/figma-canon/references/plugin-api-anomalies.md#clone-of-a-section-child-lands-at-page-level-not-in-the-section) A captura parece certa. A árvore de camadas mostra que não.
- [A exportação por REST pode ficar minutos atrás das suas edições.](../skills/figma-canon/references/plugin-api-anomalies.md#rest-v1images-renders-stale-cloud-state-after-plugin-edits) Confira o próprio PNG exportado, não o canvas.
- [O `setTimeout` nunca dispara no sandbox do plugin.](../skills/figma-canon/references/field-notes.md#settimeout-never-fires-in-the-plugin-sandbox) Um limite de tempo feito com ele não limita nada.
- [Mudar o `action` de uma reação de protótipo não faz nada.](../skills/figma-canon/references/field-notes.md#re-pointing-a-reaction-write-actions-not-action) O Figma lê `actions`, e a chamada ainda volta com sucesso.
- [O `getNodeByIdAsync` pode travar em vez de dar erro](../skills/figma-canon/references/plugin-api-anomalies.md#getnodebyidasync-hangs-does-not-throw-in-large-multi-page-files) num arquivo grande, com muitas páginas.

Os dois arquivos reúnem mais de 80 notas como essas, sobre a Plugin API, a bridge e o uso de vários agentes no mesmo arquivo. A Figma e outras pessoas mantêm listas próprias. Estas são as que eu aprendi em produção, quase todas pela bridge do figma-console.

## O que você precisa

- **Figma Desktop** para macOS ou Windows. A versão do navegador não basta: a bridge é um plugin de desenvolvimento, e a Figma só importa esse tipo de plugin no app.
- **[figma-console-mcp](https://github.com/southleft/figma-console-mcp)**, da Southleft (MIT). Roda na sua máquina e conversa com o Figma pelo plugin Desktop Bridge. Estas skills foram escritas para a ferramenta `figma_execute` dele. Última conferência: v1.40.8.
- **Node.js 18 ou mais novo.**
- **Um cliente MCP que carregue Agent Skills.** Eu uso o Claude Code.
- **Um token pessoal da Figma** para o fluxo de comentários, com File content (leitura), File versions (leitura), Variables (leitura) e Comments (leitura e escrita). Ele serve para chamadas REST, como ler comentário. O trabalho no canvas passa pela bridge.

No Claude Code, a configuração é esta. Em outros clientes, siga o [guia do projeto original](https://github.com/southleft/figma-console-mcp#readme).

```bash
claude mcp add figma-console -s user -e FIGMA_ACCESS_TOKEN=figd_YOUR_TOKEN_HERE -e ENABLE_MCP_APPS=true -- npx -y figma-console-mcp@latest
```

1. Reinicie o Claude Code para ele subir o servidor. Na primeira vez, o servidor cria o manifesto do plugin.
2. No Figma Desktop, abra um arquivo e vá em Plugins, Development, Import plugin from manifest. Escolha `~/.figma-console-mcp/plugin/manifest.json` (`~` é a sua pasta de usuário).
3. Rode o plugin Figma Desktop Bridge no arquivo em que você vai trabalhar.
4. Peça ao agente: "confere a conexão com o Figma". Ele deve chamar `figma_get_status`.

Esse comando grava o token em texto puro na configuração do agente, e ele pode ficar no histórico do terminal. Trate os dois como segredo e nunca suba a configuração para o Git. Quando o figma-console-mcp atualiza, as notas da versão às vezes pedem para importar o manifesto de novo.

**Usa só o MCP oficial da Figma?** Eu não validei estas skills lá: escrevi e usei tudo pela bridge do figma-console. A ferramenta `use_figma` dele também executa código da Plugin API, então o `figma-canon`, o `figma-slop-check` e o `figma-handoff-gate` continuam valendo como regras e checklists, e o `figma-preflight` aceita esse servidor como caminho de edição.

**Quanto custa.** Este repositório e o figma-console-mcp são gratuitos e de código aberto. O agente e o seu plano da Figma não estão incluídos.

## O hook opcional

O `hooks/figma-canon-precheck.py` lê o script que o agente vai rodar no Figma e avisa sobre padrões que costumam falhar, antes de a chamada chegar ao Figma. Nada neste repositório instala esse hook. Para ligar no Claude Code, coloque isto no seu `settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__figma-console__figma_execute(_across_files)?",
        "hooks": [
          { "type": "command", "command": "python3 /caminho/para/figma-maxxing/hooks/figma-canon-precheck.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```

Por padrão ele só acrescenta avisos. Com `FIGMA_PRECHECK_MODE=block`, ele recusa os padrões marcados como `BLOCK` (eles falham num arquivo de Design).

## Serve para, não serve para

| Serve para | Não serve para |
|---|---|
| Arquivo que já tem componentes, variáveis e time | Gerar um produto inteiro a partir de uma frase |
| Rodada de feedback, limpeza, cobertura de estados, handoff | Substituir o julgamento do designer sobre o que construir |
| Agente que edita pela bridge do figma-console | Ambiente sem o app (a bridge precisa do Figma Desktop) |
| macOS, nos scripts de recuperação | Automação da bridge em Windows ou Linux (as skills em si são Markdown) |

## Até onde foi testado

Eu construí estas skills no Claude Code, no macOS, com o figma-console-mcp, no meu próprio trabalho. Esta edição pública é uma reescrita daquele conjunto: traduzida para o inglês, generalizada e sem nenhum nome ou detalhe que identifique cliente. O lock, o hook e o instalador têm testes automáticos que rodam a cada push. Ainda não rodei a edição pública de ponta a ponta numa segunda máquina. Se alguma coisa ainda depender do meu ambiente, [abra uma issue](https://github.com/thiagoxikota/figma-maxxing/issues) com o seu ambiente e o erro exato.

## Contribuir

A melhor contribuição é um problema que você encontrou de verdade, com sintoma, causa e correção. Veja o [CONTRIBUTING.md](../CONTRIBUTING.md), o [código de conduta](../CODE_OF_CONDUCT.md) e o [changelog](../CHANGELOG.md). As notas de segurança estão no [SECURITY.md](../SECURITY.md).

## Créditos

Feito em cima do [figma-console-mcp](https://github.com/southleft/figma-console-mcp), da Southleft. O formato das skills é o padrão aberto [Agent Skills](https://agentskills.io).

Sem vínculo com a Figma. Figma é marca registrada da Figma, Inc.

## Licença

MIT. Veja [LICENSE](../LICENSE).
