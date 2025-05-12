import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from coletar_dados import fetch_os_data, extract_os_data_full
#from cos.coletar_dados_cos import obter_os_correspondentes, coletar_dados_os
from login_gspn.cookies_manager import obter_cookies_validos_recentes
from automacoes.vincular_os.master_otp import get_master_otp
import requests
import json






# --- Exemplo de Uso ---
def consultar_dados_produto(cookies, identificador: str) -> dict | None:
    """
    Consulta os dados de um produto (HHP - celular) na API GSPN
    usando seu IMEI ou Número de Série.

    Args:
        identificador: O IMEI ou Número de Série do produto.

    Returns:
        Um dicionário contendo os dados do produto se encontrado e a consulta
        for bem-sucedida, ou None em caso de erro.
        O dicionário retornado terá as chaves: 'modelo_completo', 'imei_primario',
        'serial', 'buyer', 'imei_secundario'.
    """
    #print(f"\n--- Consultando dados do produto para Identificador: {identificador} ---")

    # 1. Obter o Master OTP
    # Assume que a função consultar_master_otp() existe e está acessível
    # e que a variável global 'session' (para o COS) está configurada.
    try:
        # Certifique-se que consultar_master_otp está definida e funcional
        master_otp = get_master_otp()
    except NameError:
         print("Erro Crítico: A função 'consultar_master_otp' não está definida.")
         return None

    if not master_otp:
        print("Erro: Falha ao obter o Master OTP necessário para a consulta.")
        return None
    print(f"Master OTP obtido: {master_otp}")

    # 2. Configurar a requisição para GSPN
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Payload baseado no arquivo 'requisição consultar dados pelo imei.txt'
    # Source: requisição consultar dados pelo imei.txt
    payload = {
        'cmd': 'GetIMEIofHHPCmd',
        'imei': identificador,     # Preenchido com o argumento
        'model': identificador,    # Preenchido com o argumento
        'system': 'MPTS',
        'imeiP': '',
        'multinum': 'Y',
        'motp': master_otp,        # Preenchido com o OTP obtido
        'src': 'S'
    }

    # Cabeçalhos baseados no arquivo de requisição
    # Source: requisição consultar dados pelo imei.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/ServiceOrderCreateEHNHHP.jsp', # Referer pode variar, ajuste se necessário
        # Outros cabeçalhos podem ser necessários
    }


    # 3. Fazer a requisição POST
    try:
        response = requests.post(
            api_url,
            data=payload,
            headers=headers,
            cookies=cookies, # Usa os cookies GSPN globais
            timeout=30,
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        #print(f"Status Code da Resposta: {response.status_code}")

        # 4. Processar a resposta JSON
        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica se a API retornou sucesso
            # Source: resposta consultar dados pelo imei.txt
            if response_data.get('success'):
                #print("Sucesso na resposta da API.")
                # Extrai os dados desejados
                dados_produto = {
                    'modelo_completo': response_data.get('model'),
                    'imei_primario': response_data.get('masterNum'),
                    'serial': response_data.get('serial'),
                    'buyer': response_data.get('sales_buyercode'),
                    'imei_secundario': response_data.get('slaveImei')
                }
                # Verifica se algum dado essencial veio vazio (opcional)
                if not dados_produto['modelo_completo'] or not dados_produto['serial']:
                     print("Aviso: Modelo ou Serial não encontrados na resposta, embora 'success' seja true.")
                     # Pode decidir retornar None ou o dicionário parcial
                #print("Dados do produto extraídos:")
                #print(json.dumps(dados_produto, indent=2, ensure_ascii=False))
                return dados_produto
            else:
                # API retornou 'success: false' ou a chave 'success' não existe
                error_msg = response_data.get('returnMessage', 'Nenhuma mensagem de erro específica.')
                print(f"Erro na resposta da API: success não é 'true'. Mensagem: {error_msg}")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao consultar dados do produto: {http_err}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        if 'response' in locals():
          print("Detalhes da resposta (se disponível):")
          try:
              print(json.dumps(response.json(), indent=2, ensure_ascii=False))
          except json.JSONDecodeError:
              print(response.text[:500] + "...")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: Não foi possível conectar à API GSPN em {api_url}.")
        print(f"Detalhes: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: A requisição para {api_url} demorou muito.")
        print(f"Detalhes: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro inesperado na requisição GSPN: {req_err}")

    return None # Retorna None em caso de qualquer erro não tratado acima


def consultar_descricao_modelo(cookies, modelo: str) -> dict | None:
    """
    Consulta os detalhes descritivos de um modelo de produto na API GSPN.

    Args:
        modelo: O código do modelo a ser consultado (ex: "SM-A145MZKRZTO").

    Returns:
        Um dicionário contendo os detalhes do modelo se encontrado,
        ou None em caso de erro. O dicionário retornado terá as chaves:
        'versao', 'descricao_do_modelo', 'descricao_categoria', 'categoria',
        'sub_descricao_categoria', 'descricao_local', 'local_svc_prod',
        'sub_categoria'.
    """
    #print(f"\n--- Consultando descrição para o Modelo: {modelo} ---")

    # 1. Configurar a requisição para GSPN
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Payload baseado no arquivo 'requisição consultar dados do modelo completo.txt'
    # Source: requisição consultar dados do modelo completo.txt
    payload = {
        'cmd': 'ServiceOrderModelSearchCmd',
        'MODEL': modelo,            # Preenchido com o argumento
        'ASC_CODE': '0002446971'   # Fixo conforme o arquivo (verificar se precisa ser dinâmico)
    }

    # Cabeçalhos baseados no arquivo de requisição
    # Source: requisição consultar dados do modelo completo.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/ServiceOrderCreateEHNHHP.jsp', # Ajuste se necessário
        # Outros cabeçalhos podem ser necessários
    }

    # 2. Fazer a requisição POST
    try:
        response = requests.post(
            api_url,
            data=payload,
            headers=headers,
            cookies=cookies, # Usa os cookies GSPN globais
            timeout=30,
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        #print(f"Status Code da Resposta: {response.status_code}")

        # 3. Processar a resposta JSON
        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica o código de retorno e a presença das listas necessárias
            # Source: resposta consultar dados do modelo completo.txt
            if response_data.get('returnCode') == '0' and \
               'etModelInfoList' in response_data and response_data['etModelInfoList'] and \
               'etModelVersionList' in response_data and response_data['etModelVersionList']:

                #print("Sucesso na resposta da API (returnCode 0).")
                model_info = response_data['etModelInfoList'][0] # Pega o primeiro item da lista de info
                model_versions = response_data['etModelVersionList']

                # Encontra a primeira versão válida (não "NONE")
                versao_encontrada = None
                for v in model_versions:
                    if v.get('version') and v['version'].upper() != 'NONE':
                        versao_encontrada = v['version']
                        break
                if not versao_encontrada:
                    # Fallback se não achar versão válida (pode pegar a vazia da info ou None)
                    versao_encontrada = model_info.get('VERSION')
                    print("Aviso: Nenhuma versão válida encontrada em etModelVersionList, usando fallback.")


                # Extrai os dados desejados do model_info usando .get() para segurança
                dados_modelo = {
                    'versao': versao_encontrada,
                    'descricao_do_modelo': model_info.get('model_desc'),
                    'descricao_categoria': model_info.get('prod_category_desc'),
                    'categoria': model_info.get('prod_category'),
                    'sub_descricao_categoria': model_info.get('sub_category_desc'), # Corrigido nome da chave
                    'descricao_local': model_info.get('local_svc_prod_desc'),
                    'local_svc_prod': model_info.get('local_svc_prod'),
                    'sub_categoria': model_info.get('sub_category'),
                }

                #print("Dados do modelo extraídos:")
                #print(json.dumps(dados_modelo, indent=2, ensure_ascii=False))
                return dados_modelo
            else:
                # API retornou código de erro ou listas vazias/inexistentes
                error_msg = response_data.get('returnMessage', 'Código de retorno não é 0 ou listas de dados ausentes/vazias.')
                print(f"Erro na resposta da API: {error_msg}")
                # print(f"Return Code: {response_data.get('returnCode')}") # Para depurar
                # print(f"etModelInfoList existe? {'etModelInfoList' in response_data and bool(response_data['etModelInfoList'])}") # Para depurar
                # print(f"etModelVersionList existe? {'etModelVersionList' in response_data and bool(response_data['etModelVersionList'])}") # Para depurar
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao consultar descrição do modelo: {http_err}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        if 'response' in locals():
          print("Detalhes da resposta (se disponível):")
          try:
              print(json.dumps(response.json(), indent=2, ensure_ascii=False))
          except json.JSONDecodeError:
              print(response.text[:500] + "...")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: Não foi possível conectar à API GSPN em {api_url}.")
        print(f"Detalhes: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: A requisição para {api_url} demorou muito.")
        print(f"Detalhes: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro inesperado na requisição GSPN: {req_err}")

    return None # Retorna None em caso de qualquer erro não tratado acima


def verificar_garantia(cookies, dados_produto: dict) -> dict | None:
    """
    Consulta a API GSPN para verificar os detalhes da garantia de um produto.

    Args:
        dados_produto: Um dicionário contendo informações do produto,
                       espera-se que contenha as chaves: 'modelo_completo',
                       'serial', 'local_svc_prod', 'imei_primario', 'buyer'.

    Returns:
        Um dicionário contendo os detalhes da garantia se a consulta for
        bem-sucedida, ou None em caso de erro. O dicionário retornado terá
        as chaves: 'new_labor_wt_d', 'laborterm', 'purchase_date',
        'new_parts_wt_d', 'partsterm', 'prod_date'.
    """
    #print(f"\n--- Verificando garantia para o produto ---")
    # print(f"Dados do produto recebidos: {dados_produto}") # Descomente para depurar entrada

    # 1. Validação da Entrada
    campos_necessarios = ['modelo_completo', 'serial', 'local_svc_prod', 'imei_primario', 'buyer']
    campos_faltantes = [campo for campo in campos_necessarios if campo not in dados_produto or not dados_produto[campo]]
    if campos_faltantes:
        print(f"Erro: Dados de entrada incompletos. Campos necessários ausentes ou vazios: {campos_faltantes}")
        return None

    # 2. Configurar a requisição para GSPN
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Parâmetros da Query String (parte da URL após '?')
    # Source: requisição verificar garantia.txt
    params = {
        'IV_WTY_EXCEPTION': '',
        'IV_ASC_CODE': '0002446971', # Fixo conforme arquivo, verificar necessidade de dinamismo
        'USE_PARALLEL': '0'
    }

    # Payload (corpo da requisição POST)
    # Source: requisição verificar garantia.txt
    payload = {
        'cmd': 'ServiceOrderWtyCheckCmd',
        'MODEL': dados_produto['modelo_completo'],
        'SERIAL_NO': dados_produto['serial'],
        'PURCHASE_DATE': '', # Fixo e vazio conforme arquivo
        'SVC_PRCD': dados_produto['local_svc_prod'],
        'IMEI': dados_produto['imei_primario'],
        'CorpCode': 'C820', # Fixo conforme arquivo
        'SERVICE_TYPE': 'CI', # Fixo conforme arquivo
        'overseas': 'N', # Fixo conforme arquivo
        'SALES_BUYER': dados_produto['buyer'],
        'DEALER': '' # Fixo e vazio conforme arquivo
    }

    # Cabeçalhos
    # Source: requisição verificar garantia.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/ServiceOrderCreateEHNHHP.jsp', # Ajuste se necessário
    }


    # 3. Fazer a requisição POST
    try:
        response = requests.post(
            api_url,
            params=params,     # Adiciona os parâmetros à URL
            data=payload,      # Corpo da requisição
            headers=headers,
            cookies=cookies,   # Usa os cookies GSPN globais
            timeout=30,
            verify=False       # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        #print(f"Status Code da Resposta: {response.status_code}")

        # 4. Processar a resposta JSON
        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica se a API retornou sucesso
            # Source: resposta verificar garantia.txt (usa 'success' e 'returnCode')
            if response_data.get('success') and response_data.get('returnCode') == '0':
                #print("Sucesso na resposta da API de garantia.")

                # Extrai os dados de garantia desejados
                dados_garantia = {
                    'new_labor_wt_d': response_data.get('new_labor_wt_d'),
                    'laborterm': response_data.get('laborterm'),
                    'purchase_date': response_data.get('purchase_date'),
                    'new_parts_wt_d': response_data.get('new_parts_wt_d'),
                    'partsterm': response_data.get('partsterm'),
                    'prod_date': response_data.get('prod_date')
                    # Adicione outros campos da resposta se necessário
                    # 'wtyType': response_data.get('wtyType') # Exemplo: "Fora de Garantia"
                }

                #print("Dados de garantia extraídos:")
                #print(json.dumps(dados_garantia, indent=2, ensure_ascii=False))
                return dados_garantia
            else:
                # API retornou 'success: false' ou returnCode diferente de '0'
                error_msg = response_data.get('returnMessage', 'Nenhuma mensagem específica.')
                eula_msg = response_data.get('EsEulaInfo', {}).get('eulaMsg', '') # Tenta pegar msg da EULA se houver
                print(f"Erro na resposta da API de garantia: success={response_data.get('success')}, returnCode={response_data.get('returnCode')}")
                if error_msg: print(f"  Mensagem de Retorno: {error_msg}")
                if eula_msg: print(f"  Mensagem EULA: {eula_msg}")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API de garantia como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao verificar garantia: {http_err}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        if 'response' in locals():
          print("Detalhes da resposta (se disponível):")
          try:
              print(json.dumps(response.json(), indent=2, ensure_ascii=False))
          except json.JSONDecodeError:
              print(response.text[:500] + "...")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: Não foi possível conectar à API GSPN em {api_url}.")
        print(f"Detalhes: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: A requisição para {api_url} demorou muito.")
        print(f"Detalhes: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro inesperado na requisição GSPN: {req_err}")

    return None # Retorna None em caso de qualquer erro não tratado acima

