import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
import json
from automacoes.vincular_os.dados_consumidor_gspn import coletar_dados_detalhados_consumidor
from automacoes.vincular_os.dados_produto_gspn import consultar_dados_produto, consultar_descricao_modelo, verificar_garantia
from login_gspn.cookies_manager import obter_cookies_validos_recentes
from automacoes.cos.coletar_dados_cos import coletar_dados_os
from automacoes.vincular_os.master_otp import get_master_otp
from bs4 import BeautifulSoup
import requests
import random
import string

def gerar_ascjob():
    """
    Gera um código alfanumérico aleatório de 10 dígitos em maiúsculas.
    
    Returns:
        str: Código alfanumérico de 10 caracteres (letras A-Z e números 0-9).
    """
    # Define os caracteres possíveis: letras maiúsculas (A-Z) e números (0-9)
    characters = string.ascii_uppercase + string.digits
    
    # Gera um código de 10 caracteres escolhendo aleatoriamente de characters
    code = ''.join(random.choice(characters) for _ in range(10))
    
    return code

def coletar_informacoes_completas(cookies, numero_os) -> dict | None:
    """
    Orquestra a chamada de várias funções para coletar todas as informações
    necessárias para uma Ordem de Serviço, combinando os resultados.

    Args:
        cpf: O CPF do cliente.
        identificador_produto: O IMEI ou Número de Série do produto.

    Returns:
        Um dicionário contendo todas as informações coletadas das várias
        consultas, ou None se uma etapa crítica falhar (como obter dados
        iniciais do cliente ou produto).
    """
    print(f"\n=== Iniciando Coleta de Informações para OS ===")

    try: 
        dados_os = coletar_dados_os(numero_os)
    except Exception as e:
        print(f"Erro ao coletar dados da OS: {e}")
        return None
    cpf = dados_os.get('cpf')
    identificador_produto = dados_os.get('IMEI') or dados_os.get('Serial')

    informacoes_completas = {}


    try:
        # Coletar o Master OTP
        master_otp = get_master_otp()

    except Exception as e:
        print(f"Erro ao obter Master OTP: {e}")
        return None
    informacoes_completas['MasterOTP'] = master_otp # Adiciona ao resultado final

    try:
        # Gerar um código ASCJOB aleatório
        ascjob = gerar_ascjob()
    except Exception as e:
        print(f"Erro ao gerar ASCJOB: {e}")
        return None
    informacoes_completas['ASCJOB'] = ascjob # Adiciona ao resultado final

    descricao_produto = {
        "Acessorios": dados_os.get('Acessorios'),
        "Defeito": dados_os.get('Defeito'),
        "CondicoesProduto": dados_os.get('CondicoesProduto'),
        "tipo_atendimento": dados_os.get('tipo_atendimento'),
        "imei_cos": dados_os.get('IMEI'),
    }
    
    informacoes_completas.update(descricao_produto) # Adiciona ao resultado final

    #cookies = obter_cookies_validos_recentes()

    try:
        zpo = obter_token_zpo(cookies)
    except Exception as e:
        print(f"Erro ao obter token ZPO: {e}")
        return False
    informacoes_completas['zpo'] = zpo # Adiciona ao resultado final
    consumer_code = None
    modelo_completo = None

    # --- Etapa 1: Consultar dados básicos do consumidor por CPF ---
    #print("\n--- Etapa 1: Consultando dados do consumidor por CPF ---")
    dados_complementares = coletar_dados_detalhados_consumidor(cookies, cpf)
    if not dados_complementares:
        print("ERRO CRÍTICO: Falha ao obter dados iniciais do consumidor pelo CPF. Abortando.")
        return None

    
    if dados_complementares:
        #print("Dados complementares obtidos.")
        # Atualiza, sobrescrevendo chaves iguais se houver (ex: CONSUMER)
        informacoes_completas.update(dados_complementares)
    else:
        print("Aviso: Falha ao obter dados complementares do consumidor. Prosseguindo com dados do CPF.")

    # --- Etapa 3: Consultar dados do produto por IMEI/Serial ---
    #print("\n--- Etapa 3: Consultando dados do produto ---")
    # Nota: consultar_dados_produto chama consultar_master_otp internamente
    dados_produto = consultar_dados_produto(cookies, identificador_produto)
    if not dados_produto:
        print("ERRO CRÍTICO: Falha ao obter dados do produto. Abortando.")
        return None

    # Verifica se o modelo foi retornado (necessário para próxima etapa)
    modelo_completo = dados_produto.get('modelo_completo')
    if not modelo_completo:
         print("ERRO CRÍTICO: Modelo do produto ('modelo_completo') não encontrado na resposta. Abortando.")
         return None

    #print(f"Dados do produto obtidos. Modelo: {modelo_completo}")
    informacoes_completas.update(dados_produto) # Adiciona ao resultado final

    # --- Etapa 4: Consultar descrição detalhada do modelo ---
    #print("\n--- Etapa 4: Consultando descrição do modelo ---")
    dados_modelo = consultar_descricao_modelo(cookies, modelo_completo)
    if dados_modelo:
        #print("Descrição do modelo obtida.")
        informacoes_completas.update(dados_modelo)
    else:
        print("Aviso: Falha ao obter descrição detalhada do modelo. Verificação de garantia pode falhar.")

    # --- Etapa 5: Verificar garantia ---
    #print("\n--- Etapa 5: Verificando garantia ---")
    # Checa se temos os dados necessários vindos das etapas anteriores
    chaves_garantia = ['modelo_completo', 'serial', 'local_svc_prod', 'imei_primario', 'buyer']
    dados_para_garantia = {k: informacoes_completas.get(k) for k in chaves_garantia}

    if all(dados_para_garantia.values()): # Verifica se todos os valores necessários existem
        #print("Dados necessários para garantia encontrados. Consultando...")
        dados_garantia = verificar_garantia(cookies, dados_para_garantia)
        if dados_garantia:
            print("Dados de garantia obtidos.")
            informacoes_completas.update(dados_garantia)
        else:
            print("Aviso: Falha na consulta de garantia.")
    else:
        campos_faltantes_garantia = [k for k, v in dados_para_garantia.items() if not v]
        print(f"Aviso: Verificação de garantia pulada. Campos necessários ausentes no dicionário final: {campos_faltantes_garantia}")

    # --- Finalização ---
    #print("\n=== Coleta de Informações Concluída ===")
    return informacoes_completas



