import requests
import os
import re  # Import regular expressions library
import json # Import JSON library
from login_gspn.cookies_manager import obter_cookies_validos_recentes
from datetime import datetime # Import datetime library
from automacoes.montar_payloads import montar_payload
from automacoes.cos.coletar_dados_cos import obter_os_correspondentes

def pre_upload_anexos(upload_info, cookies):
    """
    Realiza o upload sequencial de arquivos PDF para o portal Samsung GSPN,
    extrai o nome do arquivo no servidor e retorna um mapeamento.

    Args:
        upload_info (dict): Um dicionário contendo:
            'object_id': (str) O ID do objeto.
            'OFF FOTA': (bool) True para fazer upload de 'Anexos/OFF FOTA.pdf'.
            'SERIAL FOTA': (bool) True para fazer upload de 'Anexos/SERIAL FOTA.pdf'.
            'SN LABEL FOTA': (bool) True para fazer upload de 'Anexos/SN LABEL FOTA.pdf'.

    Returns:
        dict or None: Um dicionário mapeando o nome original do arquivo para o nome
                      atribuído pelo servidor (e.g., {'OFF FOTA.pdf': 'OFF FOTA1.pdf'}).
                      Retorna None se ocorrer um erro crítico (ex: falha ao obter cookies).
                      Pode retornar um dicionário parcial se alguns uploads falharem.
    """
    # 1. Obter cookies internamente

    if not cookies:
        print("Falha no upload: Não foi possível obter cookies.")
        return None # Indica falha crítica

    # 2. Validar e extrair informações do argumento
    object_id = upload_info.get('object_id')
    if not object_id:
        print("Falha no upload: 'object_id' não fornecido no dicionário.")
        return None

    # Mapeamento das chaves para nomes de arquivo e flags
    arquivos_para_upload = {
        "OFF FOTA": upload_info.get("OFF FOTA", False),
        "SERIAL FOTA": upload_info.get("SERIAL FOTA", False),
        "SN LABEL FOTA": upload_info.get("SN LABEL FOTA", False),
    }

    # Pasta base para os anexos
    pasta_anexos = "Anexos"

    # URL e Headers (constantes)
    upload_url = "https://biz6.samsungcsportal.com/gspn/operate.do?cmd=AttachFileMultiUploadCmd"
    headers = {
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/SVCPopAttachMulti.jsp',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
    }

    # Dados do formulário (constantes)
    payload_data = {
        'objectId': object_id,
        'cmd': '',
        'returnFunctionName': 'uploadSuccessBufferV2',
    }

    # Dicionário para armazenar os resultados (nome original -> nome servidor)
    resultados_upload = {}

    # Regex para encontrar o JSON na resposta HTML
    # Captura o conteúdo entre as aspas simples de var responseJson = '...'
    json_pattern = re.compile(r"var\s+responseJson\s*=\s*'({.*?})';")

    # 3. Iterar e fazer upload
    for nome_chave, deve_enviar in arquivos_para_upload.items():
        if deve_enviar:
            nome_arquivo_pdf = f"{nome_chave}.pdf"
            pdf_file_path = os.path.join(pasta_anexos, nome_arquivo_pdf)

            if not os.path.exists(pdf_file_path):
                print(f"Erro: Arquivo '{nome_arquivo_pdf}' não encontrado em '{pasta_anexos}'. Upload pulado.")
                continue # Pula para o próximo arquivo

            # --- Upload do arquivo ---
            try:
                with open(pdf_file_path, 'rb') as f:
                    files_data = {
                        'uploadFile': (nome_arquivo_pdf, f, 'application/pdf')
                    }

                    print(f"\n--- Iniciando upload de '{nome_arquivo_pdf}' para objectId '{object_id}' ---")
                    response = requests.post(
                        upload_url,
                        headers=headers,
                        cookies=cookies,
                        data=payload_data,
                        files=files_data,
                        verify=False # Envia apenas o arquivo atual
                    )
                    print(f"Status Code: {response.status_code}")
                    response.raise_for_status() # Verifica erro HTTP

                    # --- Processamento da Resposta ---
                    response_text = response.text
                    match = json_pattern.search(response_text)

                    if match:
                        json_string = match.group(1) # Pega o conteúdo capturado (o JSON)
                        try:
                            parsed_json = json.loads(json_string)
                            # Verifica se o JSON indica sucesso e contém as informações
                            if parsed_json.get("success") and isinstance(parsed_json.get("fileInfo"), dict):
                                file_info = parsed_json["fileInfo"]
                                server_filename = file_info.get("fileName")
                                original_filename = file_info.get("fileNameOrg") # Pega nome original para confirmação

                                if server_filename and original_filename == nome_arquivo_pdf:
                                    print(f"Upload de '{nome_arquivo_pdf}' bem-sucedido.")
                                    print(f"  -> Nome no servidor: '{server_filename}'")
                                    resultados_upload[nome_arquivo_pdf] = server_filename
                                else:
                                    print(f"Erro: JSON de resposta para '{nome_arquivo_pdf}' não contém 'fileName' esperado ou 'fileNameOrg' não confere.")
                                    print(f"  JSON: {parsed_json}")
                            else:
                                print(f"Erro: JSON de resposta para '{nome_arquivo_pdf}' não indica sucesso ou falta 'fileInfo'.")
                                print(f"  JSON: {parsed_json}")

                        except json.JSONDecodeError as json_err:
                            print(f"Erro ao decodificar JSON da resposta para '{nome_arquivo_pdf}': {json_err}")
                            print(f"  Texto JSON extraído (pode estar incompleto): {json_string[:200]}...")
                    else:
                        print(f"Erro: Não foi possível encontrar o JSON na resposta HTML para '{nome_arquivo_pdf}'.")
                        # print(f"  Início da resposta: {response_text[:500]}") # Descomente para depurar

            except FileNotFoundError:
                 print(f"Erro interno (inesperado): Arquivo '{nome_arquivo_pdf}' não encontrado em '{pasta_anexos}'.")
            except requests.exceptions.RequestException as req_err:
                print(f"Erro na requisição para '{nome_arquivo_pdf}': {req_err}")
                if hasattr(req_err, 'response') and req_err.response is not None:
                     print(f"Response Status: {req_err.response.status_code}")
            except Exception as e:
                print(f"Um erro inesperado ocorreu durante o upload de '{nome_arquivo_pdf}': {e}")
        else:
            print(f"Arquivo '{nome_chave}.pdf' não será enviado (flag=False).")

    print("\n--- Resumo dos Uploads ---")
    if resultados_upload:
        print("Mapeamento (Nome Original -> Nome Servidor):")
        for original, servidor in resultados_upload.items():
            print(f"  '{original}': '{servidor}'")
    else:
        print("Nenhum upload foi concluído com sucesso ou nenhum arquivo foi solicitado.")

    return resultados_upload


