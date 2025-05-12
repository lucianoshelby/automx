import requests
import pickle
import os
import logging # É uma boa prática usar logging em vez de print para mensagens
from automacoes.cos.users_cos import recuperar_login # Importa a função de recuperação de login do módulo users_cos
# --- Configuração Inicial ---
# Configurar logging básico
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# URLs do sistema COS (mantidas do original)
URL_LOGIN_ENDPOINT = "http://192.168.25.131:8080/COS_CSO/LoginOut" # Endpoint para a ação de login
URL_TESTE = "http://192.168.25.131:8080/COS_CSO/Principal.jsp"  # Página autenticada para teste
URL_REFERER_LOGIN = "http://192.168.25.131:8080/COS_CSO/Entrar.jsp" # Referer para a página de login

# Diretório base para armazenar cookies de usuários
BASE_COOKIES_DIR = r"C:\Users\Gestão MX\Documents\AutoMX\login_do_cos\user_cookies" # Ajuste se necessário

# Cabeçalhos (mantidos do original, podem precisar de ajuste se variarem)
HEADERS = {
    "Host": "192.168.25.131:8080",
    "Connection": "keep-alive",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": URL_REFERER_LOGIN, # Usar a variável para consistência
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8"
}

# --- Funções Auxiliares ---

def get_cookies_path(nome_usuario):
    """Gera o caminho completo para o arquivo de cookies de um usuário específico."""
    # Sanitiza o nome do usuário para evitar problemas com caracteres inválidos em nomes de pasta/arquivo
    nome_sanitizado = "".join(c for c in nome_usuario if c.isalnum() or c in ('_', '-')).rstrip()
    if not nome_sanitizado:
        # Caso o nome resulte em vazio após sanitização
        raise ValueError("Nome de usuário inválido ou resulta em vazio após sanitização.")
    return os.path.join(BASE_COOKIES_DIR, nome_sanitizado, "cookies.pkl")

def salvar_cookies(session, nome_usuario):
    """Salva os cookies da sessão para um usuário específico."""
    cookies_path = get_cookies_path(nome_usuario)
    try:
        # Cria o diretório do usuário se não existir
        os.makedirs(os.path.dirname(cookies_path), exist_ok=True)
        with open(cookies_path, "wb") as f:
            pickle.dump(session.cookies, f)
        logging.info(f"🍪 Cookies salvos para o usuário '{nome_usuario}' em {cookies_path}")
    except Exception as e:
        logging.error(f"❌ Erro ao salvar cookies para '{nome_usuario}': {e}")

def carregar_cookies(session, nome_usuario):
    """Tenta carregar cookies salvos para um usuário específico."""
    cookies_path = get_cookies_path(nome_usuario)
    if os.path.exists(cookies_path):
        try:
            with open(cookies_path, "rb") as f:
                cookies = pickle.load(f)
                session.cookies.update(cookies)
            logging.info(f"🔄 Cookies carregados para o usuário '{nome_usuario}'.")
            return True # Indica sucesso no carregamento
        except Exception as e:
            logging.error(f"❌ Erro ao carregar cookies para '{nome_usuario}' de {cookies_path}: {e}")
            # Opcional: remover arquivo corrompido?
            # try:
            #     os.remove(cookies_path)
            #     logging.warning(f"Arquivo de cookie corrompido removido: {cookies_path}")
            # except OSError as oe:
            #     logging.error(f"Erro ao tentar remover cookie corrompido: {oe}")
            return False # Indica falha no carregamento
    else:
        logging.info(f"🍪 Arquivo de cookies não encontrado para '{nome_usuario}' em {cookies_path}.")
        return False # Indica que não há cookies para carregar

# --- Funções Principais Refatoradas ---

def testar_sessao(session):
    """Verifica se a sessão atual é válida acessando uma página protegida."""
    logging.info("🧪 Testando validade da sessão...")
    try:
        response_test = session.get(URL_TESTE, headers=HEADERS, allow_redirects=False, timeout=15) # Adiciona timeout
        # Verifica status e conteúdo esperado para uma sessão válida
        # Ajuste a condição conforme a resposta real da sua aplicação
        if response_test.status_code == 200 and "PaginaInicial.jsp" in response_test.text and "Acesse o site novamente" not in response_test.text:
            logging.info("✅ Sessão válida.")
            return True
        else:
            logging.warning(f"⚠️ Sessão inválida ou expirada. Status: {response_test.status_code}. Login necessário.")
            # logging.debug(f"Conteúdo da resposta do teste de sessão:\n{response_test.text[:500]}...") # Log para debug se necessário
            return False
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erro de rede ao testar a sessão: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Erro inesperado ao testar a sessão: {e}")
        return False

