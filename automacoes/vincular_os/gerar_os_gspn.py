import requests
import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
import json
import re # Import regular expressions for potential response cleaning
from automacoes.vincular_os.dados_gerais import coletar_informacoes_completas
from login_gspn.cookies_manager import obter_cookies_validos_recentes
from datetime import datetime, date
from automacoes.vincular_os.vincular_os_cos import vincular_os


hora_atual = datetime.now().strftime("%H:%M:%S")
data_atual = datetime.now().strftime("%d/%m/%Y")
data_e_hora_atual = datetime.now().strftime("%d%m%Y%H%M%S")

def criar_ordem_servico(numero_os) -> str | None:
    """
    Envia a requisição para criar uma Ordem de Serviço (OS) no GSPN.

    Args:
        payload_os: Um dicionário completo contendo todos os dados
                    formatados como 'application/x-www-form-urlencoded'
                    para o corpo da requisição POST. A construção deste
                    payload é de responsabilidade do chamador.

    Returns:
        O número da OS criada (string, vindo de 'returnObjectID') se a
        operação for bem-sucedida, ou None em caso de erro.
    """
    print("\n--- Tentando criar Ordem de Serviço ---")

    cookies = obter_cookies_validos_recentes()
    try:
        dados_completos = coletar_informacoes_completas(cookies, numero_os)
        print(f"Dados completos coletados: {dados_completos}")
    except Exception as e:
        print(f"Erro ao coletar informações completas: {e}")
        return False
    try:
        payload_os = criar_payload_para_gerar_os(dados_completos)
    except Exception as e:
        print(f"Erro ao criar payload para gerar OS: {e}")
        return None
    # 1. Validação básica do payload de entrada
    if not payload_os or not isinstance(payload_os, dict):
        print("Erro: Payload para criação da OS está vazio ou não é um dicionário.")
        return None
    # Poderia adicionar verificações de chaves essenciais no payload se necessário
    # Ex: if 'cmd' not in payload_os or 'zpo' not in payload_os: ...

    # 2. Configuração da Requisição
    api_url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Cabeçalhos baseados no arquivo 'requisição abrir OS.txt'
    # Source: requisição abrir OS.txt
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/ServiceOrderCreateEHNHHP.jsp', # Ajuste se necessário
        # Outros headers podem ser necessários
    }

    # Verifica se os cookies GSPN estão configurados
    if not cookies or 'AMOBGSPNSESSIONID' not in cookies:
         print("Aviso: Cookies GSPN (global 'cookies') parecem não estar configurados.")
         # return None # Descomente se quiser parar

    print(f"URL: {api_url}")
    print(f"Payload: (Omitido por tamanho, verifique a variável passada)")
    # print(f"Cookies GSPN: {cookies}") # Descomente para depurar

    # 3. Fazer a requisição POST
    try:
        response = requests.post(
            api_url,
            data=payload_os, # Envia o dicionário como form-urlencoded
            headers=headers,
            cookies=cookies,
            timeout=60, # Timeout um pouco maior para criação de OS
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

        print(f"Status Code da Resposta: {response.status_code}")

        # 4. Processar a resposta JSON
        response_text = response.text
        # print(f"Resposta Bruta (Texto): {response_text}") # Descomente para depuração total

        # --- Limpeza Opcional da Resposta ---
        # Tenta extrair apenas o JSON se houver caracteres extras como no exemplo "ae{...}0."
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_text = match.group(0)
            print("Texto JSON extraído da resposta.")
        else:
            # Se não achar um JSON claro, tenta usar o texto todo (pode falhar no parse)
            print("Aviso: Não foi possível extrair um JSON claro da resposta, tentando usar texto completo.")
            json_text = response_text

        try:
            response_data = json.loads(json_text)
            # print("Resposta JSON Parseada:") # Descomente para depurar
            # print(json.dumps(response_data, indent=2, ensure_ascii=False)) # Descomente para depurar

            # Verifica se a API retornou sucesso
            if response_data.get('success') and response_data.get('returncode') == '0':
                os_gspn = response_data.get('returnObjectID')

                if os_gspn:
                    os_gspn = str(os_gspn).strip() # Garante que é string e remove espaços
                    if os_gspn:
                        success_msg = response_data.get('message', 'OS criada com sucesso.')
                        vincular_os(numero_os, os_gspn) # Chama a função de vinculação
                        print(f"SUCESSO: {success_msg}")
                        print(f"Número da OS (GSPN): {os_gspn}")
                        return os_gspn
                    else:
                         print("Erro: Campo 'returnObjectID' retornado vazio.")
                         return None
                else:
                    print("Erro: Campo 'returnObjectID' não encontrado na resposta de sucesso.")
                    return None
            else:
                # API retornou 'success: false' ou returnCode diferente de '0'
                error_msg = response_data.get('message', 'Nenhuma mensagem específica.')
                print(f"Erro na resposta da API ao criar OS: success={response_data.get('success')}, returncode={response_data.get('returncode')}")
                print(f"  Mensagem: {error_msg}")
                # Verificar EtErrInfo pode dar mais detalhes
                et_err_info = response_data.get('EtErrInfo')
                if et_err_info and isinstance(et_err_info, list) and len(et_err_info) > 0:
                    print(f"  Detalhes do Erro (EtErrInfo): {et_err_info}")
                return None

        except json.JSONDecodeError:
            print("Erro: Não foi possível decodificar a resposta da API como JSON após limpeza.")
            print(f"Texto que falhou no parse: {json_text[:500]}...")
            return None

    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao criar OS: {http_err}")
        print(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
        if 'response' in locals():
          print("Detalhes da resposta (se disponível):")
          try:
              # Tenta mostrar erro JSON se possível
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


def criar_payload_para_gerar_os(dados_completos: dict) -> dict:
    """
    Função de exemplo para criar um payload de Ordem de Serviço (OS) para teste.
    """
    
    garantia = dados_completos.get("tipo_atendimento")
    lp_ow = "LP"
    void = ''
    if garantia != "Garantia Samsung":
        lp_ow = "OW"
        void = "VOID1"
    # Exemplo de payload, ajuste conforme necessário
    payload = {
        'cmd': 'ServiceOrderModifyEHNCmd',
        'SERVICE_DATE': '', 'SERVICE_TIME': '', 'CURR_STATUS': '', 'STATUS': '',
        'objectID': '', 'object_ID': '', 'WARNING_SKIP': '', 'SVC_LEVEL': '',
        'runWebCheckLogic': 'X', 'SUB_SVC_TYPE_AD': '', 'currPage': '', 'numPerPage': '',
        'Serno': '', 'ASCCODE': '', 'MB_IF_YN': '', 'MB_IF_RT_YN': '', 'MB_IF_RT_INFO': '',
        'MB_IF_VERSION': '', 'enterCreationDateTime': data_e_hora_atual, # Exemplo, use data/hora atual
        'TICKET_COMPANY': 'C820', 'SERVICE_COMPANY': 'C820',
        'zpo': dados_completos.get('zpo'), # Exemplo, obter dinamicamente
        'ACT_DATE': '', 'ACT_MOBILE_NO': '', 'SVC_PROVIDER': '', 'preBookingFlag': '',
        'sr_no': '', 'IV_DATE': data_atual, # Exemplo, use data atual
        'GD_EWP_FLAG': '0', 'DIA_METHOD': 'I', 'SES_FLAG': 'A', 'DIA_VERSION': '',
        'DIA_SW_VERSION': '', 'DIA_VERSION_CHECK': '', 'DIA_RESULT': '', 'DIA_ERROR': '',
        'DIA_RESULT_CODE': '', 'DIA_CHECK_FLAG': 'Y', 'GD_SESS_ID': '', 'GD_RESULT_TYPE': 'IQC',
        'LATEST_VER': ';;', 'SW_VER': '', 'PROCESS_ID': '', 'GD_BASE_URL': '',
        'GD_MAND_ASC': 'Y', 'REDO': '', 'DIA_TYPE': 'I', 'IV_GUBUN': 'S', 'IV_AUTO_FLAG': 'S',
        'VERIFIED_CC_FLAG': '', 'BP_NO': '', 'GD_SKIPSAVE': '', 'regionCode': '',
        'cityFlag': 'N', 'postalFlag': 'N', 'IV_INOUTWTY': '', 'recaptcha_response_field': '',
        'recaptcha_challenge_field': '', 'rdoDisplay': 'H', 'ASC_JOB_NO': dados_completos.get("ASCJOB"), # Deve ser único
        'ASC_CODE': '0002446971', 'MODEL': dados_completos.get('modelo_completo'), 'VERSION': dados_completos.get('versao'),
        'model_desc': dados_completos.get('descricao_do_modelo'), 'prod_category_desc': dados_completos.get('descricao_categoria'),
        'prod_category': dados_completos.get('categoria'), 'sub_category_desc': 'Mobile Phone',
        'local_svc_prod_desc': 'HHP - GSM', 'SVC_PRCD': 'THB02', 'sub_category': dados_completos.get('sub_descricao_categoria'),
        'HQ_SVC_PRCD': 'THBB6', 'SOLD_COUNTRY_CODE': '', 'overseas': 'N',
        'SERIAL_NO': dados_completos.get('serial'), 'IMEI': dados_completos.get('imei_primario'), 'SALES_BUYER': dados_completos.get("buyer"),
        'pbaQrCode': '', 'masterOTP': dados_completos.get("MasterOTP"), # Exemplo, obter dinamicamente
        'SERIAL_GMES': '', 'UN_IO': '', 'SKU': '', 'MODULE_ID': '', 'PRODUCT_DATE': dados_completos.get("prod_date"),
        'SKIP_SN': '', 'SALES_COUNTRY': '', 'PURCHASE_DATE': dados_completos.get('purchase_date'), 'EULA_FLAG': 'D',
        'ADH_FLAG': '', 'CERTI_NO': '', 'DAMAGE_EXPLANATION': '', 'LOSS_TYPE_ID': '',
        'CLAIM_INSU_NO': '', 'POLICY_ID': '', 'SC_PLUS_FLAG': '', 'PACK_BASE': '',
        'CHARGE_TYPE': '', 'CHARGE_AMOUNT': '', 'CHARGE_WAERS': '', 'OW_PACK_FLAG': '',
        'rType': '', 'sCompany': 'C820', 'PACK_NUMBER': '', 'WTY_in_out': lp_ow,
        'NEW_LABOR_WT_D': f'(L){dados_completos.get('new_labor_wt_d')}', 'NEW_PARTS_WT_D': f'(P){dados_completos.get('new_parts_wt_d')}',
        'WTY_EXCEPTION': void, 'LABOR_TERM': dados_completos.get('laborterm'), 'PARTS_TERM': dados_completos.get('partsterm'), 'PACK_CODE': '',
        'PACK_DESC': '', 'CONTRACTNO': '', 'CERTI': '', 'SVC_CONTRACT': '', 'extWtyDesc': '',
        'availAmount': '', 'zCourse': '', 'zCourseValue': '', 'extWtyDuration': '',
        'contractPurDate': '', 'eppType': '', 'eppTypeDesc': '', 'eppContractNo': '',
        'SERVICE_TYPE': 'CI', 'SUB_SVC_TYPE2': '', 'SUB_SVC_TYPE3': '', 'ESCAL_ASC': '',
        'SYMPTOM_CAT1': 'L2', 'SYMPTOM_CAT2': '01', 'SYMPTOM_CAT3': '01',
        'FIRST_APP_DATE': data_atual, 'FIRST_APP_TIME': hora_atual, # Use data/hora atual
        'REQUEST_DATE': data_atual, 'REQUEST_TIME': hora_atual, # Use data/hora atual
        'UNIT_RECV_DATE': data_atual, 'UNIT_RECV_TIME': hora_atual, # Use data/hora atual
        'TOKEN_NO': dados_completos.get('ASCJOB'), # Pode precisar ser dinâmico ou ter regra
        'TOKEN_DT': '', 'TOKEN_TM': '', 'CUST_CALL_DT': '', 'CUST_CALL_TM': '', 'TOT_CNT': '',
        'QM_SO_CREATE_DATE': '', 'QM_SO_CREATE_TIME': '', 'QM_PASS_VERIFY_DATA': 'N',
        'CUSTOMER_COMMENT': '', 'D_NAME_FIRST': dados_completos.get('NAME_FIRTS'), 'D_NAME_LAST': dados_completos.get('NAME_LAST'),
        'CONSUMER': dados_completos.get('CONSUMER'), 'ADDRNUMBER': dados_completos.get('ADDRNUMBER'), 'BP_TYPE': dados_completos.get('BP_TYPE'),
        'CONTACT_FLAG': dados_completos.get('CONTACT_FLAG'), 'TEL': '', 'CUST_CONFIRM_DT': data_atual, # Use data/hora atual
        'CUST_CONFIRM_TM': hora_atual, # Use data/hora atual
        'ALT_TEL_NO': '', 'ALT_EMAIL': '', 'ENGINEER': '', 'CC_CODE': '', 'DEALER_JOB_NO': '',
        'B2B_SVC': '', 'MANAGED_SVC_CODE': '', 'MANAGED_SVC_DESC': '', 'DEALER': '',
        'LOCAL_INVOICE_NO': '', 'SUB_SVC_TYPE': '', 'REF_REMARK': '', 'REF_REMARK_SR': '',
        'CARRIER': 'C001', 'PURCHASE_PLACE': '', 'CONTACT_TRK': '',
        'ACCESSORY': dados_completos.get('Acessorios'),
        'REMARK': dados_completos.get('CondicoesProduto'), # Condições do Produto
        'DEFECT_DESC': dados_completos.get('Defeito'), # Defeito
        'DEFECTDESC_L': dados_completos.get('Defeito'), # Defeito
        'attach_doc_type': 'ATT01', 'attach_doc_type_ewp': 'ATT04'
    }



    return payload
if __name__ == "__main__":
    # Exemplo de uso da função
    numero_os = "352544"  # Substitua pelo número da OS que deseja criar
    os_criada = criar_ordem_servico(numero_os)
    if os_criada:
        print(f"Ordem de Serviço criada com sucesso: {os_criada}")
    else:
        print("Falha ao criar Ordem de Serviço.")