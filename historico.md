# 📜 Histórico de Desenvolvimento - DYTB Downloader

Este documento registra todas as decisões de arquitetura, correções, modernização visual, solução de bugs e passos de compilação do projeto **DYTB Downloader**.

---

## 📌 Visão Geral do Projeto
O **DYTB Downloader** é uma aplicação desktop desenvolvida em Python com CustomTkinter para download e conversão de vídeos e áudios do YouTube em múltiplos formatos e qualidades, com empacotamento 100% autônomo (sem necessidade de instalar Python, FFmpeg ou yt-dlp à parte).

---

## 🛠️ Registro Cronológico de Alterações e Melhorias

### 1. Salvamento e Extração de Áudio (.MP3, .WAV, .M4A)
- Extração de áudio de alta qualidade integrada com FFmpeg (`--audio-quality 0`).
- Suporte a seleção de formatos de áudio (`mp3`, `wav`, `m4a`) desabilitando seletores de resolução desnecessários.
- Preservação da lógica e estabilidade dos downloads de vídeo (`mp4`, `webm`, `mkv`) com resolução até 1080p.

---

### 2. Lapidação da Janela "Sobre" (`ui/about_dialog.py`)
- **Créditos do Desenvolvedor**:
  - Inserção do crédito oficial: `"Desenvolvido por "` acompanhado do ícone da **codeLine** (`codeline.png`).
  - Link interativo estilizado para **RickHardDev**, direcionando para o perfil:
    👉 [`https://www.instagram.com/rick.hard.dev/`](https://www.instagram.com/rick.hard.dev/)
- Ajuste das dimensões da janela para acomodar os novos elementos sem cortes visuais.

---

### 3. Correção do Cálculo de Porcentagem em Tempo Real (`core/downloader.py`)
- **Causa do problema anterior:** O `yt-dlp`, ao rodar com `--print after_move:filepath` e saída redirecionada em pipe, suprimia os eventos padrão de download, travando a UI em `1.0%`.
- **Solução implementada:**
  - Adicionadas as flags `--progress` e `--progress-template`:
    ```text
    download:[download] %(progress._percent_str)s of %(progress._total_bytes_str|progress._total_bytes_estimate_str)s at %(progress._speed_str)s ETA %(progress._eta_str)s
    ```
  - Aprimoramento da função `parse_progress_line()` para filtrar termos nulos (`Unknown`, `NA`) e exibir com precisão a porcentagem, tamanho total, velocidade de conexão e ETA.

---

### 4. Empacotamento Autônomo e Versões de Distribuição
Foram disponibilizadas duas formas oficiais de distribuição:

#### 🔹 Versão 1: Executável Portátil (`DYTB.exe`)
- Arquivo único (*One-File*), ~89 MB.
- Contém `yt-dlp.exe` e `ffmpeg.exe` embutidos internamente via PyInstaller (`DYTB.spec`).
- Roda imediatamente com 2 cliques sem exigir instalação prévia de nenhuma dependência.

#### 🔹 Versão 2: Instalador Windows (`DYTB_Setup.exe`)
- Instalador gerado com **Inno Setup 6** (`installer.iss`), ~133 MB.
- Assistente em **Português do Brasil**.
- Cria atalhos na Área de Trabalho e no Menu Iniciar com o ícone `DW.ico`.
- Registra desinstalador limpo no Painel de Controle do Windows.

---

### 5. Isolamento e Publicação no GitHub
- **Desvinculação do Repositório Pai (`fenixdieta`):**
  - O diretório `DYTB` foi removido do cache do repositório pai (`git rm --cached DYTB`) e ignorado via `.gitignore` para evitar conflitos de repositórios aninhados (*submodules/gitlinks*).
- **Repositório Independente Criado e Sincronizado:**
  - Repositório oficial: [`https://github.com/RickHardBR/DYTB.git`](https://github.com/RickHardBR/DYTB.git).
  - Branch padrão: `main`.
  - `.gitignore` configurado para não subir binários pesados (`.exe`, `bin/`, `dist/`, `build/`, `__pycache__/`).
  - [`README.md`](file:///j:/RickHardBR/DYTB/README.md) completo criado com badges, imagem de prévia da interface, guia de instalação e compilação.
  - Arquivo `LICENSE` (MIT) adicionado.

---

### 6. Modernização Visual Completa (Design Dark/Neon Cyber)
A interface foi reformulada para seguir a identidade visual moderna da **Imagem 1**:

- **Paleta de Cores e Estética:**
  - Fundo Deep Navy / Charcoal (`#0b121c` e `#0e1622`).
  - Contêiner principal com borda **Ciano Neon** (`#06b6d4`).
  - Destaques em Esmeralda (`#10b981`) e Azul Céu (`#38bdf8`).
- **Header Superior:**
  - Logo oficial da codeLine + Título `DYTB Downloader` + tag de versão `v1.0.0`.
- **Seção de URL:**
  - Campo de entrada com destaque de borda e botão `Colar Link` integrado.
- **Card "CONFIGURACOES DE DOWNLOAD":**
  - Seletores estilizados de `Formato de Saida`, `Qualidade / Resolucao` e linha de destino com botão `Alterar Pasta...`.
- **Botão Principal de Download:**
  - Botão de destaque `Baixar Conteudo` com cantos arredondados e efeito hover.
- **Card Integrado "DOWNLOADS ATIVOS":**
  - Exibição do título do download em andamento diretamente na janela principal.
  - Barra de progresso ciano neon contínua.
  - Linha de métricas com status detalhado, velocidade e tempo restante (ETA).
  - Botão `Abrir Arquivo` exibido automaticamente ao concluir.
- **Barra de Navegação no Rodapé:**
  - Abas inferiores organizadas: `Downloads` (com destaque ativo), `Historico`, `Configuracoes` e `Sobre`.

---

### 7. Resolução do Bug de Inicialização Fantasma (Processo no Gerenciador de Tarefas)
- **Problema Diagnosticado:**
  - O aplicativo aparecia nos processos do Gerenciador de Tarefas, mas a janela não abria na tela.
- **Causas Raiz Identificadas:**
  1. *Conflito de codificação de caracteres unicode:* Emojis e setas unicode exóticas (como `⬇` `\u2b07` e `⤓` `\u2913`) causavam exceção oculta no subsistema de fontes e charmap do Windows (`'charmap' codec can't encode character`).
  2. *Prioridade de exibição no Windows 11:* A janela não estava sendo forçada para o topo ao inicializar a partir do executável congelado.
  3. *Ordem de empacotamento:* A barra de navegação inferior precisava ter seu espaço reservado antes da expansão dos componentes superiores.
- **Soluções Aplicadas:**
  - Substituição de símbolos unicode por renderização via imagem PIL (`codeline.png`) e strings 100% seguras.
  - Inclusão do ciclo de ativação de foco forçado no `app.py` (`root.attributes("-topmost", True)` seguido de liberação de foco).
  - Empacotamento estruturado e logs de diagnóstico detalhados para auditoria.

---

### 8. Implementação de Múltiplos Downloads e Fila Dinâmica
- **Extração Inteligente de URLs em Lote (`core/formats.py`):**
  - Criação da função `extract_urls()` capaz de parsear blocos de texto contendo múltiplos links do YouTube separados por novas linhas, vírgulas, ponto-e-vírgula ou espaços, com deduplicação e validação automática.
- **Gerenciador de Fila Assíncrono (`core/queue_manager.py`):**
  - Criação da classe `DownloadItem` e `DownloadQueueManager`.
  - Processamento sequencial em thread dedicada em background, evitando bloqueios na interface e sobrecarga de banda.
  - Callbacks thread-safe (`on_item_updated` e `on_queue_finished`) para sincronização em tempo real com a UI CustomTkinter via `parent.after()`.
  - Suporte a cancelamento individual (`cancel_item`), cancelamento em lote (`cancel_all`) e limpeza de itens finalizados (`clear_completed`).
- **Interface Visual Moderna de Fila (`ui/main_window.py`):**
  - Transformação do card de downloads em uma lista com barra de rolagem (`CTkScrollableFrame`).
  - Cards individuais para cada item da fila exibindo:
    - Título do vídeo / nome personalizado.
    - Barra de progresso ciano neon individual.
    - Status dinâmico (`Aguardando...`, `Baixando...`, `Concluído`, `Erro`, `Cancelado`).
    - Métricas em tempo real (velocidade de download e tempo restante ETA).
    - Botões contextuais de ação direta: `Abrir Arquivo` (após conclusão), `✕ Cancelar` (durante execução/espera) e `Remover` (para itens finalizados/cancelados/erro).
  - Botões globais de cabeçalho: `Cancelar Todos` e `Limpar Finalizados`.
- **Cobertura de Testes Automatizados (`test_app.py`):**
  - Testes unitários para `extract_urls()` e ciclo de vida do `DownloadQueueManager` (10 testes 100% aprovados).

---

### 9. Sanitização Automática de URLs do YouTube e Atualização do yt-dlp
- **Diagnóstico do Erro com Links de Rádio/Mix:**
  - URLs copiadas diretamente de mixes automáticos do YouTube (ex: `&list=RD...&start_radio=1`) causavam exceção de extração no `yt-dlp` ao rodar com `--no-playlist`.
- **Sanitização de URLs (`core/formats.py` e `core/downloader.py`):**
  - Criação da função `clean_youtube_url(url)` que extrai o ID limpo do vídeo (`https://www.youtube.com/watch?v=VIDEO_ID`) e descarta parâmetros de tracking, rádio (`list=RD...`), índices (`index=...`) e timestamps (`t=...`).
  - Integração da limpeza em lote no `extract_urls` e na construção de comandos do `yt-dlp`.
- **Atualização do Binário `yt-dlp.exe`:**
  - Atualização do executável embutido em `bin/yt-dlp.exe` para a versão mais recente oficial do GitHub.
- **Testes Unitários:**
  - Suíte de 11 testes automatizados cobrindo links com rádio/mix, links curtos (`youtu.be`) e parâmetros de tracking.

---

### 10. Expansão para Downloader Multi-Plataforma & Streams Fragmentados (HLS/DASH)
- **Detecção Inteligente de Plataforma (`core/formats.py`):**
  - Implementação da função `detect_platform(url)` com suporte a:
    - YouTube, Vimeo, TikTok, Instagram, Twitter / X, Facebook, Twitch, Dailymotion.
    - Plataformas de cursos/EAD: Hotmart, DIO (`web.dio.me`), Panda Video, Wistia.
    - Protocolos de streaming: HLS (`.m3u8`), DASH (`.mpd`), Vídeos Diretos (`.mp4`, `.webm`, `.mkv`, `.ts`).
- **Validador e Sanitizador Universal de Links (`validate_media_url`, `clean_media_url`):**
  - Validação aberta para URLs de streaming e websites de vídeo em geral.
  - Limpeza de parâmetros de tracking de redes sociais (`igsh`, `utm_*`, `si`, `fbclid`) preservando tokens de autenticação em manifests `.m3u8` e `.mpd`.
- **Pipeline de Fusão de Segmentos Fragmentados (`core/downloader.py`):**
  - Configuração do pipeline para download concorrente de fragmentos (`--concurrent-fragments 5`, `--hls-prefer-native`, `--fragment-retries 10`).
  - Fusão e conversão automática contínua de blocos `.ts`/`.m4s` em arquivo `.mp4`/`.mp3` final sem perdas via FFmpeg embutido.
  - Inclusão de User-Agent moderno padrão para evitar bloqueios de anti-hotlink em embeds.
- **Interface Visual Aprimorada (`ui/main_window.py`):**
  - Badge de identificação da plataforma em cada card da fila de download (`[YouTube]`, `[Vimeo]`, `[TikTok]`, `[HLS Stream]`, `[Hotmart]`, `[DIO]`).
  - Textos e placeholders de entrada adaptados para links e streams universais.
- **Suíte de Testes Automatizados (`test_app.py`):**
  - 12 testes unitários cobrindo todas as plataformas e tipos de stream com 100% de aprovação.

---

### 11. Autenticação por Sessão do Navegador (Cookies) para Vídeos Privados & Normalização de Rotas
- **Download de Vídeos Privados e Cursos Logados (`core/settings.py` e `core/downloader.py`):**
  - Implementação do suporte a injeção de cookies de sessão ativa de navegadores (`--cookies-from-browser`):
    - Opções suportadas: Google Chrome, Microsoft Edge, Mozilla Firefox, Brave Browser e Opera.
    - Permite baixar Reels de contas privadas seguidas no Instagram, vídeos protegidos por idade no YouTube e aulas de cursos EAD autenticados (Hotmart, DIO, etc.).
- **Normalização Avançada de Rotas e Embeds (`core/formats.py`):**
  - Instagram: correção e redirecionamento de rotas plurais (`/reels/ID` -> `/reel/ID`) e `/tv/ID` -> `/reel/ID`.
  - Vimeo: normalização de URLs de player embutido (`player.vimeo.com/video/ID` -> `vimeo.com/ID`) com preservação de hash de privacidade (`?h=...`).
  - Redes Sociais: remoção completa de parâmetros de tracking de link compartilhado (`igsh`, `si`, `fbclid`, `utm_*`).
- **Resiliência e Fallbacks de Formatos no Pipeline (`core/downloader.py`):**
  - Implementação do seletor resiliente de formato (`bestvideo*+bestaudio/best`) garantindo que fluxos únicos progressivos de vídeo (comuns no Vimeo, Instagram e TikTok) não falhem ao procurar trilhas de áudio/vídeo separadas.
  - Injeção automática de cabeçalhos `Referer` (`https://vimeo.com/`) e `User-Agent` de navegador desktop.
- **Configurações com Seletor de Autenticação (`ui/settings_window.py`):**
  - Novo seletor intuitivo na janela de Configurações para escolher o navegador utilizado nas sessões logadas.
- **Testes Automatizados (`test_app.py`):**
  - 14 testes unitários cobrindo injeção de cookies e normalizações com 100% de sucesso.

---

## 📁 Estrutura Atual dos Arquivos do Projeto

```text
DYTB/
├── bin/
│   ├── ffmpeg.exe           # Binário standalone do FFmpeg (ignorado no git)
│   └── yt-dlp.exe           # Binário standalone do yt-dlp (ignorado no git)
├── core/
│   ├── __init__.py
│   ├── downloader.py        # Execução de download, extração de áudio e parse de progresso
│   ├── formats.py           # Formatos suportados e extração de múltiplas URLs
│   ├── history.py           # Persistência e gerenciamento do histórico em JSON
│   ├── installer.py         # Priorização de binários embutidos e resolução de PATH
│   ├── queue_manager.py     # Gerenciador de fila assíncrono para múltiplos downloads
│   └── settings.py          # Preferências do usuário (pasta padrão, formato, qualidade)
├── ui/
│   ├── __init__.py
│   ├── about_dialog.py      # Janela Sobre com RickHardDev, link Instagram e logo codeLine
│   ├── dialogs.py           # Diálogos de nome customizado, erros e confirmações
│   ├── history_window.py    # Interface do histórico de downloads
│   ├── main_window.py       # Janela principal moderna com fila de downloads e scroll
│   └── settings_window.py   # Janela de configurações
├── docs/
│   └── screenshots/
│       └── preview.jpg      # Imagem de demonstração para o README
├── app.py                   # Ponto de entrada da aplicação e controle de inicialização
├── build.bat                # Script de compilação 1-clique (PyInstaller + Inno Setup)
├── codeline.png             # Logo oficial codeLine
├── DW.ico                   # Ícone oficial da aplicação
├── DYTB.exe                 # Executável portátil gerado (ignorado no git)
├── DYTB_Setup.exe           # Instalador Windows oficial gerado (ignorado no git)
├── DYTB.spec                # Especificação de empacotamento do PyInstaller
├── historico.md             # Documento histórico de alterações e arquitetura
├── installer.iss            # Script Inno Setup para compilação do instalador
├── LICENSE                  # Licença MIT
├── README.md                # Documentação completa do repositório GitHub
├── requirements.txt         # Dependências do projeto (customtkinter, pillow, darkdetect)
└── test_app.py              # Bateria de testes unitários automatizados
```

---

### 11. Sistema Inteligente de Diagnóstico de Erros e Suporte Multi-Plataforma Avançado

- **Resolução de Downloads no Vimeo e URLs Restritas**:
  - Implementada conversão inteligente em `core/formats.py` para redirecionar links `vimeo.com/ID` para o player embed desimpedido `https://player.vimeo.com/video/ID` com cabeçalho `--referer "https://vimeo.com/"`, permitindo o download em alta definição de vídeos sem necessidade de login na interface web.
  - Normalização automática de rotas do Instagram (`/reels/` -> `/reel/`), TikTok, Twitter/X, plataformas EAD (Hotmart, DIO, Panda Video) e streams diretos HLS (`.m3u8`) e DASH (`.mpd`).

- **Gerenciamento Resiliente de Cookies e Fallback Automático**:
  - Injeção flexível de autenticação via sessão de navegadores (Chrome, Edge, Firefox, Brave, Opera, Vivaldi) ou arquivo `cookies.txt`.
  - Mecanismo de recuperação automática: caso o Windows bloqueie o SQLite de cookies por o navegador estar em execução (`Could not copy cookie database`), o motor tenta automaticamente o download direto sem cookies antes de reportar falha.

- **Diagnóstico e Relatório de Erros Amigável (`ErrorDetailsDialog`)**:
  - **Fim do Truncamento Feio**: O card de download não trunca mais mensagens com `...` no meio do texto técnico. Em vez disso, exibe um resumo claro e em Português do Brasil (ex: `✕ Exige autenticação / login`).
  - **Botão [Ver Detalhes]**: Adicionado no card de download com falha, abrindo um modal completo no estilo Dark/Cyber Neon.
  - **Diagnóstico Passo a Passo**: O modal apresenta o motivo real do erro (vídeo privado, login necessário, bloqueio de navegador, 404, etc.) e o passo a passo exato para o usuário resolver.
  - **Caixa de Log Técnico com [Copiar Log]**: Permite copiar o log bruto do extrator com 1 clique para suporte ou depuração.
  - **Atalho Direto para Configurações**: Botão `[⚙ Ajustar Cookies nas Configurações]` dentro do modal de erro para facilitar a configuração imediata.

- **Bateria de Testes Unitários Automatizados**:
  - Expandida para **15 testes unitários** em `test_app.py`, validando detecção de plataformas, limpeza de URLs, injeção de cookies, fila assíncrona e tradução/formatação de erros. Todos os testes passam com 100% de sucesso.

---

### 12. Extração de Manifestos de Streaming HLS/DASH e Dados do Player Hotmart

- **Leitura Automática de JSON e Mídias de Cursos**:
  - Implementado parser inteligente em `core/formats.py` que reconhece quando o usuário cola dados de depuração JSON do player (`"mediaCode"`) ou URLs de manifesto `.m3u8`/`.mpd`.
  - Converte automaticamente para o endpoint de embed correspondente ou extrai diretamente a URL do manifesto para o motor de download.
- **Isolamento e Preservação de Plataformas**:
  - Todas as plataformas anteriores (YouTube, Vimeo, Instagram, TikTok, etc.) permanecem 100% operacionais e preservadas, sem efeitos colaterais.
- **Bateria de Testes Unitários Automatizados**:
  - Expandida para **16 testes unitários** em `test_app.py`, validando detecção de plataformas, limpeza de URLs, injeção de cookies, fila assíncrona, extração de manifestos e tradução/formatação de erros. Todos os testes passam com 100% de sucesso.

---

### 13. Versão 1.1.0 - Navegador Sniffer EAD Integrado (Sem Tokens Chumbados)

- **Lançamento Oficial da Versão v1.1.0**:
  - Aumento da versão de `v1.0.0` para `v1.1.0` em toda a interface gráfica, diálogos, documentação e instalador.
- **Navegador Sniffer EAD Integrado (`core/sniffer_process.py` e `core/sniffer_manager.py`)**:
  - **Captura em Tempo Real**: Novo navegador embutido (*WebView2*) que permite ao usuário navegar diretamente em plataformas de cursos fechadas (Hotmart Club, DIO, Panda Video, Kiwify, Eduzz, etc.) utilizando seu **próprio login e sessão**.
  - **Zero Tokens Chumbados**: O sistema não armazena nem fixa tokens ou IDs de usuários; cada aluno/usuário se conecta com suas próprias credenciais privadas.
  - **HUD Flutuante com Interceptador de Rede (JS Sniffer)**: O navegador injeta um interceptador de requisições (`fetch`, `XMLHttpRequest`, `<video>`, `MediaSource`) e um painel flutuante Dark/Neon que detecta streams de vídeo no momento em que o usuário clica em **Play**.
  - **Envio Direto para Download com 1 Clique**: Ao clicar em *"⬇ Enviar para Download no DYTB"*, o stream capturado é transmitido instantaneamente para a fila principal de downloads do aplicativo, montando o `.mp4` Full HD com o FFmpeg.
- **Integração na Interface Principal**:
  - Nova aba **"🌐 Sniffer EAD"** na barra de navegação inferior.
  - Botão **"🌐 Abrir no Navegador Sniffer EAD"** direto no modal de diagnóstico de erros para links de cursos fechados.
- **Empacotamento PyInstaller**:
  - Suporte completo a execução do processo do sniffer embutido via flag `--run-sniffer-url` no binário executável portátil `DYTB.exe` (~97 MB).

---

### 14. Versão 1.2.0 - Sniffer CDP Global com Suporte a Iframes, Painel Interativo e Fallback de Cookies

- **Lançamento Oficial da Versão v1.2.0**:
  - Atualização da versão para `v1.2.0` em toda a interface (`ui/main_window.py`, `ui/about_dialog.py`), instalador (`installer.iss`), `README.md` e histórico.
- **Sniffer CDP Global com Anexo Automático de Iframes (`core/sniffer_manager.py`)**:
  - **Suporte Total a Iframes EAD**: Configurado o Chrome DevTools Protocol (CDP) com `Target.setAutoAttach(autoAttach=True, waitForDebuggerOnStart=False, flatten=True)`. Isso permite capturar 100% dos manifestos de streaming emitidos por players embutidos em iframes isolados (como `content-player.hotmart.com`, Panda Video, Vimeo Embeds, etc.).
  - **Injeção de Hook JS Universal**: O sniffer injeta automaticamente (`Page.addScriptToEvaluateOnNewDocument`) scripts que monitoram chamadas `fetch`, `XMLHttpRequest` e tags `<video>` em todos os frames e sub-alvos, transmitindo os streams detectados via `Runtime.consoleAPICalled` para a aplicação.
  - **Perfil de Sessão Persistente**: Dados de login permanecem salvos em `%APPDATA%\DYTB\sniffer_browser_data`, garantindo que o usuário não precise relogar a cada abertura.
- **Painel Interativo de Controle (`ui/sniffer_dialog.py`)**:
  - Nova interface dedicada para o Sniffer EAD contendo indicador de status em tempo real (🟢 Conectado / 🔴 Fechado), campo para URL da aula, botão de iniciar/parar navegador, guia passo a passo e lista dinâmica de transmissões capturadas com botão de download no DYTB e cópia de link com 1 clique.
- **Resiliência e Fallback Automático de Cookies (`core/downloader.py`)**:
  - Eliminado o erro de bloqueio de banco SQLite do Chrome (`Could not copy Chrome cookie database`) para links diretos de streaming (.m3u8, .mpd) que já possuem tokens assinados na URL.
  - Implementado sistema de auto-recuperação e retry sem cookies caso ocorra qualquer bloqueio de banco de cookies do navegador em segundo plano.
- **Bateria de Testes Unitários Automatizados**:
  - Expandida para **17 testes unitários** em `test_app.py`, cobrindo validação de streams do sniffer, injeção de cookies e fallback automático. 100% de sucesso.

---

## 🚀 Como Recompilar o Projeto

Para gerar novamente as versões portátil e instalador após qualquer alteração:

```cmd
build.bat
```

O script executará automaticamente:
1. Instalação/atualização de dependências.
2. Compilação do executável portátil `DYTB.exe` com PyInstaller.
3. Compilação do instalador `DYTB_Setup.exe` com Inno Setup.