def upload_anexos(upload_info):
    """
    Envia a requisição de confirmação para os arquivos que foram upados com sucesso.

    Args:
        upload_info (dict): O mesmo dicionário passado para upload_arquivos_samsung.

    Returns:
        bool: True se a requisição de confirmação foi enviada e retornou sucesso,
              False caso contrário.
    """
    print("\n=== Iniciando Processo de Confirmação ===")
    cookies = obter_cookies_validos_recentes()
    #cookies = {cookie["name"]: cookie["value"] for cookie in cookies_full}
    # 1. Chamar a função de upload para obter o mapeamento
    resultados_upload = pre_upload_anexos(upload_info, cookies)

    # Verifica se houve algum upload bem-sucedido
    if not resultados_upload: # Se for None ou {}
        print("Confirmação cancelada: Nenhum arquivo foi carregado com sucesso na etapa anterior.")
        return False

    object_id = upload_info.get('object_id')
    if not object_id:
        print("Confirmação cancelada: 'object_id' não encontrado.")
        return False # Deveria ter sido pego antes, mas verificamos de novo

    if not cookies:
        print("Falha na confirmação: Não foi possível obter cookies.")
        return False

    # 3. Preparar Payload da Confirmação
    pasta_anexos = "Anexos"
    confirm_url = "https://biz6.samsungcsportal.com/gspn/operate.do" # URL base para a confirmação [cite: 1]

    # Mapeamento Fixo de Nome Original para IV_DESC (Categoria)
    # Baseado na ordem e nomes do arquivo de exemplo 'requisição confirmar upload.txt'
    iv_desc_map = {
        "OFF FOTA.pdf": "ATT03",
        "SERIAL FOTA.pdf": "ATT02",
        "SN LABEL FOTA.pdf": "ATT01"
    }

    # Ordem Preservada dos Arquivos para o Payload da Confirmação
    ordem_arquivos = ["OFF FOTA.pdf", "SERIAL FOTA.pdf", "SN LABEL FOTA.pdf"]

    # Lista de tuplas para manter a ordem e chaves duplicadas
    payload_list = [
        ('objectId', object_id),
        ('cmd', 'AttachFileMultiUploadSvcCmd'), # Comando da confirmação [cite: 2]
        ('returnFunctionName', 'uploadSuccessBufferV2') # Mesmo da requisição anterior
    ]

    # Data atual formatada
    data_atual = datetime.now().strftime('%d/%m/%Y') # Formato dd/MM/yyyy

    # Adiciona os dados de cada arquivo *que foi upado com sucesso* na ordem correta
    for nome_original in ordem_arquivos:
        if nome_original in resultados_upload:
            nome_servidor = resultados_upload[nome_original]
            iv_desc = iv_desc_map.get(nome_original)
            caminho_original = os.path.join(pasta_anexos, nome_original)

            if not iv_desc:
                print(f"Aviso: Categoria IV_DESC não mapeada para '{nome_original}'. Pulando confirmação deste arquivo.")
                continue

            try:
                tamanho_arquivo = os.path.getsize(caminho_original)
            except FileNotFoundError:
                print(f"Erro crítico: Arquivo original '{nome_original}' não encontrado para obter tamanho na confirmação. Pulando.")
                continue
            except Exception as e:
                 print(f"Erro ao obter tamanho de '{nome_original}': {e}. Pulando confirmação deste arquivo.")
                 continue

            # Adiciona o bloco de parâmetros para este arquivo
            payload_list.extend([
                ('IV_DESC', iv_desc),
                ('file_name', nome_servidor),
                ('file_name_org', nome_original),
                ('file_type', 'application/pdf'),
                ('file_size', str(tamanho_arquivo)), # Convertido para string
                ('create_date', data_atual), # Usando data atual
                ('file_type2', '.pdf')
            ])
            print(f"Adicionando dados de confirmação para: {nome_original} (IV_DESC={iv_desc}, Size={tamanho_arquivo}, ServerName={nome_servidor})")

    # Se nenhum arquivo foi adicionado ao payload de confirmação (improvável se resultados_upload não era vazio, mas seguro verificar)
    if len(payload_list) <= 3: # Apenas objectId, cmd, returnFunctionName
         print("Nenhum arquivo válido para adicionar ao payload de confirmação.")
         return False

    # Cabeçalhos para a requisição de confirmação [cite: 1, 2]
    confirm_headers = {
        'Content-type': 'application/x-www-form-urlencoded; charset=UTF-8', # Específico desta requisição
        'X-Requested-With': 'XMLHttpRequest', # Indica requisição AJAX
        'Origin': 'https://biz6.samsungcsportal.com',
        'Referer': 'https://biz6.samsungcsportal.com/svctracking/svcorder/SVCPopAttachMulti.jsp',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0',
        'Accept': 'text/javascript, text/html, application/xml, text/xml, */*', # Aceita tipos comuns de AJAX
        'Accept-Language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Accept-Encoding': 'gzip, deflate, br, zstd',
        # Outros cabeçalhos como sec-ch-* não parecem necessários aqui
    }

    # 4. Enviar requisição de confirmação
    try:
        print("\nEnviando requisição de confirmação...")
        # 'data' recebe a lista de tuplas para preservar ordem e duplicatas
        confirm_response = requests.post(
            confirm_url,
            headers=confirm_headers,
            cookies=cookies,
            data=payload_list,
            verify=False # Desabilitado para evitar problemas de SSL (não recomendado em produção)
        )
        print(f"Status Code Confirmação: {confirm_response.status_code}")
        confirm_response.raise_for_status() # Verifica erro HTTP

        # 5. Processar resposta da confirmação
        try:
            # Remove os caracteres não JSON do início/fim se presentes
            # (Ex: "42\n" no início e "\n0" no fim)
            response_text_clean = confirm_response.text.strip()
            if response_text_clean and response_text_clean[0] != '{':
                 # Tenta remover linhas extras do início
                 json_start_index = response_text_clean.find('{')
                 if json_start_index != -1:
                      response_text_clean = response_text_clean[json_start_index:]
                 # Remove o \n0 ou similar do fim, se houver
                 if response_text_clean.endswith('\n0'):
                     response_text_clean = response_text_clean[:-2].strip()


            confirm_data = json.loads(response_text_clean)
            print(f"Resposta da Confirmação (JSON): {confirm_data}")

            # Verifica sucesso (pode usar 'success' ou 'returnCode')
            if confirm_data.get("success") is True:
                print("Confirmação bem-sucedida!")
                return True
            else:
                print(f"Falha na confirmação indicada pela resposta: {confirm_data.get('returnMessage', 'Sem mensagem de erro')}")
                return False

        except json.JSONDecodeError as json_err:
            print(f"Erro ao decodificar JSON da resposta de confirmação: {json_err}")
            print(f"Texto da resposta recebida: {confirm_response.text}")
            return False

    except requests.exceptions.RequestException as req_err:
        print(f"Erro na requisição de confirmação: {req_err}")
        if hasattr(req_err, 'response') and req_err.response is not None:
                print(f"Response Status: {req_err.response.status_code}")
        return False
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante a confirmação: {e}")
        return False


