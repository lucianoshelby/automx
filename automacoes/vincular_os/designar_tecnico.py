from bs4 import BeautifulSoup # type: ignore # Biblioteca para parsear HTML
import json # Usado apenas para pretty-print no exemplo
import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
from automacoes.coletar_dados import fetch_os_data
from automacoes.cos.coletar_dados_cos import coletar_dados_os # Função auxiliar para coletar dados da OS
from automacoes.montar_payloads import montar_payload # Função auxiliar para montar payloads
import requests # Biblioteca para fazer requisições HT
from datetime import datetime, timedelta, timezone
from automacoes.montar_payloads import extract_js_variable # Função auxiliar para extrair variáveis JS do HTML

data_atual = datetime.now().strftime("%d/%m/%Y")
hora_gmt0 = datetime.now().strftime("%H:%M:%S") # Hora GMT+0

# --- Nova Função ---

def coletar_tecnicos_os(numero_os) -> dict | None:
    """
    Coleta a lista de técnicos disponíveis para um contexto específico
    (definido pelo payload FIXO) fazendo uma requisição POST à API GSPN.

    Esta função usa um payload fixo extraído do arquivo de exemplo
    'requisição coletar lista de técnicos.txt'.

    Returns:
        Um dicionário onde as chaves são os códigos dos engenheiros (str)
        e os valores são os nomes dos engenheiros (str).
        Retorna um dicionário vazio se a API retornar sucesso mas a lista
        'EtEngineerInfo' estiver vazia.
        Retorna None em caso de erro na requisição ou na resposta da API.
    """
    print("\n--- Coletando lista de técnicos (Payload Fixo) ---")

    # 1. Configuração da Requisição (Baseado nos arquivos fornecidos)
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    try:
        dados_os = fetch_os_data(numero_os) # Apenas para garantir que a função de coleta de dados esteja carregada
    except Exception as e:
        print(f"Erro ao coletar dados da OS: {e}")
        return None
    
    html_content = dados_os['html_os']
    
    cookies = dados_os.get('cookies')

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
    except Exception as e:
        print(f"Erro ao fazer o parse do HTML: {e}")
        return None
    # Parâmetros da Query String
    # Source: requisição coletar lista de técnicos.txt
    params = {
        'IV_F4_FLAG': 'X',
        'IV_PROD_AUTH': 'X'
    }

    # Payload FIXO (extraído do arquivo 'requisição coletar lista de técnicos.txt')
    # Source: requisição coletar lista de técnicos.txt
    payload = {
    'openTabID': '',
    "openTabID": "",
    "jobServiceType": soup.find("input", {"name": "jobServiceType"}).get("value", "CI") if soup.find("input", {"name": "jobServiceType"}) else "CI",
    "SOLASTCHANGEDDATE": soup.find("input", {"id": "SOLASTCHANGEDDATE"}).get("value", data_atual),
    "SOLASTCHANGEDTIME": soup.find("input", {"id": "SOLASTCHANGEDTIME"}).get("value", hora_gmt0),
    "STATE2": soup.find("input", {"id": "STATE2"}).get("value", ""),
    "LAST_APP_DATE": extract_js_variable(soup,"_l.LAST_APP_DATE"),
    'frYear': '',
    'toYear': '',
    'frMonth': '',
    'toMonth': '',
    'IV_PARTS_CODE': '',
    "IV_DATE": soup.find("input", {"id": "IV_DATE"}).get("value", ""),
    'fromListButton': '',
    'SAWPART': "", # Mantido como lista pois o parâmetro se repete
    'PART_SERIAL': '', # Nota: Este parâmetro aparece 3x, mas parse_qs pega o último valor vazio por padrão aqui
    'PART_TERM': 'O', # Nota: Este parâmetro aparece 3x, parse_qs pega o último valor 'O' por padrão aqui
    'soDetailType': '',
    'jspName': '',
    'dataChange': '',
    'p_listCall': 'X',
    'cmd': 'EngineerSearchCmd',
    'objectID': numero_os,
    "gi_ASC_JOB_NO": soup.find('input', {'id': 'ASC_JOB_NO'}).get('value', ''),
    'assignedFlag': 'X',
    'ascCode': '0002446971',
    "customerCode": soup.find("input", {"id": "customerCode"}).get("value"),
    'msg_seqno': '',
    'msgGuid': '',
    'msgText': '',
    'isawNo': '',
    'partsUsed': '',
    "wtyInOut": soup.find("input", {"id": "wtyInOut"}).get("value"),
    'IV_OBJKEY': '',
    'file_name': '',
    'fileSize': '',
    'Ctype': 'SVC_IND',
    'Code': '',
    "MODEL": soup.find("input", {"id": "MODEL"}).get("value"),
    "SERIAL": soup.find("input", {"id": "SERIAL"}).get("value"),
    "IMEI": soup.find("input", {"id": "IMEI"}).get("value"),
    "PRODUCT_DATE": soup.find("input", {"id": "PRODUCT_DATE"}).get("value"),
    'SYMPTOM_CAT1': '',
    'SYMPTOM_CAT2': '',
    'SYMPTOM_CAT3': '',
    'claimno': '',
    'wty_err_flag': '',
    'MBLNR': '',
    'MJAHR': '',
    'gi_material': '',
    'gi_qty': '',
    'gi_seq_no': '',
    'gi_engineer': '',
    'gi_engineer_nm': '',
    'gi_postingFlag': '',
    'gi_partWty': '',
    'cancelFlag': '',
    'svcPrcd': soup.find("input", {"id": "SVC_PRCD"}).get("value", "THB02"),
    'quotationFlag': '',
    'billingSearch': '',
    'hasWtyBilling': '',
    'model_p': '',
    'serialNo_p': '',
    'ASC_CODE_p': '',
    'IV_OBJECT_ID': numero_os,
    'interMessageType': '',
    'IRIS_CONDI': '',
    'IRIS_SYMPT': '',
    'IRIS_DEFECT': '',
    'IRIS_REPAIR': '',
    'IRIS_CONDI_DESC': '',
    'IRIS_SYMPT_DESC': '',
    'IRIS_DEFECT_DESC': '',
    'IRIS_REPAIR_DESC': '',
    'RetailInstallation': '',
    'additionalGasChargeForDVM': '',
    'canRedoMinorOption': '',
    'sameSAWCatCode': '',
    'canExtraPersonOption': '',
    'canExtraMileageHAOption': '',
    'sawExistCompressorSerialApproved': '',
    'sawExistSerialNoValidationApproved': '',
    'sawExistReverseVoidApproved': '',
    'highRisk': '',
    'defectType': '',
    'svcProd': '',
    'sawExistLabor': 'false',
    'bosFlag': '',
    'AUTH_GR': '',
    'PURCHASE_PLACE': '',
    'SAW_CATEGORY': '',
    'REASON': '',
    "currStatus": soup.find("input", {"id": "currStatus"}).get("value"),
    "autoDo": "",
    "cicProd": soup.find("input", {"id": "cicProd"}).get("value"),
    "hqSvcProd": soup.find("input", {"id": "hqSvcProd"}).get("value"),
    'ewpYn': '',
    'butlerX': '',
    'butlerXMsg': '',
    'sawExtraMileageApproved': 'false',
    'relatedTicketAscCode': '',
    'mesChkFlag': '',
    'month': '',
    'IV_SAW_INCL_FLAG': 'X',
    "curSvcType": soup.find("input", {"id": "curSvcType"}).get("value") or "CI",
    'irnExist': '',
    'zzuniqueId': '',
    "IV_INOUTWTY": soup.find("input", {"id": "IV_INOUTWTY"}).get("value")
    }
    # Ou cole o dicionário resultante diretamente aqui se preferir não usar a função auxiliar.

    # Cabeçalhos
    # Source: requisição coletar lista de técnicos.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID=4172879968', # Referer específico desta requisição
    }

    # Verifica se os cookies GSPN estão configurados
    if not cookies or 'AMOBGSPNSESSIONID' not in cookies:
         print("Aviso: Cookies GSPN (global 'cookies') parecem não estar configurados.")
         # return None # Descomente se quiser parar

    print(f"URL Base: {api_url}")
    print(f"Query Params: {params}")
    print(f"Payload: (Fixo, baseado no arquivo)")
    # print(f"Cookies GSPN: {cookies}") # Descomente para depurar

    # 2. Fazer a requisição POST
    try:
        response = requests.post(
            api_url,
            params=params,
            data=payload, # Usa o payload fixo
            headers=headers,
            cookies=cookies,
            timeout=30,
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        print(f"Status Code da Resposta: {response.status_code}")

        # 3. Processar a resposta JSON
        try:
            response_data = response.json()
            # print("Resposta JSON completa:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica se a API retornou sucesso
            # Source: resposta coletar lista de técnicos.txt (usa 'success')
            if response_data.get('success'):
                print("Sucesso na resposta da API (lista de técnicos).")

                # Verifica se a lista de engenheiros existe
                engineer_list = response_data.get('EtEngineerInfo')
                if isinstance(engineer_list, list):
                    tecnicos = {}
                    # Itera sobre a lista de dicionários de engenheiros
                    for engineer_info in engineer_list:
                        # Extrai o nome e o código, usando .get() por segurança
                        name = engineer_info.get('ENGINEER_NAME')
                        code = engineer_info.get('ENGINEER')

                        # Valida se ambos foram encontrados e não estão vazios
                        if name and code:
                            tecnicos[str(code).strip()] = str(name).strip() # Garante string e remove espaços
                        else:
                             print(f"  Aviso: Registro de engenheiro inválido/incompleto encontrado: {engineer_info}")

                    print(f"Extraídos {len(tecnicos)} técnicos válidos da lista.")
                    return tecnicos # Retorna o dicionário (pode estar vazio)
                else:
                     print("Erro: Chave 'EtEngineerInfo' não encontrada ou não é uma lista na resposta.")
                     return None # Retorna None se a estrutura esperada não existir

            else:
                # API retornou 'success: false'
                error_msg = response_data.get('message', 'Nenhuma mensagem específica.')
                print(f"Erro na resposta da API ao coletar técnicos: success=False")
                print(f"  Mensagem: {error_msg}")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON.")
            print(f"Resposta recebida (texto): {response.text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao coletar lista de técnicos: {http_err}")
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

import json # Usado apenas para pretty-print no exemplo

# --- Função de Busca e Fallback ---

def encontrar_codigo_tecnico(numero_os: str) -> str | None:
    """
    Busca um técnico em um dicionário pelo início do nome (primeiros dois nomes)
    e retorna seu código.

    Args:
        tecnicos_disponiveis: Dicionário onde chaves são códigos de técnico (str)
                              e valores são nomes completos (str).
                              Pode ser None ou vazio.
        nome_parcial: A string com os primeiros nomes a serem buscados.
                      Pode ser None ou vazio.

    Returns:
        O código (str) do primeiro técnico encontrado cujo nome completo começa
        com nome_parcial (ignorando maiúsculas/minúsculas e espaços extras).
        Se nenhum técnico for encontrado OU se nome_parcial for inválido/vazio,
        retorna o código do PRIMEIRO técnico listado no dicionário.
        Retorna None se o dicionário de entrada for None ou vazio.
    """
    #print(f"\n--- Buscando código para nome parcial: '{nome_parcial}' ---")
    tecnicos_disponiveis = coletar_tecnicos_os(numero_os) # Apenas para garantir que a função de coleta de dados esteja carregada
    # 1. Validar dicionário de entrada
    if not tecnicos_disponiveis or not isinstance(tecnicos_disponiveis, dict):
        print("Erro: Dicionário de técnicos disponíveis é inválido ou vazio.")
        return None
    try:
        dados_cos = coletar_dados_os(numero_os) # Apenas para garantir que a função de coleta de dados esteja carregada
    except Exception as e:
        print(f"Erro ao coletar dados da OS: {e}")
        return None
    nome_parcial = dados_cos.get('tecnico') # Nome do técnico designado (se houver)
    # 2. Normalizar nome parcial e verificar se a busca deve ser feita
    realizar_busca = False
    nome_normalizado = ""
    if nome_parcial:
        nome_normalizado = nome_parcial.strip().upper()
        if nome_normalizado: # Só busca se o nome normalizado não for vazio
             realizar_busca = True
             print(f"Buscando por: '{nome_normalizado}'")
        else:
             print("Nome parcial fornecido é vazio após normalização. Usando fallback.")
    else:
         print("Nome parcial não fornecido ou é None. Usando fallback.")


    # 3. Realizar a busca (se aplicável)
    if realizar_busca:
        for code, full_name in tecnicos_disponiveis.items():
            if not isinstance(full_name, str): # Sanity check
                continue

            # Normalizar o nome completo do técnico atual
            full_name_normalizado = full_name.strip().upper()

            # Verificar se o nome completo começa com o nome parcial normalizado
            if full_name_normalizado.startswith(nome_normalizado):
                print(f"Correspondência encontrada: '{full_name}' -> Código: {code}")
                return code # Retorna o código do primeiro match encontrado

        # Se o loop terminar sem encontrar correspondência
        print(f"Nenhuma correspondência exata encontrada para '{nome_normalizado}'. Usando fallback.")

    # 4. Fallback: Retornar o primeiro código do dicionário
    try:
        # next(iter(...)) é uma forma eficiente de pegar o primeiro item
        primeiro_codigo = next(iter(tecnicos_disponiveis))
        primeiro_nome = tecnicos_disponiveis[primeiro_codigo]
        print(f"Retornando código do primeiro técnico da lista (fallback): {primeiro_codigo} ('{primeiro_nome}')")
        return primeiro_codigo
    except StopIteration: # Caso o dicionário esteja vazio (já verificado no início, mas por segurança)
        print("Erro: Dicionário de técnicos está vazio (inesperado após validação inicial).")
        return None



def designar_tecnico_gspn(numero_os):
    """
    Modifica o status de uma Ordem de Serviço (OS) para ST040 no portal GSPN.

    Args:
        numero_os (str): O número da Ordem de Serviço a ser modificada.

    Returns:
        bool: True se a requisição foi enviada e a resposta indica sucesso,
              False caso contrário.
    """
    print(f"\n=== Iniciando Modificação de Status (ST040) para OS: {numero_os} ===")

    # 1. Obter Cookies
    try:
        dados_full = montar_payload(numero_os)
    except Exception as e:
        print(f'Erro ao carregar o payload para designar tecnico: {e}')

    try:
        codigo_tecnico = encontrar_codigo_tecnico(numero_os) # Apenas para garantir que a função de coleta de dados esteja carregada
    except Exception as e:
        print(f"Erro ao coletar dados da OS: {e}")
        return False
    
    cookies = dados_full.get('cookies')
    payload_original = dados_full.get('payload_os_full')

    if not payload_original:
        print(f"Falha na modificação: Não foi possível montar o payload base para a OS {numero_os}.")
        return False

    # 3. Obter Data/Hora Atual (usando hora do sistema local - assumindo GMT-3)
    try:
        now_local = datetime.now()
        data_atual = now_local.strftime('%d/%m/%Y')
        hora_atual = now_local.strftime('%H:%M:%S')
        print(f"Data/Hora Atual (Sistema): {data_atual} {hora_atual}")
    except Exception as e:
        print(f"Erro ao obter data/hora local: {e}. Abortando.")
        return False

    # 4. Construir Payload Modificado
    payload_modificado = []
    modificacoes_feitas = 0

    for key, original_value in payload_original:
        final_value = original_value # Valor padrão é o original

        # Aplica modificações necessárias
        if key == "ENGINEER":
            final_value = codigo_tecnico
            if original_value != final_value:
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                modificacoes_feitas += 1
        elif key == "sENGINEER":
            final_value = codigo_tecnico
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        elif key == "LAST_APP_TIME_DY_STT":
            final_value = hora_atual
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        elif key == "LAST_APP_DATE_DY_STT":
            final_value = data_atual
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        elif key == "STATUS":
            final_value = "ST025"
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        elif key == "REASON":  
            final_value = "HE005"
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1


        # Adiciona a tupla (chave, valor_final) à nova lista
        payload_modificado.append((key, final_value))

    if modificacoes_feitas < 2:
        print("Aviso: Um ou mais campos ('ENGINEER') não foram encontrados ou já tinham o valor desejado no payload base.")

    # 5. Preparar e Enviar Requisição
    target_url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    # Constrói o Referer dinamicamente (igual ao da função anterior)
    referer_url = "https://biz6.samsungcsportal.com/gspn/operate.do?UI=&currTabId=divJob"

    # Headers (baseados na requisição de fechamento - ajustar se necessário)
    headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Prototype-Version': '1.7.2',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': referer_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
    }

    try:
        print("\nEnviando requisição para modificar status da OS...")
        response = requests.post(
            target_url,
            headers=headers,
            cookies=cookies,
            data=payload_modificado, # Envia a lista de tuplas modificada
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        print(f"Status Code Modificação: {response.status_code}")
        response.raise_for_status() # Verifica erro HTTP

        # 6. Processar Resposta
        try:
            # Limpa a resposta
            response_text_clean = response.text.strip()
            if response_text_clean and response_text_clean[0] != '{':
                 json_start_index = response_text_clean.find('{')
                 if json_start_index != -1:
                      response_text_clean = response_text_clean[json_start_index:]
                 if response_text_clean.endswith('\n0'):
                     response_text_clean = response_text_clean[:-2].strip()

            modificacao_data = json.loads(response_text_clean)
            print(f"Resposta da Modificação (JSON): {modificacao_data}")

            # Verifica sucesso
            if modificacao_data.get("success") is True:
                print(f"Modificação da OS {numero_os} para status ST040 bem-sucedida!")
                return True
            else:
                print(f"Falha na modificação indicada pela resposta: {modificacao_data.get('returnMessage', 'Sem mensagem de erro')}")
                return False

        except json.JSONDecodeError as json_err:
            print(f"Erro ao decodificar JSON da resposta de modificação: {json_err}")
            print(f"Texto da resposta recebida: {response.text}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição de modificação: {req_err}")
        if hasattr(req_err, 'response') and req_err.response is not None:
                print(f"Response Status: {req_err.response.status_code}")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante a modificação da OS: {e}")
        return False
    

# Exemplo de uso
if __name__ == "__main__":
    numero_os = "4172879968"  # Exemplo de número de OS
    # Coletar técnicos disponíveis
    resultado = designar_tecnico_gspn(numero_os)
    if resultado:
        print(f"OS {numero_os} modificada com sucesso!")
    else:
        print(f"Falha ao modificar a OS {numero_os}.")

    