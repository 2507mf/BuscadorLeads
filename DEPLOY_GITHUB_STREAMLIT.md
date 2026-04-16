# 🚀 Deploy: GitHub + Streamlit Cloud

Siga esses passos UMA VEZ. Depois disso, para atualizar o app basta pedir mudanças para o Claude e rodar 3 comandos no terminal.

---

## PARTE 1 — Subir no GitHub

### 1. Abra o Terminal
- **Mac:** Cmd + Espaço → digite "Terminal" → Enter
- **Windows:** Win + R → `cmd` → Enter

### 2. Navegue até a pasta do projeto

```bash
cd ~/Downloads/BuscadorLeads
```

### 3. Crie um repositório no GitHub
1. Acesse https://github.com/new
2. Nome do repositório: `buscador-leads` (ou qualquer nome)
3. Deixe como **Private** (recomendado — seus leads ficam privados)
4. **NÃO** marque "Add a README file"
5. Clique em **Create repository**
6. Copie a URL do repositório (ex: `https://github.com/seu-usuario/buscador-leads.git`)

### 4. Conecte e envie o código

Rode esses comandos no terminal (substitua pela URL do seu repositório):

```bash
# Adiciona o GitHub como destino
git remote add origin https://github.com/SEU-USUARIO/buscador-leads.git

# Envia o código
git push -u origin master
```

> Se pedir usuário e senha, use seu **usuário GitHub** e um **Personal Access Token** como senha:
> → GitHub → Settings → Developer Settings → Personal access tokens → Tokens (classic) → Generate new token
> → Marque a opção "repo" e gere o token. Use ele como senha.

✅ Pronto — seu código está no GitHub!

---

## PARTE 2 — Deploy no Streamlit Cloud (grátis)

### 1. Acesse https://share.streamlit.io

### 2. Clique em **"Sign in with GitHub"**

### 3. Clique em **"New app"**

### 4. Preencha:
| Campo | Valor |
|-------|-------|
| Repository | `seu-usuario/buscador-leads` |
| Branch | `master` |
| Main file path | `app.py` |

### 5. Clique em **Deploy!**

O Streamlit vai instalar as dependências e publicar. Em 2-3 minutos você terá uma URL tipo:
`https://seu-usuario-buscador-leads-app-xyz123.streamlit.app`

✅ App no ar! Compartilhe com sua equipe.

---

## PARTE 3 — Fazendo atualizações depois

Quando quiser mudar algo no app:

### 1. Peça a mudança para o Claude no Cowork
> Ex: "Claude, adiciona um campo de filtro por número mínimo de funcionários" ou "Muda a cor do botão para verde"

### 2. Claude vai editar o `app.py` automaticamente

### 3. Você roda 3 comandos no terminal:

```bash
cd ~/Downloads/BuscadorLeads
git add .
git commit -m "Atualização: descrição do que mudou"
git push
```

✅ O Streamlit Cloud detecta o push e atualiza o app automaticamente em ~1 minuto!

---

## Dicas úteis

**Ver o app localmente antes de subir:**
```bash
cd ~/Downloads/BuscadorLeads
pip install -r requirements.txt
streamlit run app.py
```
Isso abre o app no seu navegador em http://localhost:8501

**Variáveis de ambiente no Streamlit Cloud (para não digitar a API Key toda vez):**
1. No painel do Streamlit Cloud → seu app → Settings → Secrets
2. Adicione:
```toml
GOOGLE_MAPS_API_KEY = "sua_chave_aqui"
```
3. No código, acesse com `st.secrets["GOOGLE_MAPS_API_KEY"]`
   (Claude pode fazer isso por você se quiser!)

**Credenciais do Google Sheets no Streamlit Cloud:**
1. Em Secrets, adicione o conteúdo do seu JSON assim:
```toml
[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
# (cole o JSON inteiro aqui)
```

---

## Resumo do fluxo

```
Você pede mudança no Cowork
         ↓
   Claude edita o código
         ↓
 Você roda: git add . && git commit -m "..." && git push
         ↓
  Streamlit Cloud atualiza automaticamente
         ↓
     App atualizado! ✅
```
