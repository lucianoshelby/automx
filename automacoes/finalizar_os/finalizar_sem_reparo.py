import requests
import os
import json
from datetime import datetime
import pytz # For timezone handling (pip install pytz)
from automacoes.montar_payloads import montar_payload # Importa a função de montagem de payloads
from automacoes.coletar_dados import extract_os_data_full, coletar_pecas_gspn_total
from automacoes.pecas import remover_pecas_os # Importa a função de login para obter cookies
from automacoes.finalizar_os.anexos_gspn import checar_e_anexar_obrigatorios # Importa a função de verificação de anexos
from login_gspn.cookies_manager import obter_cookies_validos_recentes # Importa a função de login para obter cookies
import time
from automacoes.cos.coletar_dados_cos import coletar_dados_os, coletar_usadas_cos # Importa a função de coleta de dados COS
now_local = datetime.now()

def aplicar_reparo_completo_remontagem(numero_os):
    """
    Fecha uma Ordem de Serviço (OS) como "sem reparo" (remontagem) no portal GSPN.

    Args:
        numero_os (str): O número da Ordem de Serviço a ser fechada.

    Returns:
        bool: True se a requisição foi enviada e a resposta indica sucesso,
              False caso contrário.
    """
    print(f"\n=== Iniciando Fechamento Sem Reparo para OS: {numero_os} ===")



    # 2. Obter Payload Base
    # Substitua 'montar_payload' pela sua função real!
    
    dados_full = montar_payload(numero_os)
    cookies = dados_full.get('cookies')
    payload_original = dados_full.get('payload_os_full')
    garantia = None
    for chave, valor in payload_original:
        if chave == "IN_OUT_WTY":
            print(f"Valor de IN_OUT_WTY: {valor}")

            if valor == "LP":

                try:
                    print("Mudando para Out Of Warranty (OW)...")
                    mudar_pra_ow(dados_full)# Muda a OS para Out Of Warranty (OW) se necessário
                except Exception as e:
                    print(f"Erro ao mudar para OW: {e}")
                    
    dados_os = extract_os_data_full(dados_full) # Coleta os dados da OS
    dados_full.update(dados_os) # Atualiza os dados_full dados da OS
    pecas_gspn = dados_full.get('parts')
    #print(f'Peças GSPN: {pecas_gspn}')
    try:
        if pecas_gspn:
            parts_to_remove = coletar_pecas_gspn_total(dados_full)
            print(f"Peças GSPN a serem removidas: {parts_to_remove}")
            dados_full['parts_to_remove'] = parts_to_remove # Adiciona as partes a serem removidas ao dicionário
            if parts_to_remove:
                print(f"Removendo peças GSPN")
                pecas_cos = coletar_usadas_cos(dados_full)
                dados_full.update(pecas_cos) # Atualiza os dados_full com as peças COS
                remover_pecas_os(dados_full)# Remove as peças GSPN da OS
                #time.sleep(2) 
            else:
                print(f"Não foram encontradas peças GSPN para remover.")

    except Exception as e:
        print(f"Erro ao coletar peças GSPN: {e}")


    if not payload_original:
        print(f"Falha no fechamento: Não foi possível montar o payload base para a OS {numero_os}.")
        return False
    print('Verificando anexos...')
    resultado_anexos = checar_e_anexar_obrigatorios(numero_os)
    if resultado_anexos:
        print("Anexos verificados com sucesso.")
    else:
        print("Falha na verificação de anexos. Tentando prosseguir sem verificar.")
        

    # 3. Definir Modificações e Valores Atuais
    modificacoes_fixas = {
        "STATUS": "ST035",
        "REASON": "HL005",
        "REPAIR_DESC": "REMONTAGEM",
        "IRIS_CONDI": "1",
        "LAB_TYPE": "AE",
        "IRIS_SYMPT_QCODE": "SRC012",
        "IRIS_SYMPT": "T12",
        "IRIS_REPAIR_QCODE": "SRC005",
        "IRIS_REPAIR": "M11",
        "IN_OUT_WTY": "OW"
    }


    data_atual = now_local.strftime('%d/%m/%Y')
    hora_atual = now_local.strftime('%H:%M:%S')


    # 4. Construir Payload Modificado
    payload_modificado = []
    campo_asc_job_no_encontrado = False
    campo_wty_exception_encontrado = False
    print('Atualizando payload...')
    payload_atualizado = montar_payload(numero_os) # Atualiza o payload com os dados mais recentes
    payload_original = payload_atualizado.get('payload_os_full') # Obtém o payload atualizadoS
    for key, original_value in payload_original:
        final_value = original_value # Valor padrão é o original

        # Aplica modificações fixas
        if key in modificacoes_fixas:
            final_value = modificacoes_fixas[key]
            print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
        # Aplica data/hora
        elif key == "SERVICE_DATE":
            final_value = data_atual
            print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
        elif key == "SERVICE_TIME":
            final_value = hora_atual
            print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
        # Aplica regra WTY_EXCEPTION
        elif key == "WTY_EXCEPTION":
            campo_wty_exception_encontrado = True
            if not original_value: # Se o valor original for vazio ou None
                final_value = "VOID3"
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}' (era vazio)")
            else:
                final_value = original_value # Mantém se não era vazio
        # Aplica regra ASC_JOB_NO
        elif key == "ASC_JOB_NO":
            campo_asc_job_no_encontrado = True
            # Verifica condição: (inicia com '3' e tem 6 dígitos) OU (inicia com 'FG' e tem 8 dígitos)
            if (original_value and isinstance(original_value, str) and
                    ((original_value.startswith('3') and len(original_value) == 6 and original_value.isdigit()) or \
                     (original_value.startswith('FG') and len(original_value) == 8))):
                final_value = numero_os
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}' (condição atendida)")
            else:
                final_value = original_value # Mantém se a condição não for atendida
                print(f"  Mantendo {key}: '{original_value}' (condição NÃO atendida)")

        # Adiciona a tupla (chave, valor_final) à nova lista
        payload_modificado.append((key, final_value))

    # Verificações de segurança (se campos chave para regras foram encontrados)
    if not campo_asc_job_no_encontrado:
         print("Aviso: Campo 'ASC_JOB_NO' não encontrado no payload base.")
    if not campo_wty_exception_encontrado:
         print("Aviso: Campo 'WTY_EXCEPTION' não encontrado no payload base.")

    # 5. Preparar e Enviar Requisição
    target_url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    # Constrói o Referer dinamicamente
    referer_url = f"https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID={numero_os}"

    headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Prototype-Version': '1.7.2', # Presente na requisição de exemplo
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': referer_url,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        'Sec-Fetch-Site': 'same-origin',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Dest': 'empty',
        # sec-ch-* headers omitidos, adicione se necessário
    }

    try:
        print("\nEnviando requisição para fechar OS sem reparo...")
        response = requests.post(
            target_url,
            headers=headers,
            cookies=cookies,
            data=payload_modificado,
            verify=False 
        )
        print(f"Status Code Fechamento: {response.status_code}")
        response.raise_for_status() # Verifica erro HTTP

        # 6. Processar Resposta
        try:
            # Limpa a resposta (similar à função de confirmação)
            response_text_clean = response.text.strip()
            if response_text_clean and response_text_clean[0] != '{':
                 json_start_index = response_text_clean.find('{')
                 if json_start_index != -1:
                      response_text_clean = response_text_clean[json_start_index:]
                 if response_text_clean.endswith('\n0'):
                     response_text_clean = response_text_clean[:-2].strip()

            fechamento_data = json.loads(response_text_clean)
            print(f"Resposta do Fechamento (JSON): {fechamento_data}")

            # Verifica sucesso
            if fechamento_data.get("success") is True:
                print(f"Fechamento da OS {numero_os} bem-sucedido!")
                return True
            else:
                print(f"Falha no fechamento indicada pela resposta: {fechamento_data.get('returnMessage', 'Sem mensagem de erro')}")
                return False

        except json.JSONDecodeError as json_err:
            print(f"Erro ao decodificar JSON da resposta de fechamento: {json_err}")
            print(f"Texto da resposta recebida: {response.text}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição de fechamento: {req_err}")
        if hasattr(req_err, 'response') and req_err.response is not None:
                print(f"Response Status: {req_err.response.status_code}")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante o fechamento da OS: {e}")
        return False




