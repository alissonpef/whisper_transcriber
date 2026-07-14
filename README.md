<a id="readme-top"></a>

<!-- ESCUDOS DO PROJETO -->

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![LinkedIn][linkedin-shield]][linkedin-url]

<!-- LOGOTIPO DO PROJETO -->
<br />
<div align="center">
  <a href="https://github.com/alissonpef/whisper_transcriber">
    <img src="assets/icon.png" alt="Logo" width="80" height="80">
  </a>

  <h3 align="center">Transcritor Whisper</h3>

  <p align="center">
    Uma ferramenta poderosa e elegante para transcrição de áudio local com refinamento por IA.
    <br />
    <a href="https://github.com/alissonpef/whisper_transcriber"><strong>Explore a documentação »</strong></a>
    <br />
    <br />
    <a href="https://github.com/alissonpef/whisper_transcriber/issues">Reportar Bug</a>
    &middot;
    <a href="https://github.com/alissonpef/whisper_transcriber/issues">Solicitar Recurso</a>
  </p>
</div>

<!-- ÍNDICE -->
<details>
  <summary>Índice</summary>
  <ol>
    <li>
      <a href="#sobre-o-projeto">Sobre O Projeto</a>
      <ul>
        <li><a href="#construído-com">Construído Com</a></li>
      </ul>
    </li>
    <li>
      <a href="#começando">Começando</a>
      <ul>
        <li><a href="#pré-requisitos">Pré-requisitos</a></li>
        <li><a href="#instalação">Instalação</a></li>
      </ul>
    </li>
    <li><a href="#uso">Uso</a></li>
    <li><a href="#contribuindo">Contribuindo</a></li>
    <li><a href="#licença">Licença</a></li>
    <li><a href="#contato">Contato</a></li>
  </ol>
</details>

<!-- SOBRE O PROJETO -->

## Sobre O Projeto