def filtrar_dados_os(os_numero: str) -> dict | None:
    """
    Busca os dados de uma OS usando coletar_dados_os() e retorna
    um dicionário filtrado com informações específicas, usando as chaves
    exatas fornecidas.

    Args:
        os_numero: O número da Ordem de Serviço a ser consultada.

    Returns:
        Um dicionário contendo os dados filtrados ('tipo_atendimento', 'cpf',
        'IMEI', 'Acessorios', 'Defeito', 'CondicoesProduto', 'Serial')
        ou None se a OS não for encontrada ou ocorrer um erro.
    """
    #print(f"\n--- Filtrando dados para OS: {os_numero} ---")

    # 1. Chamar a função que coleta os dados completos
    dados_completos_os = coletar_dados_os(os_numero)

    # 2. Verificar se a coleta foi bem-sucedida
    if dados_completos_os is None:
        print(f"Erro: Não foi possível coletar os dados para a OS {os_numero}.")
        return None

    # 3. Extrair os dados usando as chaves EXATAS fornecidas
    # Usar .get() ainda é uma boa prática caso a função coletar_dados_os
    # possa, por algum motivo, retornar um dicionário sem uma dessas chaves.
    dados_filtrados = {
        "tipo_atendimento": dados_completos_os.get("tipo_atendimento"),
        "cpf": dados_completos_os.get("cpf"),
        "IMEI": dados_completos_os.get("IMEI"),
        "Acessorios": dados_completos_os.get("Acessorios"),
        "Defeito": dados_completos_os.get("Defeito"),
        "CondicoesProduto": dados_completos_os.get("CondicoesProduto"),
        "Serial": dados_completos_os.get("Serial")
    }

    #print("Dados filtrados (com chaves exatas):")
    #print(json.dumps(dados_filtrados, indent=2, ensure_ascii=False))

    # 4. Retornar o dicionário filtrado
    return dados_filtrados



