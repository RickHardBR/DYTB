# 📜 Histórico de Desenvolvimento - DYTB Downloader

Este documento registra todas as decisões de arquitetura, correções, implementações e passos de compilação realizados no projeto **DYTB Downloader**.

---

## 📌 Visão Geral do Projeto
O **DYTB Downloader** é uma aplicação desktop desenvolvida em Python com CustomTkinter para download e conversão de vídeos e áudios do YouTube em múltiplos formatos e qualidades.

---

## 🛠️ Modificações e Implementações Realizadas

### 1. Salvamento e Conversão de Áudio (.MP3, .WAV, .M4A)
- Integração da extração e conversão de áudio com suporte ao FFmpeg.
- Parâmetros configurados para garantir saída em `.mp3` de alta qualidade (`--audio-quality 0`).
- Validação e preservação de estabilidade em todos os formatos suportados.

---

### 2. Lapidação da Janela "Sobre" (`ui/about_dialog.py`)
- **Créditos do Desenvolvedor**:
  - Inclusão do texto: `"Desenvolvido por "` com ícone oficial da **codeLine** (`codeline.png`).
  - Link interativo estilizado para **RickHardDev**, que redireciona para o perfil no Instagram:
    👉 [`https://www.instagram.com/rick.hard.dev/`](https://www.instagram.com/rick.hard.dev/)
- **Dimensões e Layout**:
  - Ajuste de espaçamento para acomodar os novos elementos sem cortes visuais.
  - Carregamento de recursos transparente tanto em ambiente de desenvolvimento quanto em executável congelado (`sys._MEIPASS`).

---

### 3. Correção do Cálculo e Exibição de Porcentagem (`core/downloader.py`)
- **Problema Identificado**:
  - A marcação de download ficava fixa em `1.0%` até o final do processo, aparentando travamento para o usuário. Isso ocorria porque o `yt-dlp`, ao rodar com `--print after_move:filepath` e saída redirecionada/pipe, suprimia os eventos padrão de progresso.
- **Solução Aplicada**:
  - Inclusão explícita das flags `--progress` e `--progress-template`:
    ```text
    download:[download] %(progress._percent_str)s of %(progress._total_bytes_str|progress._total_bytes_estimate_str)s at %(progress._speed_str)s ETA %(progress._eta_str)s
    ```
  - Aprimoramento da função `parse_progress_line()` para filtrar termos nulos (`Unknown`, `NA`) e exibir com precisão:
    - Porcentagem atualizada (`XX.X%`)
    - Tamanho baixado / tamanho total (`de 15.30MiB`)
    - Velocidade da conexão (`(34.03MiB/s)`)
    - Tempo estimado restante (`ETA: 00:00`)

---

### 4. Resolução Autônoma de Binários (`core/installer.py` e `core/downloader.py`)
- Adicionada a pasta `bin/` contendo os binários standalone para Windows:
  - `yt-dlp.exe`
  - `ffmpeg.exe`
- O `core/installer.py` foi atualizado para priorizar o carregamento de binários na seguinte ordem:
  1. Diretório temporário do PyInstaller (`sys._MEIPASS` e `sys._MEIPASS/bin`)
  2. Diretório local da aplicação (`<app_root>/bin`)
  3. Variáveis de ambiente do sistema (`PATH`, WinGet, Python Scripts)
- O `build_ytdlp_command()` passa explicitamente `--ffmpeg-location` apontando para a pasta onde o `ffmpeg.exe` estiver localizado.

---

### 5. Criação das Duas Versões de Distribuição

#### 🔹 Versão 1: Executável Portátil (`DYTB.exe`)
- **Finalidade:** Arquivo único (*One-File*), 100% autônomo e portátil.
- **Funcionamento:** Não requer instalação de Python, nem de FFmpeg, nem de yt-dlp na máquina do usuário. Basta clicar duas vezes para executar.
- **Configuração no PyInstaller (`DYTB.spec`):**
  - Empacota `DW.ico`, `codeline.png`, `bin/yt-dlp.exe` e `bin/ffmpeg.exe`.

#### 🔹 Versão 2: Instalador Windows (`DYTB_Setup.exe`)
- **Finalidade:** Instalador tradicional para Windows com assistente em Português do Brasil.
- **Recursos gerados pelo Inno Setup (`installer.iss`):**
  - Instala o programa e binários em `C:\Arquivos de Programas\DYTB Downloader` (ou pasta escolhida).
  - Cria atalho na **Área de Trabalho** com o ícone `DW.ico`.
  - Cria atalho no **Menu Iniciar**.
  - Cria entrada no **Painel de Controle** para desinstalação completa e limpa.

---

### 6. Automação de Compilação (`build.bat`)
O script `build.bat` foi atualizado para realizar todo o ciclo de build em um único clique:
1. Instala dependências do `requirements.txt`.
2. Compila a versão portátil com `pyinstaller --noconfirm DYTB.spec`.
3. Copia `dist/DYTB.exe` para a raiz.
4. Compila o instalador `dist/DYTB_Setup.exe` via Inno Setup (`ISCC.exe`) e copia para a raiz.

---

## 📁 Estrutura Atual dos Arquivos Principais

```text
DYTB/
├── bin/
│   ├── ffmpeg.exe           # Binário standalone do FFmpeg
│   └── yt-dlp.exe           # Binário standalone do yt-dlp
├── core/
│   ├── downloader.py        # Lógica de download, progresso e chamada aos binários
│   ├── formats.py           # Formatos suportados e validação de URLs
│   ├── history.py           # Persistência do histórico de downloads
│   ├── installer.py         # Resolução e priorização de PATH e binários
│   └── settings.py          # Preferências do usuário (qualidade, pastas)
├── ui/
│   ├── about_dialog.py      # Janela Sobre com RickHardDev, link e ícone codeLine
│   ├── dialogs.py           # Diálogos de progresso, erros e confirmações
│   ├── history_window.py    # Interface do histórico
│   ├── main_window.py       # Janela principal do aplicativo
│   └── settings_window.py   # Janela de configurações
├── app.py                   # Ponto de entrada principal
├── build.bat                # Script para compilar DYTB.exe e DYTB_Setup.exe
├── codeline.png             # Logo da codeLine utilizado na interface
├── DW.ico                   # Ícone oficial da aplicação
├── DYTB.exe                 # Executável portátil gerado
├── DYTB_Setup.exe           # Instalador Windows gerado
├── DYTB.spec                # Especificação do PyInstaller
├── historico.md             # Registro histórico de decisões e mudanças
├── installer.iss            # Script Inno Setup para gerar DYTB_Setup.exe
├── requirements.txt         # Dependências Python (customtkinter, pillow, darkdetect)
└── test_app.py              # Bateria de testes automatizados
```

---

## 🚀 Como Recompilar no Futuro

Para gerar novamente os executáveis após qualquer modificação no código:
```cmd
build.bat
```
Ou manualmente pelo terminal:
```cmd
# 1. Gerar versão portátil
pyinstaller --noconfirm DYTB.spec

# 2. Gerar instalador Setup
"C:\Users\RickHard\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss
```
