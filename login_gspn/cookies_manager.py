import requests
from requests.cookies import RequestsCookieJar
import urllib.parse # Para decodificar o menuUrl se necessário (boa prática)
import json
import os



def testar_cookies_samsung(lista_cookies_completa: list) -> bool:
    """
    Testa a validade de um conjunto de cookies para o Samsung CS Portal.

    Args:
        lista_cookies_completa: Uma lista de dicionários, onde cada dicionário
                                representa um cookie com chaves como 'name',
                                'value', 'domain', etc.

    Returns:
        True se os cookies forem válidos, False caso contrário.
    """
    target_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # 1. Filtrar os cookies relevantes pelo domínio
    dominios_permitidos = ("samsungcsportal.com", "gspn6.samsungcsportal.com")
    cookies_filtrados = [
        cookie for cookie in lista_cookies_completa
        if cookie.get("domain") and any(cookie["domain"].endswith(d) for d in dominios_permitidos)
    ]

    if not cookies_filtrados:
        print("Nenhum cookie encontrado para os domínios relevantes.")
        return False

    # 2. Encontrar o cookie 'gspn_saveid' para extrair o aclId
    acl_id = None
    for cookie in cookies_filtrados:
        if cookie.get("name") == "gspn_saveid":
            acl_id = cookie.get("value")
            break

    if not acl_id:
        print("Cookie 'gspn_saveid' não encontrado nos cookies filtrados.")
        return False
    print(f"ACL ID encontrado: {acl_id}") # Para depuração

    # 3. Preparar o payload (data)
    # O menuUrl no exemplo está parcialmente URL encoded, vamos usar como está
    # Se fosse necessário montar dinamicamente, usaríamos urllib.parse.urlencode
    payload = {
        "cmd": "AuthCommandListCmd",
        "menuUrl": "/svctracking/monitor/SVCJobSummarybyStatus.jsp", # Valor do exemplo
        "subRegionCd": "LA", # Valor do exemplo
        "aclId": acl_id
    }

    # 4. Preparar os headers (baseados no exemplo)
    headers = {
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Connection': 'keep-alive',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/monitor/SVCJobSummarybyStatus.jsp?search_status=&searchContent=&menuBlock=&menuUrl=&naviDirValue=', # Do exemplo
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36', # Do exemplo
        'X-Prototype-Version': '1.7.2', # Do exemplo
        'X-Requested-With': 'XMLHttpRequest',
        'sec-ch-ua': '"Google Chrome";v="135", "Not-A.Brand";v="8", "Chromium";v="135"', # Do exemplo
        'sec-ch-ua-mobile': '?0', # Do exemplo
        'sec-ch-ua-platform': '"Windows"', # Do exemplo
        # Host e Content-Length são gerenciados pelo requests
        # Cookie será gerenciado pelo cookie_jar
    }

    # 5. Preparar o RequestsCookieJar
    cookie_jar = RequestsCookieJar()
    for cookie_dict in cookies_filtrados:
        # Adaptação mínima para o set_cookie do RequestsCookieJar
        cookie_jar.set(
            name=cookie_dict.get("name"),
            value=cookie_dict.get("value"),
            domain=cookie_dict.get("domain"),
            path=cookie_dict.get("path", "/") # Default path to '/' if missing
        )

    # 6. Fazer a requisição
    try:
        #print(f"Enviando POST para: {target_url}") # Para depuração
        response = requests.post(
            target_url,
            headers=headers,
            data=payload,
            cookies=cookie_jar,
            timeout=15,
            verify=False  # Definir um timeout razoável (em segundos)
        )
        response.raise_for_status() # Levanta exceção para status HTTP 4xx/5xx

        # 7. Validar a resposta
        response_text = response.text
        #print(f"Resposta recebida (status {response.status_code}):\n{response_text[:200]}...") # Mostrar início da resposta

        # String de sucesso esperada (parte relevante)
        success_string = '"success":true'
        # String de falha (manutenção)
        maintenance_string = "window.top.location.href = 'https://gspn6.samsungcsportal.com/maintenance.jsp';"

        if success_string in response_text:
            print("Validação: Sucesso!")
            return True
        elif maintenance_string in response_text:
            print("Validação: Falha (Página de Manutenção)")
            return False
        else:
            print("Validação: Falha (Resposta inesperada)")
            return False

    except requests.exceptions.Timeout:
        print(f"Erro: Timeout ao tentar conectar com {target_url}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return False



def carregar_cookies_do_json(nome_arquivo: str = "C:\\Users\\Gestão MX\\Documents\\AutoMX\\cookies_temp.json") -> list | dict | None:
    """
    Carrega os cookies de um arquivo JSON.

    Args:
        nome_arquivo: O nome do arquivo JSON a ser carregado.
                      Padrão é "cookies_temp.json".

    Returns:
        Uma lista ou dicionário contendo os dados do JSON,
        ou None se o arquivo não for encontrado ou houver erro no JSON.
    """
    try:
        # Abre o arquivo no modo de leitura ('r') com codificação UTF-8 (comum para JSON)
        with open(nome_arquivo, 'r', encoding='utf-8') as f:
            # Carrega o conteúdo do arquivo JSON para uma variável Python
            dados_cookies = json.load(f)
            # json.load() retorna uma lista se o JSON for um array [...]
            # ou um dicionário se for um objeto {...}
            return dados_cookies
    except FileNotFoundError:
        print(f"Erro: Arquivo '{nome_arquivo}' não encontrado.")
        return None
    except json.JSONDecodeError as e:
        print(f"Erro: O arquivo '{nome_arquivo}' não contém um JSON válido.")
        print(f"Detalhe do erro: {e}")
        return None
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao ler o arquivo: {e}")
        return None

def validar_e_salvar_cookies(lista_cookies: list, pasta_destino: str = "login_gspn\\cookies") -> bool:
    """
    Valida os cookies usando testar_cookies_samsung e, se válidos,
    salva-os em um arquivo JSON nomeado com o ID do usuário.

    Args:
        lista_cookies: A lista de dicionários de cookies recebida.
        pasta_destino: O nome da subpasta onde os cookies serão salvos.
                       Padrão é "cookies".

    Returns:
        True se os cookies foram validados e salvos com sucesso, False caso contrário.
    """
    #print(f'Lista de Cookies recebida: {lista_cookies}')
    if not lista_cookies:
        print("Lista de cookies está vazia. Nada para validar ou salvar.")
        return False

    print("\n--- Iniciando validação e salvamento de cookies ---")

    # 1. Extrair o ID do usuário (necessário para o nome do arquivo)
    user_id = None
    for cookie in lista_cookies:
        if cookie.get("name") == "gspn_saveid":
            user_id = cookie.get("value")
            break

    if not user_id:
        print("Erro: Não foi possível encontrar o cookie 'gspn_saveid' para determinar o nome do arquivo.")
        return False

    print(f"ID de usuário encontrado para nome do arquivo: {user_id}")

    # 2. Testar a validade dos cookies
    #print("Testando a validade dos cookies...")
    # Supõe que testar_cookies_samsung está definida e acessível
    sao_validos = testar_cookies_samsung(lista_cookies)

    if not sao_validos:
        print("Validação falhou. Os cookies não serão salvos.")
        return False

    print("Cookies validados com sucesso!")

    # 3. Criar o diretório de destino se não existir
    try:
        # os.makedirs cria o diretório e pais necessários.
        # exist_ok=True evita erro se o diretório já existir.
        os.makedirs(pasta_destino, exist_ok=True)
        print(f"Diretório '{pasta_destino}' verificado/criado.")
    except OSError as e:
        print(f"Erro ao criar o diretório '{pasta_destino}': {e}")
        return False

    # 4. Definir o caminho completo do arquivo
    nome_arquivo = f"{user_id}.json"
    caminho_arquivo = os.path.join(pasta_destino, nome_arquivo) # Forma segura de juntar caminhos

    # 5. Salvar a lista ORIGINAL de cookies no arquivo JSON
    #print(f"Salvando cookies em '{caminho_arquivo}'...")
    try:
        with open(caminho_arquivo, 'w', encoding='utf-8') as f:
            # Salva a lista completa de cookies recebida
            # indent=4 para formatar o JSON de forma legível
            json.dump(lista_cookies, f, ensure_ascii=False, indent=4)
        #print("Cookies salvos com sucesso!")
        return True
    except IOError as e:
        print(f"Erro ao salvar o arquivo JSON '{caminho_arquivo}': {e}")
        return False
    except Exception as e:
        print(f"Ocorreu um erro inesperado ao salvar o arquivo: {e}")
        return False

def verificar_e_limpar_cookies_salvos(pasta_cookies: str = "login_gspn\\cookies") -> list:
    """
    Verifica todos os arquivos .json na pasta de cookies, testa a validade
    de cada um, deleta os inválidos e retorna uma lista dos IDs de usuário válidos.

    Args:
        pasta_cookies: O caminho para a pasta contendo os arquivos .json de cookies.
                       Padrão é "cookies".

    Returns:
        Uma lista de strings contendo os IDs de usuário (nomes dos arquivos sem .json)
        cujos cookies foram validados com sucesso.
    """
    #print(f"\n--- Iniciando verificação e limpeza na pasta '{pasta_cookies}' ---")
    usuarios_validos = []

    # Verifica se a pasta existe
    if not os.path.isdir(pasta_cookies):
        print(f"A pasta '{pasta_cookies}' não existe. Nenhum cookie para verificar.")
        return usuarios_validos

    # Lista todos os arquivos na pasta
    try:
        nomes_arquivos = os.listdir(pasta_cookies)
    except OSError as e:
        print(f"Erro ao listar arquivos na pasta '{pasta_cookies}': {e}")
        return usuarios_validos # Retorna lista vazia em caso de erro

    for nome_arquivo in nomes_arquivos:
        # Considera apenas arquivos .json
        if nome_arquivo.endswith(".json") and os.path.isfile(os.path.join(pasta_cookies, nome_arquivo)):
            caminho_completo = os.path.join(pasta_cookies, nome_arquivo)
            user_id = nome_arquivo[:-5] # Remove '.json' do final para obter o ID
            #print(f"\nVerificando arquivo: {nome_arquivo} (ID: {user_id})")

            lista_cookies = None
            erro_leitura = False
            sao_validos = False

            # 1. Tentar carregar os cookies do arquivo
            try:
                with open(caminho_completo, 'r', encoding='utf-8') as f:
                    lista_cookies = json.load(f)
                if not isinstance(lista_cookies, list):
                     print(f"Erro: Conteúdo de '{nome_arquivo}' não é uma lista JSON válida.")
                     erro_leitura = True # Trata como erro para possível exclusão
                #else:
                    #print(f"Cookies carregados de '{nome_arquivo}'.")

            except json.JSONDecodeError as e:
                print(f"Erro ao decodificar JSON em '{nome_arquivo}': {e}")
                erro_leitura = True
            except IOError as e:
                print(f"Erro de I/O ao ler '{nome_arquivo}': {e}")
                erro_leitura = True
            except Exception as e:
                 print(f"Erro inesperado ao ler '{nome_arquivo}': {e}")
                 erro_leitura = True # Trata como erro genérico

            # 2. Se carregou com sucesso, testar a validade
            if not erro_leitura and lista_cookies is not None:
                try:
                    # Chama a função de teste existente
                    sao_validos = testar_cookies_samsung(lista_cookies)
                except Exception as e:
                    print(f"Erro inesperado ao chamar testar_cookies_samsung para '{nome_arquivo}': {e}")
                    # Considera inválido se o teste falhar com erro
                    sao_validos = False

            # 3. Tomar ação: manter ID na lista ou deletar arquivo
            if sao_validos:
                #print(f"Cookies para ID '{user_id}' são VÁLIDOS.")
                usuarios_validos.append(user_id)
            else:
                if erro_leitura:
                     print(f"Arquivo '{nome_arquivo}' com erro ou inválido. Deletando...")
                else:
                     print(f"Cookies para ID '{user_id}' são INVÁLIDOS. Deletando arquivo...")

                # Deletar o arquivo inválido ou com erro
                try:
                    os.remove(caminho_completo)
                    print(f"Arquivo '{nome_arquivo}' deletado.")
                except OSError as e:
                    print(f"Erro ao tentar deletar '{nome_arquivo}': {e}")
                    # Continua para o próximo arquivo mesmo se a deleção falhar

    #print("\n--- Verificação e limpeza concluídas ---")
    if usuarios_validos:
        #print(f"IDs de usuário com cookies válidos: {usuarios_validos}")
        print(f'usuarios_validos: {usuarios_validos}')
    else:
        print("Nenhum cookie válido encontrado.")

    return usuarios_validos
def obter_cookies_validos_recentes(pasta_cookies: str = "login_gspn\\cookies") -> list | None:
    """
    Encontra o conjunto de cookies válidos mais recente na pasta especificada.

    Verifica os arquivos .json na pasta, ordenados por data de modificação (mais
    recentes primeiro). Testa a validade de cada um e retorna o primeiro
    conjunto válido encontrado. Arquivos inválidos encontrados durante a busca
    são deletados.

    Args:
        pasta_cookies: O caminho para a pasta contendo os arquivos .json de cookies.
                       Padrão é "cookies".

    Returns:
        Uma lista de dicionários de cookies válidos do arquivo mais recente,
        ou None se nenhum cookie válido for encontrado.
    """
    #print(f"\n--- Buscando cookies válidos mais recentes em '{pasta_cookies}' ---")

    if not os.path.isdir(pasta_cookies):
        print(f"A pasta '{pasta_cookies}' não existe.")
        return None

    arquivos_json = []
    try:
        # Lista todos os arquivos .json e suas datas de modificação
        for nome_arquivo in os.listdir(pasta_cookies):
            caminho_completo = os.path.join(pasta_cookies, nome_arquivo)
            if nome_arquivo.endswith(".json") and os.path.isfile(caminho_completo):
                try:
                    # Obtém o timestamp da última modificação
                    mod_time = os.path.getmtime(caminho_completo)
                    arquivos_json.append((mod_time, caminho_completo, nome_arquivo))
                except OSError as e:
                    print(f"Aviso: Não foi possível obter informações de '{nome_arquivo}': {e}")

        # Ordena pela data de modificação, decrescente (mais recente primeiro)
        arquivos_json.sort(key=lambda item: item[0], reverse=True)

    except OSError as e:
        print(f"Erro ao listar arquivos na pasta '{pasta_cookies}': {e}")
        return None

    if not arquivos_json:
        print("Nenhum arquivo .json encontrado na pasta.")
        return None

    #print(f"Arquivos .json encontrados e ordenados por data: {[a[2] for a in arquivos_json]}")

    # Itera sobre os arquivos, do mais recente para o mais antigo
    for mod_time, caminho_completo, nome_arquivo in arquivos_json:
        #print(f"\nTestando arquivo (mais recente): {nome_arquivo}")
        lista_cookies = None
        erro_leitura = False
        sao_validos = False

        # 1. Tentar carregar
        try:
            with open(caminho_completo, 'r', encoding='utf-8') as f:
                lista_cookies = json.load(f)
            if not isinstance(lista_cookies, list):
                #print(f"Erro: Conteúdo de '{nome_arquivo}' não é uma lista JSON.")
                erro_leitura = True
            #else:
                 #print(f"Cookies carregados de '{nome_arquivo}'.")

        except json.JSONDecodeError as e:
            print(f"Erro ao decodificar JSON em '{nome_arquivo}': {e}")
            erro_leitura = True
        except IOError as e:
            print(f"Erro de I/O ao ler '{nome_arquivo}': {e}")
            erro_leitura = True
        except Exception as e:
            print(f"Erro inesperado ao ler '{nome_arquivo}': {e}")
            erro_leitura = True # Trata como erro genérico

        # 2. Se carregou, testar validade
        if not erro_leitura and lista_cookies is not None:
            try:
                sao_validos = testar_cookies_samsung(lista_cookies) # Usa a função de teste
            except Exception as e:
                print(f"Erro inesperado ao chamar testar_cookies_samsung para '{nome_arquivo}': {e}")
                sao_validos = False # Considera inválido se teste der erro

        # 3. Avaliar resultado
        if sao_validos:
            #print(f"SUCESSO: Cookies de '{nome_arquivo}' são VÁLIDOS. Retornando este conjunto.")
            cookies = {cookie["name"]: cookie["value"] for cookie in lista_cookies}
            return cookies # Retorna a lista de cookies válidos
        else:
            # Se inválido ou erro na leitura, deleta o arquivo problemático
            if erro_leitura:
                print(f"Arquivo '{nome_arquivo}' com erro ou inválido. Deletando...")
            else: # Entra aqui se carregou mas testar_cookies_samsung retornou False
                 print(f"Cookies de '{nome_arquivo}' são INVÁLIDOS. Deletando arquivo...")

            try:
                os.remove(caminho_completo)
                print(f"Arquivo '{nome_arquivo}' deletado.")
            except OSError as e:
                print(f"Erro ao tentar deletar '{nome_arquivo}': {e}")
            # Continua o loop para testar o próximo arquivo mais recente

    # Se o loop terminar sem retornar, nenhum cookie válido foi encontrado
    print("Nenhum conjunto de cookies válido foi encontrado após verificar todos os arquivos.")
    return None

# --- Exemplo de Uso ---
if __name__ == "__main__":
    # Primeiro, talvez execute a limpeza para ter um estado conhecido (opcional)
    # verificar_e_limpar_cookies_salvos("cookies")
    cookies = carregar_cookies_do_json("cookies_temp.json")
    validar_e_salvar_cookies(cookies)
    # Agora, tenta obter o conjunto de cookies válido mais recente
    cookies_para_usar = obter_cookies_validos_recentes("login_gspn\\cookies")

    if cookies_para_usar:
        # Extrai o ID apenas para demonstração (não necessário para usar os cookies)
        user_id_demo = "desconhecido"
        for c in cookies_para_usar:
            if c.get("name") == "gspn_saveid":
                user_id_demo = c.get("value")
                break
        print(f"\nCookies válidos obtidos (do usuário: {user_id_demo}). Pronto para usar em requests.")
        # Aqui você usaria 'cookies_para_usar' em suas requisições
        # Exemplo:
        # cookie_jar_final = RequestsCookieJar()
        # for cookie_dict in cookies_para_usar:
        #     cookie_jar_final.set(...)
        # response = requests.get(url, cookies=cookie_jar_final)

    else:
        print("\nNão foi possível obter um conjunto de cookies válido.")
        # Aqui você precisaria de um fluxo para obter novos cookies (login)