def fazer_login(nome_usuario):
    """Realiza um novo login no sistema usando credenciais dinâmicas."""
    logging.info(f"🔑 Iniciando processo de login para o usuário '{nome_usuario}'...")

    # 1. Recuperar credenciais dinamicamente
    credenciais = recuperar_login(nome_usuario)
    if not credenciais or 'user' not in credenciais or 'senha' not in credenciais:
        logging.error(f"❌ Falha ao recuperar credenciais válidas para o usuário '{nome_usuario}'. Abortando login.")
        return None # Retorna None para indicar falha no login

    # 2. Preparar parâmetros de login
    params_login = {
        "Acao": "Logar",
        "Usuario": credenciais['user'],
        "Senha": credenciais['senha']
    }

    # 3. Criar uma nova sessão para o login
    session = requests.Session()

    # 4. Enviar a requisição de login
    try:
        logging.info(f"🚀 Enviando requisição de login para {URL_LOGIN_ENDPOINT}...")
        response_login = session.get(URL_LOGIN_ENDPOINT, params=params_login, headers=HEADERS, allow_redirects=False, timeout=20) # Adiciona timeout

        logging.info(f"🔍 Resposta do servidor no login - Status: {response_login.status_code}")
        # logging.debug(f"Cookies recebidos após login: {session.cookies.get_dict()}") # Log para debug

        # 5. Verificar sucesso inicial (presença de cookie de sessão)
        if "JSESSIONID" in session.cookies.get_dict():
            logging.info("✅ Cookie de sessão (JSESSIONID) recebido.")

            # 6. Testar imediatamente se o login funcionou (opcional, mas recomendado)
            if testar_sessao(session):
                logging.info(f"✅ Login bem-sucedido para '{nome_usuario}'.")
                # 7. Salvar cookies após login bem-sucedido
                salvar_cookies(session, nome_usuario)
                return session # Retorna a sessão ativa
            else:
                logging.error(f"❌ Login parece ter falhado para '{nome_usuario}' (sessão não validada após tentativa).")
                return None
        else:
            logging.error("❌ Nenhum cookie de sessão (JSESSIONID) foi recebido. Login falhou.")
            # logging.debug(f"Conteúdo da resposta do login:\n{response_login.text[:500]}...") # Log para debug se necessário
            return None

    except requests.exceptions.Timeout:
        logging.error(f"❌ Timeout ao tentar fazer login para '{nome_usuario}'.")
        return None
    except requests.exceptions.RequestException as e:
        logging.error(f"❌ Erro de rede durante o login para '{nome_usuario}': {e}")
        return None
    except Exception as e:
        logging.error(f"❌ Erro inesperado durante o login para '{nome_usuario}': {e}")
        return None

def carregar_sessao(nome_usuario):
    """
    Função principal. Tenta carregar e validar uma sessão existente para o usuário.
    Se não for possível, realiza um novo login.
    Retorna um objeto 'requests.Session' válido ou None em caso de falha.
    """
    logging.info(f"----- Iniciando carregamento de sessão para: {nome_usuario} -----")
    session = requests.Session()

    # 1. Tentar carregar cookies existentes
    if carregar_cookies(session, nome_usuario):
        # 2. Se carregou, testar se a sessão ainda é válida
        if testar_sessao(session):
            logging.info(f"✅ Sessão carregada e validada com sucesso para '{nome_usuario}'.")
            return session
        else:
            logging.warning(f"⚠️ Cookies carregados para '{nome_usuario}', mas a sessão está inválida/expirada. Tentando novo login...")
            # Prossegue para fazer login
    else:
        logging.info(f"ⓘ Não foi possível carregar cookies válidos para '{nome_usuario}'. Tentando novo login...")
        # Prossegue para fazer login

    # 3. Se não carregou cookies ou se a sessão carregada era inválida, fazer novo login
    nova_session = fazer_login(nome_usuario)

    if nova_session:
        logging.info(f"✅ Nova sessão criada com sucesso para '{nome_usuario}' após login.")
        return nova_session
    else:
        logging.error(f"❌ Falha crítica: Não foi possível carregar ou criar uma sessão válida para '{nome_usuario}'.")
        return None

# --- Exemplo de Uso ---
if __name__ == "__main__":
    # Exemplo: Tentar carregar/criar sessão para dois usuários diferentes
    usuario1 = "Luciano Oliveira" # Usuário do exemplo original

    logging.info(f"\n--- Testando para usuário: {usuario1} ---")
    sessao_usuario1 = carregar_sessao(usuario1)
    if sessao_usuario1:
        logging.info(f"Operação concluída para {usuario1}. Sessão pronta para uso.")
        # Aqui você usaria a 'sessao_usuario1' para fazer outras requisições
        # Exemplo: response = sessao_usuario1.get("http://...")
    else:
        logging.error(f"Não foi possível obter uma sessão para {usuario1}.")

    logging.info("\nVerifique as pastas em:")
    logging.info(f"{BASE_COOKIES_DIR}\\{usuario1}")