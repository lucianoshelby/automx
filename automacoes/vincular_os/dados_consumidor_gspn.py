import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
import requests
import json
from datetime import datetime, timedelta

from login_gspn.cookies_manager import obter_cookies_validos_recentes # [cite: 1]


def coletar_codigo_consumidor(cookies, cpf: str) -> str | None:
    """
    Consulta a API usando o CPF para obter o código do consumidor.

    Args:
        cpf: O número do CPF do cliente (como string, apenas números).

    Returns:
        O código do consumidor (string) se encontrado, ou None em caso de erro.
    """
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do" # [cite: 3]
     # Obtém os cookies válidos [cite: 1]
    # Payload base com campos fixos, conforme arquivo de requisição [cite: 4]
    # O campo 'uniqueID' será atualizado com o CPF fornecido.
    payload = {
        'cmd': 'SVCPopCustomerSearchCmd',
        'numPerPage': '100',
        'currPage': '0',
        'SVCRequestNo': 'false',
        'BP_NO': '',
        'MODEL': '',
        'SERIAL_NO': '',
        'IMEI': '',
        'bpKind': '',
        'IV_C_CHANNEL': '',
        'IV_DIVISION': 'X',
        'country': 'BR',
        'IV_ASC_CODE': '',
        'Sequence': '',
        'firstName': '',
        'lastName': '',
        'phone': '',
        'uniqueID': cpf, # CPF entra aqui [cite: 4]
        'bpno': '',
        'IV_EMAIL': '',
        'D_BP_TYPE': '',
        'D_TITLE': '',
        'D_NAME_FIRST': '',
        'D_NAME_LAST': '',
        'D_CONSUMER': '',
        'D_GENDER': '',
        'D_UNIQUE_ID': '',
        'D_PREFERENCE_CHANNEL': '',
        'D_HOME_PHONE': '',
        'D_OFFICE_PHONE': '',
        'D_OFFICE_PHONE_EXT': '',
        'D_MOBILE_PHONE': '',
        'D_FAX': '',
        'D_EMAIL': '',
        'D_CONTACT_FLAG': '',
        'D_STREET1': '',
        'D_STREET2': '',
        'D_STREET3': '',
        'D_DISTRICT': '',
        'D_CITY': '',
        'D_CITY_CODE': '',
        'D_REGION_CODE': '',
        'D_REGION': '',
        'D_COUNTRY': '',
        'D_POST_CODE': ''
    }

    # Cabeçalhos baseados no arquivo de requisição [cite: 3]
    # 'Cookie' será tratado pelo parâmetro 'cookies' do requests
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8', # [cite: 4]
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0', # [cite: 3]
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*', # [cite: 3]
        'Origin': 'https://biz6.samsungcsportal.com', # [cite: 4]
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/common/SVCPopCustomerSearch.jsp', # [cite: 4]
        # Outros cabeçalhos podem ser necessários dependendo da API
    }

    print(f"\n--- Consultando código do consumidor para CPF: {cpf} ---")
    print(f"URL: {api_url}")
    # print(f"Payload: {payload}") # Descomente para depurar o payload enviado
    # print(f"Cookies: {cookies}") # Descomente para depurar os cookies

    try:
        response = requests.post(
            api_url,
            data=payload,    # Usar 'data' para 'application/x-www-form-urlencoded'
            headers=headers,
            cookies=cookies, # Passa o dicionário de cookies global
            timeout=30,
            verify=False       # Define um timeout para a requisição
        )

        # Verifica se houve erro na requisição HTTP (status code não 2xx)
        response.raise_for_status()

        print(f"Status Code da Resposta: {response.status_code}") # [cite: 1]

        # Tenta decodificar a resposta JSON
        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica se a resposta indica sucesso e contém os dados esperados [cite: 2]
            if response_data.get('success') and 'dataLists' in response_data and response_data['dataLists']:
                # Extrai o código do consumidor do primeiro item da lista [cite: 2]
                codigo_consumidor = response_data['dataLists'][0].get('CONSUMER')
                if codigo_consumidor:
                    print(f"Código do Consumidor encontrado: {codigo_consumidor}")
                    return codigo_consumidor
                else:
                    print("Erro: Campo 'CONSUMER' não encontrado nos dados do cliente.")
                    return None
            elif response_data.get('retcode') != '0':
                 print(f"Erro retornado pela API: retcode={response_data.get('retcode')}, retmsg='{response_data.get('retmsg')}'")
                 return None
            else:
                print("Erro: Resposta da API não contém 'dataLists' ou a lista está vazia.")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...") # Mostra parte da resposta
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao consultar consumidor: {http_err}")
        print(f"Status Code: {response.status_code}")
        print("Detalhes da resposta (se disponível):")
        try:
            # Tenta mostrar o erro da API se for JSON
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        except json.JSONDecodeError:
            print(response.text[:500] + "...") # Mostra parte do texto se não for JSON
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Erro de Conexão: Não foi possível conectar à API em {api_url}.")
        print(f"Detalhes: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Erro de Timeout: A requisição para {api_url} demorou muito.")
        print(f"Detalhes: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Erro inesperado na requisição: {req_err}")

    return None # Retorna None em caso de qualquer erro