def obter_token_zpo(cookies) -> str | None:
    """
    Faz uma requisição GET para a página de criação de OS para obter
    o token 'zpo' de um campo input hidden.

    Depende da biblioteca BeautifulSoup4 (`pip install beautifulsoup4 lxml`).

    Returns:
        A string do token 'zpo' se encontrado, ou None em caso de erro.
    """
    #print("\n--- Obtendo token ZPO ---")

    # URL da página que contém o token
    # Source: requisição obter token zpo.txt
    target_url = "https://biz6.samsungcsportal.com/svctracking/svcorder/ServiceOrderCreateEHNHHP.jsp"

    # Cabeçalhos baseados no arquivo de requisição GET
    # Source: requisição obter token zpo.txt
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8',
        'Upgrade-Insecure-Requests': '1', # Comum para requisições GET de páginas
        'Sec-Fetch-Site': 'none', # Pode variar dependendo do fluxo real
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-User': '?1',
        'Sec-Fetch-Dest': 'document',
        # 'Referer': # O referer pode não ser necessário ou pode ser a página anterior no fluxo
    }



    #print(f"URL: {target_url}")
    # print(f"Headers: {headers}") # Descomente para depurar
    # print(f"Cookies GSPN: {cookies}") # Descomente para depurar

    try:
        response = requests.get(
            target_url,
            headers=headers,
            cookies=cookies,
            timeout=30,
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        #print(f"Status Code da Resposta: {response.status_code}")

        # Verifica se o conteúdo parece ser HTML
        content_type = response.headers.get('Content-Type', '').lower()
        if 'html' not in content_type:
            print(f"Erro: A resposta não parece ser HTML (Content-Type: {content_type}).")
            # print(f"Resposta (texto): {response.text[:500]}...") # Descomente para depurar
            return None

        # Parsear o HTML com BeautifulSoup
        try:
            # Usar 'lxml' como parser é geralmente recomendado pela performance
            soup = BeautifulSoup(response.text, 'lxml')
        except Exception as e:
            # Captura erros gerais durante o parsing, embora raro com lxml
            print(f"Erro ao parsear o HTML com BeautifulSoup: {e}")
            return None

        # Encontrar o input com id='zpo'
        zpo_input = soup.find('input', {'id': 'zpo'})

        if zpo_input:
            # Extrair o valor do atributo 'value'
            token_zpo = zpo_input.get('value')

            if token_zpo: # Verifica se o valor não é None e não está vazio
                token_zpo = token_zpo.strip() # Remove espaços extras
                if token_zpo:
                     #print(f"Token ZPO encontrado: {token_zpo}")
                     return token_zpo
                else:
                     print("Erro: Input 'zpo' encontrado, mas o atributo 'value' está vazio.")
                     return None
            else:
                print("Erro: Input 'zpo' encontrado, mas não possui o atributo 'value'.")
                # print(f"Elemento encontrado: {zpo_input}") # Descomente para depurar
                return None
        else:
            print("Erro: Input com id='zpo' não encontrado no HTML da página.")
            # Pode ser útil salvar o HTML para análise se isso acontecer frequentemente
            # with open("debug_zpo_page.html", "w", encoding="utf-8") as f:
            #     f.write(response.text)
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao obter página para token ZPO: {http_err}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        if 'response' in locals():
          print("Detalhes da resposta (se disponível):")
          print(response.text[:500] + "...") # Mostrar início do HTML ou mensagem de erro
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: Não foi possível conectar à API GSPN em {target_url}.")
        print(f"Detalhes: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: A requisição para {target_url} demorou muito.")
        print(f"Detalhes: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro inesperado na requisição GSPN: {req_err}")

    return None # Retorna None em caso de qualquer erro não tratado acima


# --- Exemplo de Uso ---
if __name__ == "__main__":

    #cookies = obter_cookies_validos_recentes() # Chama a função para garantir que os cookies estejam atualizados

    cookies = obter_cookies_validos_recentes()
    zpo = obter_token_zpo(cookies)
    if zpo:
        print(f"Token ZPO obtido: {zpo}")
    else:
        print("Falha ao obter o token ZPO.")

