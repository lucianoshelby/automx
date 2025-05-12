from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import json
import os
import time
import random
from datetime import datetime, timezone

COOKIES_PATH = "cookies.json"
COOKIES_TEMP_PATH = "cookies_temp.json"
def configurar_driver():
    """Configura e retorna o WebDriver do Selenium, tentando restaurar a conexão se possível."""
    
    chrome_options = Options()
    chrome_options.add_argument("user-data-dir=C:/Users/IMEI/AppData/Local/Google/Chrome/User Data")
    chrome_options.add_argument("profile-directory=Default")
    chrome_options.add_argument("--disable-sync")

    # 🟢 Tentar conectar ao navegador já aberto
    try:
        chrome_options.add_experimental_option("debuggerAddress", "localhost:9222")
        driver = webdriver.Chrome(options=chrome_options)
        print("✅ Conectado ao navegador já aberto.")
        return driver

    except Exception as e:
        print(f"⚠️ Não foi possível conectar ao navegador já aberto: {e}")
        print("🔄 Iniciando um novo navegador...")

        # 🟢 Se a conexão falhar, iniciar um novo navegador com depuração remota
        chrome_options.add_argument("--remote-debugging-port=9222")
        driver = webdriver.Chrome(options=chrome_options)
        
        print("✅ Novo navegador iniciado com suporte a reconexão.")
        return driver

"""def configurar_driver():
    ""Cria e retorna um WebDriver do Selenium em uma instância separada, compartilhando cookies.""

    chrome_options = Options()
    
    # 🔹 Criar um perfil TEMPORÁRIO para cada processo (evita conflito entre instâncias)
    profile_id = random.randint(1000, 9999)
    profile_path = f"C:/selenium-profile/temp-{profile_id}"
    chrome_options.add_argument(f"user-data-dir={profile_path}")

    chrome_options.add_argument("profile-directory=Default")
    chrome_options.add_argument("--disable-sync")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
        print(f"✅ Nova instância do Chrome criada com perfil temp-{profile_id}")

        # 🔹 Carregar os cookies imediatamente após abrir o navegador
        carregar_cookies(driver)

        return driver
    except Exception as e:
        print(f"❌ Erro ao iniciar o navegador: {e}")
        return None"""

def salvar_cookies(driver, caminho_arquivo=COOKIES_PATH):
    """Salva os cookies da sessão atual em um arquivo JSON."""
    try:
        cookies = driver.get_cookies()
        with open(caminho_arquivo, "w") as file:
            json.dump(cookies, file, indent=4)  # Salva os cookies formatados
        print("✅ Cookies salvos! Conteúdo do arquivo:")
        print(json.dumps(cookies, indent=4))  # Imprime os cookies no console
    except Exception as e:
        print(f"⚠️ Erro ao salvar cookies: {e}")

def carregar_cookies(driver, caminho_arquivo=COOKIES_PATH):
    """Carrega os cookies salvos no navegador Selenium."""
    if not os.path.exists(caminho_arquivo):
        print("⚠️ Nenhum cookie encontrado. O usuário pode precisar fazer login manualmente.")
        return

    try:
        with open(caminho_arquivo, "r") as file:
            cookies = json.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
        print("✅ Cookies carregados com sucesso!")
    except Exception as e:
        print(f"⚠️ Erro ao carregar cookies: {e}")


def imprimir_expiracao_cookies(caminho_arquivo):
    """
    Lê um arquivo JSON contendo uma lista de cookies e imprime
    o nome e a informação de expiração de cada um.
    """
    print(f"--- Lendo informações de expiração do arquivo: {os.path.abspath(caminho_arquivo)} ---")

    # 1. Verifica se o arquivo existe
    if not os.path.exists(caminho_arquivo):
        print(f"\n❌ ERRO: Arquivo não encontrado em '{caminho_arquivo}'.")
        print("      Verifique o caminho ou execute a captura de cookies primeiro.")
        return

    # 2. Tenta ler e decodificar o JSON
    try:
        with open(caminho_arquivo, "r", encoding='utf-8') as f:
            cookies_list = json.load(f)

        # Valida se o conteúdo é uma lista
        if not isinstance(cookies_list, list):
             print(f"\n❌ ERRO: O conteúdo de '{caminho_arquivo}' não é uma lista JSON válida.")
             return

    except json.JSONDecodeError as e:
        print(f"\n❌ ERRO: Falha ao decodificar JSON do arquivo '{caminho_arquivo}'. Erro: {e}")
        return
    except Exception as e:
        print(f"\n❌ ERRO: Ocorreu um erro inesperado ao ler o arquivo '{caminho_arquivo}'. Erro: {e}")
        return

    # 3. Processa e imprime cada cookie
    if not cookies_list:
        print("\nℹ️ O arquivo de cookies está vazio.")
        return

    print(f"\nTotal de cookies encontrados: {len(cookies_list)}")
    print("-" * 60)

    for cookie_data in cookies_list:
        # Verifica se o item é um dicionário (robustez)
        if not isinstance(cookie_data, dict):
            print("Item ignorado: não é um formato de cookie esperado (dicionário).")
            continue

        # Pega nome e expiração (usando .get para evitar erros se a chave faltar)
        nome = cookie_data.get("name", "NOME_NAO_ENCONTRADO")
        expires_timestamp = cookie_data.get("expires", None)

        info_expiracao = ""
        if expires_timestamp is None:
            info_expiracao = "Expiração não especificada"
        # Valores 0 ou -1 geralmente indicam cookie de sessão no CDP
        elif expires_timestamp <= 0:
            info_expiracao = "🍪 Cookie de Sessão (expira ao fechar navegador)"
        else:
            # Tenta converter o timestamp (segundos desde Epoch) para data/hora local
            try:
                data_hora_expiracao = datetime.fromtimestamp(expires_timestamp)
                # Formata para exibição
                info_expiracao = f"🗓️  Expira em: {data_hora_expiracao.strftime('%d/%m/%Y %H:%M:%S')} (horário local)"
            except OverflowError:
                info_expiracao = f"⚠️ Timestamp de expiração inválido/muito grande: {expires_timestamp}"
            except Exception as e:
                 info_expiracao = f"⚠️ Erro ao converter timestamp {expires_timestamp}: {e}"

        # Imprime formatado
        # Ajusta o espaçamento para alinhar :<45 garante que o nome ocupe até 45 caracteres
        print(f"Nome: {nome:<45} | {info_expiracao}")

    print("-" * 60)
    print("--- Leitura de expiração concluída ---")


# --- Execução ---
if __name__ == "__main__":
    imprimir_expiracao_cookies(COOKIES_TEMP_PATH)
    # Se você executar dando dois cliques no arquivo .py no Windows,
    # descomente a linha abaixo para a janela não fechar imediatamente.
    # input("\nPressione Enter para sair...")