[![Captura de Tela do Produto][product-screenshot]](https://github.com/alissonpef/whisper_transcriber)

O **Transcritor Whisper** é uma aplicação desktop desenvolvida para transformar sua voz em texto de forma instantânea e privada. Utilizando modelos de última geração rodando localmente, ele garante que seus dados nunca saiam da sua máquina.

### Principais Características:
* **Privacidade Total:** Processamento 100% local (Whisper + LLM Local).
* **Refinamento por IA:** Botão "Reescrever" que utiliza um modelo Qwen local para limpar gaguejos, vícios de linguagem e melhorar a coesão do texto.
* **Agilidade:** Atalho global (`Ctrl+Shift+Espaço`) para iniciar/parar gravações de qualquer lugar do sistema.
* **Interface Moderna:** Design escuro e minimalista com animações fluidas e visualização de ondas sonoras em tempo real.
* **Resiliência:** Suporte a aceleração por hardware (CUDA) com fallback automático para CPU.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

### Construído Com

Esta seção lista as tecnologias principais e bibliotecas utilizadas neste projeto:

* [![Python][Python-shield]][Python-url]
* [![Tkinter][Tkinter-shield]][Tkinter-url]
* [![Faster-Whisper][Whisper-shield]][Whisper-url]
* [![Llama-cpp-python][Llama-shield]][Llama-url]
* [![Sounddevice][Sounddevice-shield]][Sounddevice-url]
* [![NumPy][NumPy-shield]][NumPy-url]

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

<!-- COMEÇANDO -->

## Começando

Siga os passos abaixo para configurar e executar o Transcritor Whisper localmente.

### Pré-requisitos

O projeto foi desenvolvido para ambientes Linux (especialmente distribuições baseadas em Debian/Ubuntu). Certifique-se de possuir instalado:

* **Python 3.10** ou superior
* **uv** (gerenciador de pacotes rápido para Python)
* **FFmpeg** (utilizado para decodificação de áudio)
* **PortAudio** (necessário para a biblioteca Sounddevice interagir com o microfone)

Para instalar os pacotes do sistema no Debian/Ubuntu:
```sh
sudo apt update
sudo apt install ffmpeg portaudio19-dev python3-tk
```

E para instalar o `uv`:
```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Instalação

1. Clone o repositório:
   ```sh
   git clone https://github.com/alissonpef/whisper_transcriber.git
   cd whisper_transcriber
   ```
2. Sincronize e crie o ambiente virtual com as dependências usando `uv`:
   ```sh
   uv sync
   ```
3. (Opcional) Execute o script de instalação para configurar o daemon e o atalho de inicialização automática:
   ```sh
   ./scripts/install.sh
   ```

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

<!-- EXEMPLOS DE USO -->

## Uso

1. **Executando a interface gráfica (Popup):**
   ```sh
   uv run python -m src.transcriber_popup
   ```
2. **Executando o daemon de atalho global (Hotkey Daemon):**
   ```sh
   uv run python -m src.hotkey_daemon
   ```
3. **Gravação:** Pressione o atalho global `Ctrl+Shift+Espaço` para exibir a popup e começar a gravar.
4. **Transcrição:** A transcrição aparecerá em tempo real no visor de texto da popup.
5. **Reescrita com IA:** Clique em **✨ Reescrever** para acionar o modelo de linguagem local Qwen 1.5B (via Llama-cpp) e purificar sua transcrição bruta.
6. **Copiar:** Pressione o botão **📋 Copiar** ou o atalho `Ctrl+Shift+C` para enviar a versão refinada diretamente para a área de transferência.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

<!-- CONTRIBUINDO -->

## Contribuindo

As contribuições são o que tornam a comunidade open source um lugar tão incrível para aprender, inspirar e criar. Qualquer contribuição que você fizer será **muito apreciada**.

Se você tiver alguma sugestão que tornaria isso melhor, por favor faça o fork do repositório e crie um pull request. Você também pode simplesmente abrir uma issue com a tag "enhancement".
Não se esqueça de dar uma estrela ao projeto! Obrigado novamente!

1. Faça o Fork do Projeto
2. Crie a sua Branch de Funcionalidade (`git checkout -b feature/FuncionalidadeIncrivel`)
3. Commit suas Mudanças (`git commit -m 'Adicione alguma FuncionalidadeIncrivel'`)
4. Faça o Push para a Branch (`git push origin feature/FuncionalidadeIncrivel`)
5. Abra um Pull Request

### Principais contribuidores:

<a href="https://github.com/alissonpef/whisper_transcriber/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=alissonpef/whisper_transcriber" alt="imagem contrib.rocks" />
</a>

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

<!-- LICENÇA -->

## Licença

Distribuído sob a Licença MIT. Veja `LICENSE` para mais informações.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

<!-- CONTATO -->

## Contato

Alisson Pereira Ferreira - alissonpef@gmail.com - [LinkedIn](https://www.linkedin.com/in/alisson-pereira-ferreira/)

Link do Projeto: [https://github.com/alissonpef/whisper_transcriber](https://github.com/alissonpef/whisper_transcriber)

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

Made with ❤️ by **Alisson Pereira**.

<!-- MARKDOWN LINKS & IMAGES -->
[contributors-shield]: https://img.shields.io/github/contributors/alissonpef/whisper_transcriber.svg?style=for-the-badge
[contributors-url]: https://github.com/alissonpef/whisper_transcriber/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/alissonpef/whisper_transcriber.svg?style=for-the-badge
[forks-url]: https://github.com/alissonpef/whisper_transcriber/network/members
[stars-shield]: https://img.shields.io/github/stars/alissonpef/whisper_transcriber.svg?style=for-the-badge
[stars-url]: https://github.com/alissonpef/whisper_transcriber/stargazers
[issues-shield]: https://img.shields.io/github/issues/alissonpef/whisper_transcriber.svg?style=for-the-badge
[issues-url]: https://github.com/alissonpef/whisper_transcriber/issues
[license-shield]: https://img.shields.io/github/license/alissonpef/whisper_transcriber.svg?style=for-the-badge
[license-url]: https://github.com/alissonpef/whisper_transcriber/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://www.linkedin.com/in/alisson-pereira-ferreira/
[product-screenshot]: assets/image.png

[Python-shield]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[Tkinter-shield]: https://img.shields.io/badge/Tkinter-GUI-orange?style=for-the-badge
[Tkinter-url]: https://docs.python.org/3/library/tkinter.html
[Whisper-shield]: https://img.shields.io/badge/Faster--Whisper-OpenAI-blue?style=for-the-badge
[Whisper-url]: https://github.com/SYSTRAN/faster-whisper
[Llama-shield]: https://img.shields.io/badge/Llama--CPP-AI-green?style=for-the-badge
[Llama-url]: https://github.com/abetlen/llama-cpp-python
[Sounddevice-shield]: https://img.shields.io/badge/Sounddevice-Audio-red?style=for-the-badge
[Sounddevice-url]: https://python-sounddevice.readthedocs.io/
[NumPy-shield]: https://img.shields.io/badge/NumPy-013243?style=for-the-badge&logo=numpy&logoColor=white
[NumPy-url]: https://numpy.org/