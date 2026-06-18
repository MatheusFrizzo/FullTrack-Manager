# FullTrack Manager — Guia de Setup na VM Linux

## Pré-requisitos

- Ubuntu 20.04+ / Debian 11+ / qualquer distro Linux
- Python 3.8+
- Acesso à internet para instalar dependências

---

## 1. Instalar dependências do sistema

```bash
# Atualizar pacotes
sudo apt update && sudo apt upgrade -y

# Python e pip
sudo apt install -y python3 python3-pip python3-venv

# Chromium e ChromeDriver (para o Selenium)
sudo apt install -y chromium-browser chromium-driver

# Verificar versões
python3 --version
chromedriver --version
chromium-browser --version
```

> **Nota:** Em alguns sistemas o pacote se chama `chromium` em vez de `chromium-browser`:
> ```bash
> sudo apt install -y chromium chromium-driver
> ```

---

## 2. Copiar o projeto para a VM

```bash
# Opção A: via SCP do Windows para a VM
scp -r "FullTrack - Linux" usuario@ip-da-vm:~/fulltrack-manager

# Opção B: git clone (se você colocar no GitHub)
git clone <url-do-repo> ~/fulltrack-manager

# Entrar na pasta
cd ~/fulltrack-manager
```

---

## 3. Criar ambiente virtual e instalar dependências Python

```bash
# Criar venv
python3 -m venv venv

# Ativar venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

---

## 4. Rodar a aplicação

```bash
# Com venv ativado
source venv/bin/activate
python3 app.py
```

Você verá:
```
============================================================
  FullTrack Manager rodando em http://0.0.0.0:5000
  Acesse pelo navegador: http://localhost:5000
============================================================
```

Abra o navegador e acesse: **http://localhost:5000**  
(ou **http://IP-DA-VM:5000** de outra máquina na rede)

---

## 5. Configurar as credenciais

1. Na interface web, clique em **Configurações**
2. Preencha **E-mail/Usuário** e **Senha** do FullTrack
3. Confirme a **URL** do FullTrack (já vem preenchida)
4. Clique em **Salvar Credenciais**

As credenciais ficam salvas no banco SQLite local (`fulltrack.db`).

---

## 6. Usar a aplicação

### Adicionar seriais
- Clique em **"+ Adicionar Seriais"** → cole os números (um por linha)
- Ou clique em **"Importar Planilha"** → faça upload do `.xlsx` / `.csv`  
  *(os seriais devem estar na coluna A)*

### Processar em lote
- Clique em **"▶ Processar Pendentes"** para rodar todos de uma vez
- O Selenium abre em segundo plano e vai processando um a um

### Bloquear manualmente
- Na tabela, clique no ícone 🔒 ao lado de qualquer serial
- O bloqueio inicia imediatamente para aquele serial

### Acompanhar em tempo real
- Vá na aba **Logs** para ver o processo ao vivo

---

## 7. Ajustar os Seletores CSS (IMPORTANTE)

O arquivo `automation.py` tem seletores genéricos que tentam funcionar,  
mas **podem precisar ser ajustados** para o seu site FullTrack.

Procure por `# ⚠️ AJUSTAR` no arquivo e substitua pelos seletores reais:

```bash
grep -n "AJUSTAR" automation.py
```

**Como encontrar o seletor:**
1. Abra o FullTrack no Chrome
2. Pressione `F12` → DevTools
3. Clique no ícone de seta e clique no elemento (campo de busca, botão, etc.)
4. Copie o atributo `id`, `class` ou o seletor CSS mostrado

---

## 8. Rodar como serviço (opcional — inicia automaticamente com o servidor)

```bash
# Criar arquivo de serviço
sudo nano /etc/systemd/system/fulltrack-manager.service
```

Cole este conteúdo (ajuste o caminho `WorkingDirectory` e `User`):

```ini
[Unit]
Description=FullTrack Manager Web App
After=network.target

[Service]
Type=simple
User=seu-usuario
WorkingDirectory=/home/seu-usuario/fulltrack-manager
ExecStart=/home/seu-usuario/fulltrack-manager/venv/bin/python3 app.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
# Ativar e iniciar
sudo systemctl daemon-reload
sudo systemctl enable fulltrack-manager
sudo systemctl start fulltrack-manager

# Verificar status
sudo systemctl status fulltrack-manager

# Ver logs do serviço
sudo journalctl -u fulltrack-manager -f
```

---

## 9. Abrir porta no firewall (se acessar de outra máquina)

```bash
sudo ufw allow 5000/tcp
sudo ufw reload
```

---

## Estrutura dos Arquivos

```
fulltrack-manager/
├── app.py              ← Backend Flask (API + servidor)
├── automation.py       ← Selenium (⚠️ ajuste os seletores aqui)
├── database.py         ← SQLite (banco de dados)
├── requirements.txt    ← Dependências Python
├── fulltrack.db        ← Banco SQLite (criado ao rodar)
└── static/
    ├── index.html      ← Interface web
    ├── style.css       ← Estilos
    └── app.js          ← Lógica frontend
```

---

## Troubleshooting

### Chrome não inicia
```bash
# Teste manual
chromium-browser --headless --no-sandbox --dump-dom https://google.com

# Se der erro de GPU:
chromium-browser --headless --no-sandbox --disable-gpu --dump-dom https://google.com
```

### Erro "chromedriver not found"
```bash
which chromedriver
# Se não retornar nada:
sudo apt install -y chromium-driver
# ou
sudo snap install chromium
```

### Porta 5000 já em uso
```bash
# Verificar o que está usando a porta
sudo lsof -i :5000

# Matar o processo
sudo kill -9 <PID>

# Ou mudar a porta no app.py (última linha):
# app.run(host="0.0.0.0", port=8080, ...)
```

### Ver logs da aplicação
```bash
# Se rodando direto no terminal: os logs aparecem no terminal
# Se como serviço systemd:
sudo journalctl -u fulltrack-manager -f
```