def coletar_dados_detalhados_consumidor(cookies, cpf: str) -> dict | None:
    """
    Consulta a API GSPN usando o código do consumidor (BP_NO) para obter
    dados detalhados/complementares do consumidor (usando SVCPopCustomerDetailCmd).

    Args:
        consumer_code: O código do consumidor (valor do campo 'CONSUMER').

    Returns:
        Um dicionário contendo os dados complementares se encontrado,
        ou None em caso de erro. O dicionário retornado terá as chaves:
        'CONSUMER', 'ADDRNUMBER', 'NAME_LAST', 'NAME_FIRST', 'CONTACT_FLAG',
        'BP_TYPE'.
    """
    try:
        consumer_code = coletar_codigo_consumidor(cookies, cpf) # Coleta o código do consumidor
    except Exception as e:
        print(f"Erro ao coletar o código do consumidor: {e}")
        return None
    if not consumer_code:
        print("Erro: Código do consumidor não fornecido.")
        return None

    print(f"\n--- Coletando dados complementares (DetailCmd) para Consumer Code: {consumer_code} ---")

    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Payload baseado no arquivo 'requisição coledar dados complementares consumidor.txt'
    # Source: requisição coledar dados complementares consumidor.txt
    payload = {
        'cmd': 'SVCPopCustomerDetailCmd', # <- Comando CORRETO
        'numPerPage': '100',
        'currPage': '0',
        'SVCRequestNo': 'false',
        'BP_NO': consumer_code, # <- Código do consumidor aqui
        'MODEL': '',
        'SERIAL_NO': '',
        'IMEI': '',
        'bpKind': '',
        'IV_C_CHANNEL': '',
        'IV_DIVISION': 'X',
        'country': 'BR',
        'IV_ASC_CODE': '0002446971', # <- Fixo conforme arquivo
        'Sequence': '',
        'firstName': '',
        'lastName': '',
        'phone': '',
        'uniqueID': '', # <- CPF/UniqueID vazio
        'bpno': consumer_code, # <- Código do consumidor aqui também
        'IV_EMAIL': '',
        # Os campos D_ podem ser omitidos se a API os ignorar quando vazios,
        # mas incluí-los vazios replica exatamente a requisição de exemplo.
        'D_BP_TYPE': '', 'D_TITLE': '', 'D_NAME_FIRST': '', 'D_NAME_LAST': '',
        'D_CONSUMER': '', 'D_GENDER': '', 'D_UNIQUE_ID': '', 'D_PREFERENCE_CHANNEL': '',
        'D_HOME_PHONE': '', 'D_OFFICE_PHONE': '', 'D_OFFICE_PHONE_EXT': '',
        'D_MOBILE_PHONE': '', 'D_FAX': '', 'D_EMAIL': '', 'D_CONTACT_FLAG': '',
        'D_STREET1': '', 'D_STREET2': '', 'D_STREET3': '', 'D_DISTRICT': '',
        'D_CITY': '', 'D_CITY_CODE': '', 'D_REGION_CODE': '', 'D_REGION': '',
        'D_COUNTRY': '', 'D_POST_CODE': ''
    }

    # Cabeçalhos baseados no novo arquivo de requisição
    # Source: requisição coledar dados complementares consumidor.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36', # Exemplo do novo arquivo
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/common/SVCPopCustomerSearch.jsp', # Mesmo referer
    }

    # Verifica se os cookies GSPN estão configurados
    if not cookies or 'AMOBGSPNSESSIONID' not in cookies:
         print("Aviso: Cookies GSPN (global 'cookies') parecem não estar configurados.")
         # return None # Descomente se quiser parar

    print(f"URL: {api_url}")
    # print(f"Payload: {payload}") # Descomente para depurar payload completo
    # print(f"Cookies GSPN: {cookies}") # Descomente para depurar

    try:
        response = requests.post(
            api_url,
            data=payload,
            headers=headers,
            cookies=cookies,
            timeout=30,
            verify=False # Define um timeout para a requisição
        )
        response.raise_for_status() # Verifica erros HTTP

        print(f"Status Code da Resposta: {response.status_code}")

        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica o sucesso e a presença dos dados
            # Source: resposta coletar dados complementares consumidor.txt
            if response_data.get('success') and response_data.get('retcode') == '0' and \
               'dataLists' in response_data and response_data['dataLists']:

                print("Sucesso na resposta da API (dados complementares - DetailCmd).")
                consumidor_info = response_data['dataLists'][0]

                # Extrai os campos solicitados
                dados_complementares = {
                    'CONSUMER': consumidor_info.get('CONSUMER'),
                    'ADDRNUMBER': consumidor_info.get('ADDRNUMBER'), # Agora deve ter valor
                    'NAME_LAST': consumidor_info.get('NAME_LAST'),
                    'NAME_FIRST': consumidor_info.get('NAME_FIRST'),
                    'CONTACT_FLAG': consumidor_info.get('CONTACT_FLAG'), # Agora deve ter valor
                    'BP_TYPE': consumidor_info.get('BP_TYPE') # Agora deve ter valor
                }

                # Validação opcional
                if dados_complementares.get('CONSUMER') != consumer_code:
                    print(f"Aviso: O código do consumidor retornado ({dados_complementares.get('CONSUMER')}) não corresponde ao solicitado ({consumer_code}).")

                print("Dados complementares do consumidor extraídos:")
                print(json.dumps(dados_complementares, indent=2, ensure_ascii=False))
                return dados_complementares

            elif response_data.get('retcode') != '0':
                 print(f"Erro retornado pela API: retcode={response_data.get('retcode')}, retmsg='{response_data.get('retmsg')}'")
                 return None
            else:
                error_msg = response_data.get('retmsg', 'Dados complementares não encontrados ou resposta inválida (DetailCmd).')
                print(f"Erro: Não foi possível obter os dados complementares. Mensagem: {error_msg}")
                if not response_data.get('dataLists'):
                     print("  (Detalhe: A lista 'dataLists' está vazia ou ausente na resposta)")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao coletar dados complementares (DetailCmd): {http_err}")
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

# --- Exemplo de Uso ---
if __name__ == "__main__":

    # --- Bloco de Configuração de Teste ---



    # Use o mesmo código de consumidor dos exemplos anteriores
    consumer_code_teste = "79957374168"

    if consumer_code_teste:
        dados_compl = coletar_dados_detalhados_consumidor(consumer_code_teste)

        if dados_compl:
            print(f"\n>>> Dados Complementares (DetailCmd) obtidos para o Consumidor '{consumer_code_teste}':")
            print(json.dumps(dados_compl, indent=4, ensure_ascii=False))
            # Agora ADDRNUMBER, CONTACT_FLAG, BP_TYPE devem ter valores baseado na nova resposta
        else:
            print(f"\n>>> Falha ao obter os Dados Complementares (DetailCmd) para o Consumidor '{consumer_code_teste}'.")
    else:
        print("Código do consumidor não fornecido para teste.")