def checar_e_anexar_obrigatorios(os_gspn):
    """
    Verifica se as categorias de anexo obrigatórias (ATT01, ATT02, ATT03)
    estão presentes no payload e, se não estiverem, chama a função
    para anexar os arquivos correspondentes.

    Args:
        payload_original (list): A lista de tuplas [(key, value), ...]
                                 representando o payload onde verificar os anexos.
        numero_os (str): O número da OS (ObjectID) a ser usado nos uploads.

    Returns:
        dict or None: O dicionário de mapeamento retornado por
                      upload_arquivos_samsung (pode ser vazio se nenhum
                      upload foi necessário ou se todos falharam), ou None
                      se a função de upload falhar criticamente (ex: cookies).
                      Retorna {} se todos os anexos já estavam presentes.
    """
    if len(os_gspn) == 6:
        os_temp = obter_os_correspondentes(os_gspn)
        os_gspn = os_temp
    numero_os = os_gspn # O número da OS (ObjectID) a ser usado nos uploads
    #numero_os = dados_full.get("object_id") # O número da OS (ObjectID) a ser usado nos uploads
    dados = montar_payload(numero_os)
    payload_original = dados.get("payload_os_full") # O payload original a ser verificado
     # Monta o payload original para verificar anexos
    print(f"\n=== Verificando Anexos Obrigatórios para OS: {numero_os} ===")

    if not payload_original or not numero_os:
        print("Erro: Payload original ou número da OS inválido.")
        return {} # Retorna vazio indicando que nada foi feito

    # 1. Definir categorias obrigatórias
    categorias_obrigatorias = {"ATT01", "ATT02", "ATT03"}

    # 2. Encontrar categorias presentes no payload
    categorias_presentes = set()
    for key, value in payload_original:
        if key == "docTypeCode":
            if value: # Garante que o valor não seja vazio
                categorias_presentes.add(value)

    print(f"Categorias obrigatórias: {categorias_obrigatorias}")
    print(f"Categorias encontradas no payload: {categorias_presentes}")

    # 3. Determinar categorias faltantes
    categorias_faltantes = categorias_obrigatorias - categorias_presentes
    print(f"Categorias faltantes: {categorias_faltantes if categorias_faltantes else 'Nenhuma'}")

    # 4. Se nada estiver faltando, encerrar
    if not categorias_faltantes:
        print("Todos os anexos obrigatórios (ATT01, ATT02, ATT03) já estão presentes.")
        return {} # Retorna dicionário vazio indicando que nenhuma ação de upload foi necessária

    # 5. Preparar para anexar os faltantes
    print("Iniciando processo para anexar categorias faltantes...")

    # Mapeamento de Categoria para Chave da Flag de Upload e Nome do Arquivo
    mapa_categorias = {
        "ATT01": {"flag": "OFF FOTA", "arquivo": "OFF FOTA.pdf"},
        "ATT02": {"flag": "SERIAL FOTA", "arquivo": "SERIAL FOTA.pdf"},
        "ATT03": {"flag": "SN LABEL FOTA", "arquivo": "SN LABEL FOTA.pdf"}
    }

    # Cria o dicionário de informações para a função de upload
    upload_info = {
        "object_id": numero_os,
        "OFF FOTA": False,
        "SERIAL FOTA": False,
        "SN LABEL FOTA": False,
    }

    pasta_anexos = "Anexos"
    pelo_menos_um_arquivo_existe = False

    # Define as flags como True para as categorias faltantes e verifica se o arquivo existe
    for categoria in categorias_faltantes:
        if categoria in mapa_categorias:
            info_cat = mapa_categorias[categoria]
            chave_flag = info_cat["flag"]
            nome_arquivo = info_cat["arquivo"]
            caminho_arquivo = os.path.join(pasta_anexos, nome_arquivo)

            if os.path.exists(caminho_arquivo):
                print(f"  - Categoria {categoria} faltante. Marcando '{chave_flag}' para upload (Arquivo: {nome_arquivo}).")
                upload_info[chave_flag] = True
                pelo_menos_um_arquivo_existe = True
            else:
                print(f"  - Categoria {categoria} faltante, MAS o arquivo '{nome_arquivo}' NÃO foi encontrado em '{pasta_anexos}'. Upload não será tentado.")
        else:
            print(f"Aviso: Categoria obrigatória faltante '{categoria}' não possui mapeamento conhecido.")

    # 6. Chamar a função de upload apenas se houver algo a ser enviado e o arquivo existir
    if pelo_menos_um_arquivo_existe:
        print(f"\nChamando upload_arquivos_samsung com a seguinte configuração: {upload_info}")
        # Chama a função que realmente faz o upload (usando a versão das etapas anteriores)
        # Esta função já lida com cookies internamente e retorna o mapeamento
        resultados_novos_uploads = upload_anexos(upload_info)
        if resultados_novos_uploads:
            print("Upload de anexos faltantes concluído com sucesso.")
            return True

        else:
            print("Falha ao fazer upload de anexos faltantes.")
            return {}
    else:
        print("\nNenhuma categoria faltante tinha seu arquivo correspondente disponível para upload.")
        return True # Retorna True indicando que não houve necessidade de upload, mas não falhou