def aplicar_produto_entregue(numero_os):
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
    dados_full = montar_payload(numero_os)
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
        if key == "STATUS":
            final_value = "ST040"
            if original_value != final_value:
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                modificacoes_feitas += 1
        elif key == "SERVICE_DATE":
            final_value = data_atual
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        elif key == "SERVICE_TIME":
            final_value = hora_atual
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1

        # Adiciona a tupla (chave, valor_final) à nova lista
        payload_modificado.append((key, final_value))

    if modificacoes_feitas < 3:
        print("Aviso: Um ou mais campos ('STATUS', 'SERVICE_DATE', 'SERVICE_TIME') não foram encontrados ou já tinham o valor desejado no payload base.")

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

def mudar_pra_ow(dados_full):
    """
    Modifica uma Ordem de Serviço (OS) para Out Of Warranty (OW)
    e define a exceção como VOID3 no portal GSPN.

    Args:
        numero_os (str): O número da Ordem de Serviço a ser modificada.

    Returns:
        bool: True se a requisição foi enviada e a resposta indica sucesso,
              False caso contrário.
    """
    numero_os = dados_full.get('object_id')
    print(f'numero_os: {numero_os}')
    print(f"\n=== Iniciando Modificação para OW/VOID3 para OS: {numero_os} ===")

    # 1. Obter Cookies
    cookies = dados_full.get('cookies')
    if not cookies:
        print("Falha na modificação: Não foi possível obter cookies.")
        return False

    # 2. Obter Payload Base
    # Substitua 'montar_payload' pela sua função real!
    payload = montar_payload(numero_os)
    payload_original = payload.get('payload_os_full')
    if not payload_original:
        print(f"Falha na modificação: Não foi possível montar o payload base para a OS {numero_os}.")
        return False

    # 3. Construir Payload Modificado
    payload_modificado = []
    modificacoes_feitas = 0

    for key, original_value in payload_original:
        final_value = original_value # Valor padrão é o original

        # Aplica modificações necessárias
        if key == "IN_OUT_WTY":
            final_value = "OW"
            if original_value != final_value:
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                modificacoes_feitas += 1
        elif key == "WTY_EXCEPTION":
            final_value = "VOID3"
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1

        # Adiciona a tupla (chave, valor_final) à nova lista
        payload_modificado.append((key, final_value))

    if modificacoes_feitas == 0:
        print("Aviso: Nenhum dos campos ('IN_OUT_WTY', 'WTY_EXCEPTION') precisou ser modificado (ou não foram encontrados). Enviando mesmo assim.")
    elif modificacoes_feitas < 2:
        print("Aviso: Apenas um dos campos ('IN_OUT_WTY', 'WTY_EXCEPTION') foi modificado.")


    # 4. Preparar e Enviar Requisição
    target_url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    # Constrói o Referer dinamicamente (igual ao das funções anteriores)
    referer_url = f"https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID={numero_os}"

    # Headers (baseados na requisição de fechamento - ajustar se necessário)
    # Assumindo que a estrutura da requisição de modificação é a mesma
    headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'X-Prototype-Version': '1.7.2', # Presente na requisição de exemplo
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
        print("\nEnviando requisição para modificar OS para OW/VOID3...")
        response = requests.post(
            target_url,
            headers=headers,
            cookies=cookies,
            data=payload_modificado, # Envia a lista de tuplas modificada
            verify=False # Desabilita verificação de SSL (não recomendado em produção)
        )
        print(f"Status Code Modificação OW: {response.status_code}")
        response.raise_for_status() # Verifica erro HTTP

        # 5. Processar Resposta
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
            print(f"Resposta da Modificação OW (JSON): {modificacao_data}")

            # Verifica sucesso
            if modificacao_data.get("success") is True:
                print(f"Modificação da OS {numero_os} para OW/VOID3 bem-sucedida!")
                return True
            else:
                print(f"Falha na modificação OW indicada pela resposta: {modificacao_data.get('returnMessage', 'Sem mensagem de erro')}")
                return False

        except json.JSONDecodeError as json_err:
            print(f"Erro ao decodificar JSON da resposta de modificação OW: {json_err}")
            print(f"Texto da resposta recebida: {response.text}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição de modificação OW: {req_err}")
        if hasattr(req_err, 'response') and req_err.response is not None:
                print(f"Response Status: {req_err.response.status_code}")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante a modificação OW da OS: {e}")
        return False


if __name__ == "__main__":
    dados_full = {"object_id": '4172821217'}  # Exemplo de dados_full
      # Exemplo de número de OS
    cookies_full = obter_cookies_validos_recentes()
    cookies = {cookie["name"]: cookie["value"] for cookie in cookies_full}
    dados_full['cookies'] = cookies

    sucesso = mudar_pra_ow(dados_full)
    if sucesso:
        print("Modificação para OW/VOID3 concluída com sucesso.")
    else:
        print("Falha na modificação para OW/VOID3.")


def muda_tecnico_gspn(numero_os):
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
    dados_full = montar_payload(numero_os)
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
            final_value = "6086039614"
            if original_value != final_value:
                print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                modificacoes_feitas += 1
        elif key == "sENGINEER":
            final_value = "6086039614"
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1
        """elif key == "SERVICE_TIME":
            final_value = hora_atual
            if original_value != final_value:
                 print(f"  Modificando {key}: '{original_value}' -> '{final_value}'")
                 modificacoes_feitas += 1"""

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