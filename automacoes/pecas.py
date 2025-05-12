import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
from automacoes.cos.coletar_dados_cos import coletar_usadas_cos
from flask_socketio import SocketIO, emit
from flask import Flask
import requests
import json
from urllib.parse import quote
from datetime import datetime
from coletar_dados import fetch_os_data, extract_os_data_full, coletar_usadas_cos, consultar_estoque_tecnico, confere_qtd_pecas, comparar_pecas_os, consultar_delivery
from multiprocessing import Queue
from montar_payloads import pl_deletar_pecas
from bs4 import BeautifulSoup
import logging
import urllib3
from montar_payloads import montar_payload
# Desabilitar avisos de SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

#app = Flask(__name__)
#socketio = SocketIO(app, cors_allowed_origins="*")

def configurar_logger(object_id=None):
    """
    Configura um logger específico para o object_id fornecido.
    
    Args:
        object_id (str, optional): Identificador da OS. Se None, usa um log genérico.
    
    Returns:
        logging.Logger: Logger configurado.
    """
    logger = logging.getLogger(f"gspn_sync_{object_id}" if object_id else "gspn_sync")
    if logger.handlers:  # Evita duplicação de handlers
        return logger
    
    logger.setLevel(logging.DEBUG)  # Nível mínimo do logger
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    # Handler para console (apenas INFO e superior)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Exibe apenas INFO, WARNING, ERROR, etc.
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para arquivo (DEBUG e superior)
    log_filename = f"C:\\Users\\Gestão MX\\Documents\\AutoMX\\logs\\sincronizar_pecas_detalhado_{object_id}.log" if object_id else "C:\\Users\\Gestão MX\\Documents\\AutoMX\\logs\\sincronizar_pecas_detalhado.log"
    file_handler = logging.FileHandler(log_filename, mode='a')
    file_handler.setLevel(logging.DEBUG)  # Grava DEBUG e superior
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger

def send_progress(queue, os_gspn, step, status, sid, error=None):
    """
    Envia atualização de progresso para o frontend via queue, garantindo a mesma estrutura do módulo original.
    
    Args:
        queue (Queue): Fila de mensagens para comunicação com o módulo main.
        os_gspn (str): Número da OS.
        step (str): Etapa atual do processo.
        status (str): Status da etapa ('running', 'completed', 'failed').
        sid (str): ID da sessão do socketio (garante a correta emissão dos eventos).
        error (str, optional): Mensagem de erro, se houver.
    """
    # Garantir que os dados enviados seguem o mesmo formato do módulo original
    progress_data = {
        'os': os_gspn,
        'step': step,
        'status': status,
        'sid': sid
    }
    #for key in progress_data:
        #print(f'{key}: {progress_data[key]}')  # Debug: imprime cada chave e valor
    
    # Se houver erro, garantir que a chave 'error' esteja presente (mantendo o formato do original)
    #if error:
    #    progress_data['error'] = error

    # Certificar-se de que não há valores None no dicionário
    #progress_data = {k: v for k, v in progress_data.items() if v is not None}

    queue.put(progress_data)
    
def create_headers(endpoint_url=None, content_type="application/x-www-form-urlencoded; charset=UTF-8"):
    """
    Cria headers HTTP padronizados para requisições ao GSPN.
    
    Args:
        endpoint_url (str, optional): URL específica para Referer. Se None, usa o endpoint padrão.
        content_type (str, optional): Content-Type para a requisição.
        
    Returns:
        dict: Headers HTTP padronizados.
    """
    # URL base para referer
    base_url = "https://biz6.samsungcsportal.com"
    referer = endpoint_url if endpoint_url else f"{base_url}/gspn/operate.do"
    
    return {
        "Host": "biz6.samsungcsportal.com",
        "Connection": "keep-alive",
        "X-Prototype-Version": "1.7.2",
        "sec-ch-ua-platform": "Windows",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Microsoft Edge\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Content-type": content_type,
        "Origin": base_url,
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": referer,
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
    }

def inserir_pecas_gspn(dados_full):
    """
    Monta o payload e insere/atualiza peças e deliveries na OS no GSPN.
    Atualiza blocos existentes e adiciona apenas os blocos faltantes.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    logger.info("Iniciando a função inserir_pecas_gspn")
    #logger.debug(f"Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")

    try:
        object_id = dados_full['object_id']
        logger.info("Consultando delivery")
        dados_full.update(consultar_delivery(dados_full))
        #logger.debug(f"Estado de dados_full após consultar_delivery: {json.dumps(dados_full, indent=2, default=str)}")

        logger.info("Montando o payload inicial (se necessário)")
        # Assume que montar_payload retorna 'payload_os_full' e 'parts_to_add'
        if 'payload_os_full' not in dados_full or 'parts_to_add' not in dados_full:
             try:
                 dados_full.update(montar_payload(object_id))
                 #logger.debug(f"Estado de dados_full após montar_payload: {json.dumps(dados_full, indent=2, default=str)}")
             except Exception as e:
                 logger.error(f"Erro ao montar payload: {e}")
                 logger.debug(f"Estado de dados_full após falha no passo 1: {json.dumps(dados_full, indent=2, default=str)}")
                 print(f'Erro ao montar payload: {e}')
                 return False # Não pode continuar sem payload

        logger.info("Extraindo dados necessários")
        cookies = dados_full.get('cookies', {}) # Adiciona um fallback
        parts_to_add = dados_full.get('parts_to_add', [])
        delivery_resultados = dados_full.get('delivery_resultados', [])
        payload_original = dados_full.get('payload_os_full', [])

        if not payload_original:
            logger.warning("Payload original está vazio ou ausente.")
            # Poderia decidir parar ou tentar criar um payload do zero aqui
            # return False # Ou adaptar a lógica para criar tudo novo

        # Estrutura base de um bloco de peça (mantida)
        bloco_base = [
            ("PARTS_SEQ_NO", ""), ("SHIP_DATE", ""), ("OLD_PARTS_SEQ_NO", ""),
            ("OLD_SHIP_DATE", ""), ("REPAIR_LOC", ""), ("PROACTIVE_FLAG", ""),
            ("PARTS_STATUS", ""), ("ORG_PARTS_CODE", ""), ("PARTS_CODE", ""),
            ("PARTS_DESC", ""), ("INVOICE_NO", ""), ("INVOICE_ITEM_NO", ""),
            ("PARTS_QTY", ""), ("D_REQUEST_NO", ""), ("REQUEST_NO", ""),
            ("REQUEST_ITEM_NO", ""), ("PO_NO", ""), ("SO_NO", ""),
            ("SO_ITEM_NO", ""), ("D_SO_NO", ""), ("OLD_SERIAL_MAT", ""),
            ("SERIAL_MAT", ""), ("OLD_FAB_ID", ""), ("FAB_ID", ""),
            ("PARTS_INOUT", ""), ("GI_DATE", ""), ("gi_document_no", ""),
        ]

        payload_final = []
        codigos_pecas_existentes = set()
        bloco_atual = None
        processando_bloco = False

        logger.info("Processando payload original e atualizando blocos existentes...")
        for i, tupla in enumerate(payload_original):
            campo, valor = tupla

            if campo == "PARTS_SEQ_NO":
                # Início de um bloco de peça
                if bloco_atual is not None:
                    logger.warning(f"Encontrado novo PARTS_SEQ_NO sem fim do bloco anterior. Bloco anterior: {bloco_atual}")
                    # Decide como lidar: talvez adicionar o bloco anterior mesmo assim?
                    # payload_final.extend(bloco_atual) # Opção: Adiciona o bloco anterior incompleto
                bloco_atual = [tupla]
                processando_bloco = True
                continue # Pula para a próxima iteração

            if processando_bloco:
                bloco_atual.append(tupla)
                if campo == "gi_document_no":
                    # Fim de um bloco de peça
                    parts_code = next((item[1] for item in bloco_atual if item[0] == "PARTS_CODE"), None)
                    gi_date = next((item[1] for item in bloco_atual if item[0] == "GI_DATE"), "")

                    if not parts_code:
                        logger.warning(f"Bloco de peça terminado em gi_document_no sem PARTS_CODE: {bloco_atual}")
                        # Adiciona o bloco como está, pois não podemos processá-lo sem código
                        payload_final.extend(bloco_atual)
                    else:
                        codigos_pecas_existentes.add(parts_code) # Registra que esta peça existe
                        #logger.debug(f"Processando bloco existente para PARTS_CODE: {parts_code}, GI_DATE: '{gi_date}'")

                        # Verifica se precisa atualizar delivery (GI_DATE vazia ou padrão "nulo")
                        if not gi_date or gi_date == "00/00/0000" or gi_date.strip() == "":
                            delivery_info = next((d for d in delivery_resultados if d.get("codigo") == parts_code), None)
                            if delivery_info:
                                logger.info(f"Atualizando delivery para PARTS_CODE {parts_code} no bloco existente.")
                                bloco_modificado = []
                                for item_campo, item_valor in bloco_atual:
                                    if item_campo == "INVOICE_NO":
                                        bloco_modificado.append((item_campo, delivery_info.get("delivery", "")))
                                    elif item_campo == "INVOICE_ITEM_NO":
                                        bloco_modificado.append((item_campo, delivery_info.get("item_no", "")))
                                    else:
                                        bloco_modificado.append((item_campo, item_valor))
                                payload_final.extend(bloco_modificado)
                            else:
                                # Nenhuma informação de delivery encontrada, adiciona o bloco como está
                                logger.debug(f"Nenhuma informação de delivery para {parts_code}, mantendo bloco original.")
                                payload_final.extend(bloco_atual)
                        else:
                            # GI_DATE preenchida, não atualiza delivery, adiciona o bloco como está
                            #logger.debug(f"GI_DATE preenchida para {parts_code}, mantendo bloco original.")
                            payload_final.extend(bloco_atual)

                    # Reseta para o próximo bloco
                    bloco_atual = None
                    processando_bloco = False
            else:
                # Tupla fora de um bloco de peça, apenas adiciona ao payload final
                payload_final.append(tupla)

        # Caso o último bloco não tenha terminado com 'gi_document_no' (payload malformado?)
        if bloco_atual is not None:
             logger.warning(f"Payload terminou dentro de um bloco de peça não finalizado: {bloco_atual}")
             payload_final.extend(bloco_atual) # Adiciona o bloco restante

        logger.info("Adicionando blocos para peças faltantes de parts_to_add...")
        novos_blocos_adicionados = 0
        for parte in parts_to_add:
            codigo = parte.get("codigo")
            quantidade = parte.get("quantidade", "1") # Default para 1 se faltar

            if not codigo:
                logger.warning(f"Item em parts_to_add sem 'codigo': {parte}")
                continue

            if codigo not in codigos_pecas_existentes:
                logger.info(f"Peça {codigo} não encontrada no payload original. Criando novo bloco.")
                novos_blocos_adicionados += 1
                novo_bloco = []
                delivery_info = next((d for d in delivery_resultados if d.get("codigo") == codigo), None)

                # Monta o novo bloco a partir do template
                for campo_base, valor_base in bloco_base:
                    if campo_base == "PARTS_CODE":
                        novo_bloco.append((campo_base, codigo))
                    elif campo_base == "PARTS_QTY":
                        novo_bloco.append((campo_base, str(quantidade)))
                    elif campo_base == "PARTS_STATUS":
                        novo_bloco.append((campo_base, "P")) # Status padrão para peça nova? Ajuste se necessário
                    elif campo_base == "PARTS_INOUT":
                        novo_bloco.append((campo_base, "I")) # Padrão para entrada? Ajuste se necessário
                    elif campo_base == "INVOICE_NO" and delivery_info:
                        novo_bloco.append((campo_base, delivery_info.get("delivery", "")))
                    elif campo_base == "INVOICE_ITEM_NO" and delivery_info:
                        novo_bloco.append((campo_base, delivery_info.get("item_no", "")))
                    else:
                        # Mantém o valor padrão do bloco_base (geralmente vazio)
                        novo_bloco.append((campo_base, valor_base))

                # Adiciona o novo bloco ao final do payload
                # Idealmente, deveria ser inserido antes de algum campo final,
                # mas adicionar ao fim é mais simples e geralmente funciona.
                # Se a ordem exata for crítica, a lógica de inserção precisa ser mais complexa.
                payload_final.extend(novo_bloco)
                logger.debug(f"Novo bloco para {codigo} adicionado.")
                # print(f'Novo bloco adicionado para {codigo}:')
                # for key, value in novo_bloco:
                #     print(f'  {key}: {value}')

            else:
                logger.info(f"Peça {codigo} de parts_to_add já existe no payload. Bloco já foi atualizado (se aplicável).")

        logger.info(f"Processamento concluído. {len(codigos_pecas_existentes)} peças existentes processadas. {novos_blocos_adicionados} novas peças adicionadas.")
        # logger.debug(f"Payload final antes do envio: {json.dumps(payload_final, default=str)}") # Log pode ser muito grande
        print("--- Payload Final Gerado ---")
        # for key, value in payload_final:
        #      print(f'{key}: {value}') # Descomente para depuração detalhada


        # Cria o referer dinâmico com base no object_id
        referer = f"https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID={object_id}"
        headers = create_headers(referer)

        logger.info("Enviando payload atualizado para GSPN...")
        try:
            response = requests.post(
                "https://biz6.samsungcsportal.com/gspn/operate.do",
                headers=headers,
                cookies=cookies,
                data=payload_final, # Usa o payload reconstruído
                verify=False # Considere remover ou tratar a verificação SSL adequadamente
            )
            response.raise_for_status() # Levanta erro para status HTTP 4xx/5xx

            if '"success":true' in response.text:
                logger.info(f"Peças inseridas/atualizadas com sucesso para object_id {object_id}.")
                # logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}") # dados_full não foi modificado aqui
                return True
            else:
                try:
                    response_json = response.json
                    mensagem_de_erro = response_json.get("message")
                    return {"Erro": mensagem_de_erro}
                except:
                    mensagem_de_erro = response.text
                logger.error(f"Erro retornado pelo GSPN ao inserir/atualizar peças. Status: {response.status_code}, Resposta: {mensagem_de_erro}")
                # logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
                return {"Erro": mensagem_de_erro}
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição ao inserir/atualizar peças: {str(e)}")
            # logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
            return False

    except KeyError as e:
        logger.error(f"Erro: Chave obrigatória não encontrada em dados_full: {e}")
        print(f'Erro: Chave obrigatória não encontrada: {e}')
        return False
    except Exception as e:
        logger.exception(f"Erro inesperado na função inserir_pecas_gspn: {e}") # Usar exception para logar o traceback
        print(f'Erro inesperado ao inserir/atualizar peças: {e}')
        # logger.debug(f"Estado de dados_full no momento do erro: {json.dumps(dados_full, indent=2, default=str)}")
        return False


def sincronizar_pecas(os_gspn, sid, queue):
    """
    Sincroniza as peças entre COS, técnico e OS no GSPN, verificando condições com precisão.
    
    Args:
        os_gspn (str): Número da OS no GSPN.
        queue (Queue): Fila para comunicação com o frontend.
        sid (str): ID da sessão do socketio.
    
    Returns:
        bool: True se a sincronização for concluída com sucesso, False caso contrário.
    """
    print(f'sid da sessão: {sid}')
    dados_full = {"object_id": os_gspn}
    logger = configurar_logger(os_gspn)
    #logger.debug(f"Início da sincronização para OS {os_gspn}. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    #send_progress(queue, os_gspn, 'Iniciando', 'running', sid)
    
    try:
        # 1 - Baixa o HTML da OS
        logger.info(f"Passo 1: Baixando HTML da OS {os_gspn}")
        send_progress(queue, os_gspn, 'Carregando informações da OS', 'running', sid)
        try:
            resultado_fetch = fetch_os_data(os_gspn)
            dados_full.update(resultado_fetch)
            if not dados_full.get("html_os"):
                error_msg = f"Erro ao baixar OS: {dados_full.get('error', 'Erro desconhecido')}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Carregando informações da OS', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 1: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("HTML da OS baixado com sucesso")
        except Exception as e:
            error_msg = f"Erro ao baixar HTML da OS: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Carregando informações da OS', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 1: {json.dumps(dados_full, indent=2, default=str)}")
            return False
        
        #send_progress(queue, os_gspn, 'Carregando informações da OS', 'completed', sid)
        
        # 2 - Extrai dados da OS
        logger.info("Passo 2: Extraindo dados da OS")
        send_progress(queue, os_gspn, 'Extraindo dados', 'running', sid)
        try:
            resultado_extract = extract_os_data_full(dados_full)
            dados_full.update(resultado_extract)
            if "error" in dados_full:
                error_msg = f"Erro ao extrair dados da OS: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Extraindo dados', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 2: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Dados da OS extraídos com sucesso")
        except Exception as e:
            error_msg = f"Erro ao extrair dados da OS: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Extraindo dados', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 2: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'Extraindo dados', 'completed', sid)

        # 3 - Coleta peças do COS
        logger.info("Passo 3: Coletando peças do COS")
        send_progress(queue, os_gspn, 'Coletando peças do COS', 'running', sid)
        try:
            resultado_cos = coletar_usadas_cos(dados_full)
            dados_full.update(resultado_cos)
            if "error" in dados_full:
                error_msg = f"Erro ao coletar peças do COS: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Coletando peças do COS', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 3: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Peças do COS coletadas com sucesso")
        except Exception as e:
            error_msg = f"Erro ao coletar peças do COS: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Coletando peças do COS', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 3: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'Coletando peças do COS', 'completed', sid)

        # 4 - Compara peças da OS com COS
        logger.info("Passo 4: Comparando peças da OS com COS")
        send_progress(queue, os_gspn, 'Comparando peças', 'running', sid)
        try:
            resultado_comparar = comparar_pecas_os(dados_full)
            dados_full.update(resultado_comparar)
            if "error" in dados_full:
                error_msg = f"Erro ao comparar peças: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Comparando peças', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 4: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Comparação de peças concluída")
        except Exception as e:
            error_msg = f"Erro ao comparar peças: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Comparando peças', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 4: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'Comparando peças', 'completed', sid)

        # 5 - Consulta estoque do técnico
        logger.info("Passo 5: Consultando estoque do técnico")
        send_progress(queue, os_gspn, 'Consultando estoque do técnico', 'running', sid)
        try:
            resultado_tecnico = consultar_estoque_tecnico(dados_full)
            dados_full.update(resultado_tecnico)
            if "error" in dados_full:
                error_msg = f"Erro ao consultar estoque do técnico: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Consultando estoque do técnico', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 5: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Consulta ao estoque do técnico concluída")
        except Exception as e:
            error_msg = f"Erro ao consultar estoque do técnico: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Erro ao estoque do técnico', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 5: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'Consultando estoque do técnico', 'completed', sid)

        # 6 - Confere quantidades e consulta estoque ASC
        logger.info("Passo 6: Conferindo quantidades e consultando estoque ASC")
        send_progress(queue, os_gspn, 'Comparando peças COS / GSPN', 'running', sid)
        try:
            resultado_confere = confere_qtd_pecas(dados_full)
            dados_full.update(resultado_confere)
            if "error" in dados_full:
                error_msg = f"Erro ao conferir quantidades: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao comparar peças COS / GSPN', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 6: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Conferência de quantidades concluída")
        except Exception as e:
            error_msg = f"Erro ao conferir quantidades: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Erro ao comparar peças COS / GSPN', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 6: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'Comparação concluída', 'completed', sid)

        # 7 - Ajusta estoque ASC, se necessário
        if dados_full.get("asc_stock_adjustments") and dados_full["asc_stock_adjustments"]:
            logger.info("Passo 7: Ajustando estoque ASC")
            send_progress(queue, os_gspn, 'Ajustando quantidade em estoque', 'running', sid)
            try:
                resultado = ajustar_estq_asc(dados_full)
                if not resultado:
                    error_msg = f"Erro ao ajustar estoque ASC: {dados_full.get('error', 'Erro desconhecido')}"
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, 'Erro ao ajustar estoque', 'failed', sid, error_msg)
                    #logger.debug(f"Estado de dados_full após falha no passo 7: {json.dumps(dados_full, indent=2, default=str)}")
                    return False
                logger.info("Ajuste de estoque ASC concluído")
            except Exception as e:
                error_msg = f"Erro ao ajustar estoque ASC: {str(e)}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao ajustar estoque', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após erro no passo 7: {json.dumps(dados_full, indent=2, default=str)}")
                return False
                
            #send_progress(queue, os_gspn, 'Ajustando quantidade em estoque', 'completed', sid)

        # 8 - Solicita e transfere peças para o técnico, se necessário
        if dados_full.get("technician_stock_shortages") and dados_full["technician_stock_shortages"]:
            logger.info("Passo 8a: Solicitando peças para o técnico")
            send_progress(queue, os_gspn, 'Transferindo peças para o técnico', 'running', sid)

            try:
                resultado_request = request_stock_parts_from_os(dados_full)
                dados_full.update(resultado_request)
                if "error" in dados_full:
                    error_msg = f"Erro ao solicitar peças para o técnico: {dados_full['error']}"
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, 'Erro ao transferir peças para o técnico', 'failed', sid, error_msg)
                    #logger.debug(f"Estado de dados_full após falha no passo 8a: {json.dumps(dados_full, indent=2, default=str)}")
                    return False
                logger.info("Solicitação de peças para o técnico concluída")
            except Exception as e:
                error_msg = f"Erro ao solicitar peças para o técnico: {str(e)}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao transferir peças para o técnico', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após erro no passo 8a: {json.dumps(dados_full, indent=2, default=str)}")
                return False

            logger.info("Passo 8b: Transferindo peças para o técnico")
            try:
                resultado = transferir_pecas_tecnico(dados_full)
                if not resultado:
                    error_msg = f"Erro ao transferir peças para o técnico: {dados_full.get('error', 'Erro desconhecido')}"
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, 'Erro ao transferir peças para o técnico', 'failed', sid, error_msg)
                    #logger.debug(f"Estado de dados_full após falha no passo 8b: {json.dumps(dados_full, indent=2, default=str)}")
                    return False
                logger.info("Transferência de peças para o técnico concluída")
            except Exception as e:
                error_msg = f"Erro ao transferir peças para o técnico: {str(e)}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao transferir peças', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após erro no passo 8b: {json.dumps(dados_full, indent=2, default=str)}")
                return False
                
            #send_progress(queue, os_gspn, 'Peças transferidas para o técnico', 'completed', sid)

        # 9 - Remover peças da OS, se necessário
        if dados_full.get("parts_to_remove") and dados_full["parts_to_remove"]:
            logger.info("Passo 9: Removendo peças da OS")
            send_progress(queue, os_gspn, 'Removendo peças divergentes', 'running', sid)
            try:
                resultado = remover_pecas_os(dados_full)
                if not resultado or "error" in dados_full:
                    error_msg = f"Erro ao remover peças da OS: {dados_full.get('error', 'Erro desconhecido')}"
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, 'Removendo peças desnecessárias', 'failed', sid, error_msg)
                    #logger.debug(f"Estado de dados_full após falha no passo 9: {json.dumps(dados_full, indent=2, default=str)}")
                    return False
                logger.info("Remoção de peças da OS concluída")
            except Exception as e:
                error_msg = f"Erro ao remover peças da OS: {str(e)}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Removendo peças desnecessárias', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após erro no passo 9: {json.dumps(dados_full, indent=2, default=str)}")
                return False
                
            #send_progress(queue, os_gspn, 'Peça divergentes removidas', 'completed', sid)

        # 10 - Inserir peças na OS, se necessário
        if True: #dados_full.get("parts_to_add") and dados_full["parts_to_add"]:
            logger.info("Passo 10: Inserindo peças na OS")
            send_progress(queue, os_gspn, 'Inserindo peças e deliveries', 'running', sid)
            try:
                resultado = inserir_pecas_gspn(dados_full)
                if resultado is False:
                    error_msg = "Erro ao inserir peças na OS"
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, 'Erro ao inserir peças', 'failed', sid, error_msg)
                    return False
                    #logger.debug(f"Estado de dados_full após falha no passo 10: {json.dumps(dados_full, indent=2, default=str)}")
                elif isinstance(resultado, dict) and "Erro" in resultado:
                    error_msg = "Erro ao inserir peças na OS"
                    mensagem_erro = resultado["Erro"]
                    print(f"mensagem de erro: {mensagem_erro}")
                    erro =  json.loads(mensagem_erro)
                    erro_filtrado = erro["message"]
                    logger.error(error_msg)
                    send_progress(queue, os_gspn, f'Erro ao inserir peças: {erro_filtrado}', 'failed', sid, error_msg)
                    return False
                logger.info("Inserção de peças na OS concluída")
            except Exception as e:
                error_msg = "Erro ao inserir peças na OS"
                error_msg = f"Erro ao inserir peças na OS: {str(e)}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao inserir peças', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após erro no passo 10: {json.dumps(dados_full, indent=2, default=str)}")
                return False
                
            #send_progress(queue, os_gspn, 'Peças inseridas', 'completed', sid)

        # 11 - Posta G/I nas peças
        logger.info("Passo 11: Postando G/I nas peças")
        send_progress(queue, os_gspn, 'Postando G/I', 'running', sid)
        try:
            # Recarrega os dados da OS antes de postar G/I
            resultado_fetch = fetch_os_data(os_gspn)
            dados_full.update(resultado_fetch)
            resultado_extract = extract_os_data_full(dados_full)
            dados_full.update(resultado_extract)
            logger.info("Dados da OS recarregados para postagem de G/I")
            
            resultado_gi = manusear_gi(dados_full)
            dados_full.update(resultado_gi)
            if "error" in dados_full:
                error_msg = f"Erro ao postar G/I: {dados_full['error']}"
                logger.error(error_msg)
                send_progress(queue, os_gspn, 'Erro ao postar G/I', 'failed', sid, error_msg)
                #logger.debug(f"Estado de dados_full após falha no passo 11: {json.dumps(dados_full, indent=2, default=str)}")
                return False
            logger.info("Postagem de G/I concluída")
        except Exception as e:
            error_msg = f"Erro ao postar G/I: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'Erro ao postar G/I', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 11: {json.dumps(dados_full, indent=2, default=str)}")
            return False
            
        #send_progress(queue, os_gspn, 'G/I postado', 'completed', sid)

        # 12 - Revalida a OS após sincronização
        logger.info("Passo 12: Validando sincronização")
        send_progress(queue, os_gspn, 'Verificando resultado', 'running', sid)
        try:
            # Recarrega os dados da OS
            resultado_fetch = fetch_os_data(os_gspn)
            dados_full.update(resultado_fetch)
            resultado_extract = extract_os_data_full(dados_full)
            dados_full.update(resultado_extract)
            logger.info("Dados da OS recarregados para validação")
            
            # Valida os resultados
            used_parts_cos = dados_full.get("used_parts_cos", {})
            parts = dados_full.get("parts", {})
            divergencias = []

            for codigo, info_cos in used_parts_cos.items():
                if codigo not in parts:
                    divergencias.append(f"Peça {codigo} ausente na OS (necessária: {info_cos['quantidade']})")
                else:
                    qtd_os = int(parts[codigo]["quantity"])
                    qtd_cos = info_cos["quantidade"]
                    if qtd_os != qtd_cos:
                        divergencias.append(f"Peça {codigo} com quantidade divergente: OS={qtd_os}, COS={qtd_cos}")
                    if not parts[codigo]["gi_posted"]:
                        divergencias.append(f"Peça {codigo} sem G/I postado")
                    if not parts[codigo]["delivery"].strip():
                        divergencias.append(f"Peça {codigo} sem delivery preenchido")

            for codigo in parts:
                if codigo not in used_parts_cos:
                    divergencias.append(f"Peça {codigo} presente na OS mas não no COS")

            if divergencias:
                logger.warning("Divergências encontradas após sincronização:")
                for divergencia in divergencias:
                    logger.warning(f" - {divergencia}")
                
                msg_divergencia = "Sincronização concluída, mas com divergências: " + ", ".join(divergencias[:3])
                if len(divergencias) > 3:
                    msg_divergencia += f" e mais {len(divergencias) - 3} problemas"
                
                #send_progress(queue, os_gspn, msg_divergencia, 'completed', sid)
                logger.debug(f"Estado final de dados_full com divergências no passo 12: {json.dumps(dados_full, indent=2, default=str)}")
                return True
        except Exception as e:
            error_msg = f"Erro ao validar sincronização: {str(e)}"
            logger.error(error_msg)
            send_progress(queue, os_gspn, 'A verificação falhou', 'failed', sid, error_msg)
            #logger.debug(f"Estado de dados_full após erro no passo 12: {json.dumps(dados_full, indent=2, default=str)}")
            return False

        logger.info("Sincronização concluída com sucesso! Todas as peças estão corretas e com G/I postado.")
        send_progress(queue, os_gspn, 'Tudo certo!', 'completed', sid)
        #logger.debug(f"Estado final de dados_full após sucesso: {json.dumps(dados_full, indent=2, default=str)}")
        return True

    except Exception as e:
        error_msg = f"Erro inesperado: {str(e)}"
        logger.error(error_msg, exc_info=True)
        #logger.debug(f"Estado de dados_full após erro inesperado: {json.dumps(dados_full, indent=2, default=str)}")
        send_progress(queue, os_gspn, 'Erro inesperado', 'failed', sid, error_msg)
        return False
    
def ajustar_estq_asc(dados_full):
    """
    Ajusta o estoque ASC enviando requisições para cada peça em asc_stock_adjustments.
    
    Args:
        dados_full (dict): Dicionário contendo 'cookies' e 'asc_stock_adjustments'.
    
    Returns:
        bool: True se todas as requisições forem bem-sucedidas, ou atualiza dados_full com erro.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    #logger.debug(f"Início da função ajustar_estq_asc. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    
    logger.info("Iniciando ajuste de estoque ASC")
    
    cookies = dados_full.get("cookies")
    asc_stock_adjustments = dados_full.get("asc_stock_adjustments")

    if not cookies:
        error_msg = "Cookies não encontrados em dados_full"
        logger.error(error_msg)
        dados_full["error"] = error_msg
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return False
    
    if not asc_stock_adjustments:
        logger.info("Nenhum ajuste necessário no estoque ASC: asc_stock_adjustments está vazio")
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return True

    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    referer = "https://biz6.samsungcsportal.com/invmgnt/inv/InventoryAdjustSave.jsp"
    headers = create_headers(referer)

    payload_base = {
        "cmd": "InventoryAdjustCmd",
        "Cdmty": "AJ_REASON",
        "Lang": "P",
        "asc_code": "0002446971",
        "IV_ASC_CODE": "0002446971",
        "material": "",
        "ext_user": "marcoslima3",
        "account": "0002446971",
        "avg_price": "23.98",
        "IV_LIMIT_FLAG": "",
        "IV_SO_NO": "",
        "INVOICE_NO": "",
        "TRY_CNT": "1",
        "ad_reason": "90",
        "add_qty": "",
        "remark": "Ajustando para transferir ao tecnico."
    }

    for ajuste in asc_stock_adjustments:
        codigo = ajuste["codigo"]
        quantidade = str(ajuste["quantidade"])

        logger.info(f"Ajustando estoque para peça {codigo}: adicionando {quantidade} unidade(s)")

        payload = payload_base.copy()
        payload["material"] = codigo
        payload["add_qty"] = quantidade
        
        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
            response.raise_for_status()
            
            response_text = response.text.strip()
            if response_text.startswith("4e"):
                response_text = response_text[2:-1]
            response_json = json.loads(response_text)

            if response_json.get("success", False):
                logger.info(f"Ajuste bem-sucedido para {codigo}: {quantidade} adicionada ao estoque ASC")
            else:
                error_msg = f"Falha no ajuste para {codigo}: {response_json.get('returnMessage', 'Erro desconhecido')}"
                logger.error(error_msg)
                dados_full["error"] = error_msg
                #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
                return False
        except requests.exceptions.RequestException as e:
            error_msg = f"Erro ao ajustar estoque ASC para {codigo}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return False
        except json.JSONDecodeError as e:
            error_msg = f"Erro ao parsear resposta para {codigo}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return False

    logger.info("Todos os ajustes no estoque ASC foram concluídos com sucesso!")
    #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    return True

def manusear_gi(dados_full, cancelar_gi=None):
    """
    Realiza o posting ou cancelamento de G/I para peças em used_parts_cos ou lista específica.
    
    Args:
        dados_full (dict): Dicionário contendo 'cookies', 'used_parts_cos', 'parts', 'in_out_wty' e outros dados.
        cancelar_gi (list, optional): Lista de códigos de peças para cancelar G/I. Padrão é None.
    
    Returns:
        dict: Dicionário dados_full atualizado com resultados ou erros detalhados.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    #logger.debug(f"Início da função manusear_gi. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    
    logger.info(f"Iniciando manusear_gi. Modo de cancelamento: {cancelar_gi is not None}")
    
    cookies = dados_full.get("cookies")
    used_parts_cos = dados_full.get("used_parts_cos")
    parts = dados_full.get("parts", {})
    in_out_wty = dados_full.get("in_out_wty")
    asc_job_no = dados_full.get("asc_job_no")
    object_id = dados_full.get("object_id")
    engineer = dados_full.get("engineer")
    user_id = dados_full.get("user_id")

    required_fields = {
        "cookies": cookies, "used_parts_cos": used_parts_cos, "in_out_wty": in_out_wty,
        "asc_job_no": asc_job_no, "object_id": object_id, "engineer": engineer, "user_id": user_id
    }
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        error_msg = f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"
        logger.error(error_msg)
        dados_full["error"] = error_msg
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    if not used_parts_cos and not cancelar_gi:
        logger.info("Nenhuma peça encontrada em used_parts_cos e cancelar_gi não especificado.")
        dados_full["gi_posted"] = []
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    referer = "https://biz6.samsungcsportal.com/svctracking/svcorder/SVCPopGiPosting.jsp"
    headers = create_headers(referer)

    payload_base = {
        "cmd": "ServiceOrderGiPostingCmd",
        "ascCode": "0002446971",
        "PARTS_CODE": "",
        "IV_IMEI": "",
        "PARTS_QTY": "1",
        "GI_FLAG": "Y",
        "ENGINEER_CODE": engineer,
        "objectID": object_id,
        "SEQ_NO": "",
        "ASC_JOB_NO": asc_job_no,
        "IN_OUT_WTY": "",
        "IV_ASC_ACCTNO": "0002446971",
        "IV_INOUT": "I",
        "IV_WTY_INOUT": in_out_wty,
        "GI_DATE": datetime.now().strftime("%Y%m%d"),
        "giDocNo": "",
        "fiscalYear": "",
        "userId": user_id,
        "IV_LIMIT_FLAG": "",
        "TRY_CNT": "1",
        "IV_SO_NO": "",
        "IV_AUTO_DO": ""
    }

    gi_posted = []

    def tentar_postar_pecas(pecas_a_processar):
        corrigir_delivery = []
        local_gi_posted = []
        
        for parts_code in pecas_a_processar:
            if cancelar_gi is not None:
                if parts_code not in parts or "gi_date" not in parts[parts_code]:
                    logger.info(f"Peça {parts_code} não tem G/I ou gi_date para cancelar, ignorando.")
                    continue
                payload = payload_base.copy()
                payload["PARTS_CODE"] = parts_code
                payload["PARTS_QTY"] = str(used_parts_cos[parts_code]["quantidade"])
                payload["SEQ_NO"] = parts[parts_code]["seq_no"]
                payload["GI_FLAG"] = "N"
                payload["IV_INOUT"] = "O"
                payload["GI_DATE"] = parts[parts_code]["gi_date"]
                #logger.info(f"Preparando para cancelar G/I para peça {parts_code} (SEQ_NO={payload['SEQ_NO']}, GI_DATE={payload['GI_DATE']})")
            else:
                if parts_code in parts and parts.get(parts_code, {}).get("gi_posted", False):
                    logger.info(f"Peça {parts_code} já tem G/I postado em parts, ignorando.")
                    continue
                payload = payload_base.copy()
                payload["PARTS_CODE"] = parts_code
                payload["PARTS_QTY"] = str(used_parts_cos[parts_code]["quantidade"])
                payload["SEQ_NO"] = parts.get(parts_code, {}).get("seq_no", "0001")
                #logger.info(f"Preparando para postar G/I para peça {parts_code} (SEQ_NO={payload['SEQ_NO']})")

            logger.debug(f"Enviando requisição para {parts_code}: {json.dumps(payload, indent=2)}")

            try:
                response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
                response.raise_for_status()
                response_text = response.text.strip()
                logger.debug(f"Resposta recebida para {parts_code} - Status: {response.status_code}, Corpo: {response_text[:100]}")

                if response_text.startswith("4e"):
                    response_text = response_text[2:-1]
                
                try:
                    result = json.loads(response_text)
                    logger.debug(f"Resposta parseada para {parts_code}: {json.dumps(result, indent=2)}")

                    if (not result.get("success", False) and 
                        result.get("message") == "[Error] Check D/O Balance Info." and 
                        cancelar_gi is None):
                        logger.warning(f"Erro de D/O Balance para {parts_code}, adicionando a corrigir_delivery")
                        corrigir_delivery.append(parts_code)
                        continue

                    if result.get("success", False):
                        action = "cancelado" if cancelar_gi is not None else "postado"
                        logger.info(f"G/I {action} com sucesso para {parts_code}, quantidade: {payload['PARTS_QTY']}, SEQ_NO: {payload['SEQ_NO']}")
                        local_gi_posted.append({
                            "parts_code": parts_code,
                            "quantity": payload["PARTS_QTY"],
                            "gi_doc_no": result.get("giDocNo", ""),
                            "seq_no": payload["SEQ_NO"]
                        })
                    else:
                        error_msg = f"Erro ao processar G/I para {parts_code}: Status={response.status_code}, Resposta={json.dumps(result)}"
                        logger.error(error_msg)
                        dados_full["error"] = error_msg
                        return None, None
                except json.JSONDecodeError as e:
                    error_msg = f"Erro ao parsear resposta JSON para {parts_code}: {str(e)}, Resposta crua={response_text}"
                    logger.error(error_msg)
                    dados_full["error"] = error_msg
                    return None, None

            except requests.exceptions.RequestException as e:
                error_msg = f"Erro de requisição ao processar G/I para {parts_code}: {str(e)}"
                logger.error(error_msg)
                dados_full["error"] = error_msg
                return None, None

        return local_gi_posted, corrigir_delivery

    pecas_a_processar = cancelar_gi if cancelar_gi is not None else used_parts_cos.keys()
    
    if not pecas_a_processar:
        logger.info("Nenhuma peça para processar.")
        dados_full["gi_posted"] = []
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full
    
    logger.info(f"Iniciando processamento de G/I para {len(pecas_a_processar)} peças")

    local_gi_posted, corrigir_delivery = tentar_postar_pecas(pecas_a_processar)
    if local_gi_posted is None:
        logger.error("Erro crítico durante primeira tentativa de postar G/I.")
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full
    gi_posted.extend(local_gi_posted)

    tentativa = 1
    max_tentativas = 3
    while corrigir_delivery and cancelar_gi is None and tentativa <= max_tentativas:
        logger.info(f"Tentativa {tentativa}: Processando correção de delivery para {len(corrigir_delivery)} peças")
        dados_full["parts_to_remove"] = [
            {"codigo": code, "seq_no": parts[code]["seq_no"]}
            for code in corrigir_delivery if code in parts
        ]
        dados_full["parts_to_add"] = [
            {
                "codigo": code,
                "quantidade": used_parts_cos[code]["quantidade"],
                "delivery": used_parts_cos[code].get("delivery", "")
            }
            for code in corrigir_delivery 
            if code in used_parts_cos
        ]
        
        resultado_remover = remover_pecas_os(dados_full)
        if resultado_remover and "error" not in dados_full:
            resultado_inserir = inserir_pecas_gspn(dados_full)
            if not resultado_inserir:
                logger.error("Falha ao inserir peças após correção de delivery")
                break
        else:
            logger.error("Falha ao remover peças para correção de delivery")
            break

        resultado_fetch = fetch_os_data(dados_full["object_id"])
        dados_full.update(resultado_fetch)
        resultado_extract = extract_os_data_full(dados_full)
        dados_full.update(resultado_extract)
        parts = dados_full.get("parts", {})

        local_gi_posted, corrigir_delivery = tentar_postar_pecas(corrigir_delivery)
        if local_gi_posted is None:
            logger.error(f"Erro crítico durante tentativa {tentativa} de postar G/I após correção de delivery.")
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return dados_full
        gi_posted.extend(local_gi_posted)
        tentativa += 1
    
    if corrigir_delivery and tentativa > max_tentativas:
        logger.warning(f"Atingido limite de {max_tentativas} tentativas para corrigir delivery. Peças sem G/I: {corrigir_delivery}")

    dados_full["gi_posted"] = gi_posted

    logger.info(f"Processamento de G/I concluído! {len(gi_posted)} peças processadas com sucesso.")
    #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    return dados_full

def remover_pecas_os(dados_full):
    """
    Remove peças desnecessárias da OS com base em dados_full["parts_to_remove"].
    
    Args:
        dados_full (dict): Dicionário contendo 'cookies', 'parts_to_remove' e 'parts'.
        
    Returns:
        dict: Dados atualizados ou False em caso de erro.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    logger.debug(f"Início da função remover_pecas_os. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    
    logger.info("Iniciando remoção de peças da OS")
    
    cookies = dados_full.get('cookies')
    parts_to_remove = dados_full.get('parts_to_remove', [])
    parts = dados_full.get('parts', {})
    
    if not parts_to_remove:
        logger.info("Nenhuma peça para remover encontrada em dados_full")
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full
    
    logger.info(f"Peças para remover: {parts_to_remove}")
    
    try:
        base_payload = pl_deletar_pecas(dados_full)
    except Exception as e:
        logger.error(f"Erro ao montar payload base: {str(e)}")
        dados_full["error"] = f"Erro ao montar payload de deleção: {str(e)}"
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    cancelar_gi = []
    for part in parts_to_remove:
        codigo = part.get('codigo')
        logger.info(f"Verificando peça {codigo} para G/I postado")
        if codigo in parts and parts[codigo].get('gi_posted'):
            logger.info(f"Peça {codigo} tem G/I postado. Preparando para cancelar")
            cancelar_gi.append(codigo)

    if cancelar_gi:
        logger.info(f"Cancelando G/I para as peças: {cancelar_gi}")
        manusear_gi(dados_full, cancelar_gi)
        try:
            resultado_fetch = fetch_os_data(dados_full['object_id'])
            dados_full.update(resultado_fetch)
            resultado_extract = extract_os_data_full(dados_full)
            dados_full.update(resultado_extract)
        except Exception as e:
            logger.error(f"Erro ao recarregar dados após cancelar G/I: {str(e)}")
            dados_full["error"] = f"Erro ao recarregar dados após cancelar G/I: {str(e)}"
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return dados_full

    for part in parts_to_remove:
        codigo = part.get('codigo')
        seq_no = part.get('seq_no')
        
        if not codigo or not seq_no:
            logger.warning(f"Item inválido em parts_to_remove: {part}")
            continue

        payload = base_payload.copy()
        payload["IV_PARTS_CODE"] = codigo
        payload["SAWPART"] = codigo

        url = f"https://biz6.samsungcsportal.com/gspn/operate.do?PARTS_SEQ_NO={seq_no}"
        referer = f"https://biz6.samsungcsportal.com/gspn/operate.do?cmd=ZifGspnSvcMainLDCmd&objectID={dados_full.get('object_id')}"
        headers = create_headers(referer)

        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")
            if "html" in content_type.lower():
                soup = BeautifulSoup(response.text, "html.parser")
                logger.info(f"Remoção de {codigo} (seq_no: {seq_no}) - Título da página: {soup.title.string if soup.title else 'Sem título'}")
            elif "json" in content_type.lower():
                data = response.json()
                logger.info(f"Remoção de {codigo} (seq_no: {seq_no}) - Resposta JSON: {data}")
            else:
                logger.info(f"Remoção de {codigo} (seq_no: {seq_no}) - Resposta bruta: {response.text[:100]}")
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para remover {codigo} (seq_no: {seq_no}): {str(e)}")
            dados_full["error"] = f"Erro ao remover peça {codigo}: {str(e)}"
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return dados_full

    try:
        resultado_fetch = fetch_os_data(dados_full['object_id'])
        dados_full.update(resultado_fetch)
        resultado_extract = extract_os_data_full(dados_full)
        dados_full.update(resultado_extract)
    except Exception as e:
        logger.error(f"Erro ao recarregar dados após remover peças: {str(e)}")
        dados_full["error"] = f"Erro ao recarregar dados após remover peças: {str(e)}"
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    logger.info("Todas as peças desnecessárias foram removidas com sucesso!")
    #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    return dados_full

def request_stock_parts_from_os(dados_full):
    """
    Solicita peças ao estoque ASC com base em technician_stock_shortages.
    
    Args:
        dados_full (dict): Dicionário contendo 'cookies', 'technician_stock_shortages' e outros dados.
    
    Returns:
        dict: Dicionário dados_full atualizado com resultados ou erros.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    #logger.debug(f"Início da função request_stock_parts_from_os. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    
    logger.info("Iniciando solicitação de peças ao estoque ASC")
    
    cookies = dados_full.get("cookies")
    technician_stock_shortages = dados_full.get("technician_stock_shortages")
    company = dados_full.get("company")
    ext_user = dados_full.get("user_id")
    asc_code = dados_full.get("asc_code")
    account = dados_full.get("account")
    req_date = dados_full.get("req_date")
    engineer = dados_full.get("engineer")
    asc_job_no = dados_full.get("asc_job_no")
    refno2 = dados_full.get("token_no")

    required_fields = {
        "cookies": cookies, "technician_stock_shortages": technician_stock_shortages,
        "company": company, "ext_user": ext_user, "asc_code": asc_code, "account": account,
        "req_date": req_date, "engineer": engineer, "asc_job_no": asc_job_no, "refno2": refno2
    }
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        error_msg = f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"
        logger.error(error_msg)
        dados_full["error"] = error_msg
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    if not technician_stock_shortages:
        logger.info("Nenhuma peça para solicitar em technician_stock_shortages")
        dados_full["requested_parts"] = []
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return dados_full

    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    referer = "https://biz6.samsungcsportal.com/svctracking/svcorder/SVCPopGiPosting.jsp"
    headers = create_headers(referer)

    payload_base = {
        "cmd": "MaterialRequestCmd",
        "Company": company,
        "ext_user": ext_user,
        "ascCode": asc_code,
        "account": account,
        "i_material": "",
        "i_req_qty": "",
        "ireq_date": quote(req_date),
        "ireq_type": "02",
        "iengineer": engineer,
        "IASC_JOB_NO": asc_job_no,
        "refno2": refno2,
        "ref_item": "0011",
        "i_remark": ""
    }

    requested_parts = []

    for shortage in technician_stock_shortages:
        material = shortage["material"]
        quantidade_a_solicitar = str(shortage["shortage"])
        
        logger.info(f"Solicitando peça {material}: quantidade {quantidade_a_solicitar}")

        payload = payload_base.copy()
        payload["i_material"] = material
        payload["i_req_qty"] = quantidade_a_solicitar

        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
            response.raise_for_status()
            
            response_text = response.text
            if response_text.startswith("7f"):
                response_text = response_text.strip("7f\n0\n")
            
            result = json.loads(response_text)

            if result.get("success", False):
                logger.info(f"Solicitação bem-sucedida para {material}! Request No: {result.get('requestNo')}")
                requested_parts.append({
                    "material": material,
                    "quantity": quantidade_a_solicitar,
                    "request_no": result.get("requestNo")
                })
            else:
                error_msg = f"Erro na solicitação para {material}: {result.get('returnMessage', 'Erro desconhecido')}"
                logger.error(error_msg)
                dados_full["error"] = error_msg
                #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
                return dados_full

        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição para {material}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return dados_full
        except json.JSONDecodeError as e:
            error_msg = f"Erro ao parsear resposta para {material}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return dados_full

    dados_full["requested_parts"] = requested_parts
    logger.info(f"Todas as requisições ({len(requested_parts)}) ao estoque ASC foram concluídas com sucesso!")
    #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    return dados_full

def transferir_pecas_tecnico(dados_full):
    """
    Transfere peças do estoque ASC para o estoque do técnico com base em requested_parts.
    
    Args:
        dados_full (dict): Dicionário contendo 'cookies', 'requested_parts' e 'engineer'.
    
    Returns:
        bool: True se todas as transferências forem bem-sucedidas, False caso contrário.
    """
    logger = configurar_logger(dados_full.get('object_id'))
    #logger.debug(f"Início da função transferir_pecas_tecnico. Estado inicial de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    
    logger.info("Iniciando transferência de peças para o técnico")
    
    cookies = dados_full.get("cookies")
    requested_parts = dados_full.get("requested_parts")
    engineer = dados_full.get("engineer")

    required_fields = {
        "cookies": cookies,
        "requested_parts": requested_parts,
        "engineer": engineer
    }
    missing_fields = [field for field, value in required_fields.items() if not value]
    if missing_fields:
        error_msg = f"Campos obrigatórios ausentes: {', '.join(missing_fields)}"
        logger.error(error_msg)
        dados_full["error"] = error_msg
        #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
        return False

    if not requested_parts:
        logger.info("Nenhuma peça para transferir em requested_parts")
        dados_full["transferred_parts"] = []
        #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
        return True

    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    referer = "https://biz6.samsungcsportal.com/invmgnt/inv/StockTransferConfirm.jsp"
    headers = create_headers(referer)

    payload_base = {
        "cmd": "StockTransferCmd",
        "numPerPage": "",
        "currPage": "",
        "tr_type": "01",
        "ascCode": "0002446971",
        "ext_user": dados_full.get("user_id", "marcoslima3"),
        "tr_from": "0002446971",
        "tr_to": engineer,
        "account": "0002446971",
        "Lang": "P",
        "material": "",
        "tr_qty": "",
        "remark": "",
        "req_no": "",
        "req_item": "000001"
    }

    transferred_parts = []

    for request in requested_parts:
        material = request["material"]
        tr_qty = request["quantity"]
        req_no = request["request_no"]
        
        logger.info(f"Transferindo peça {material}: quantidade {tr_qty}, req_no {req_no}")

        payload = payload_base.copy()
        payload["material"] = material
        payload["tr_qty"] = tr_qty
        payload["req_no"] = req_no

        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
            response.raise_for_status()
            
            response_text = response.text.strip()
            if response_text.startswith("4e"):
                response_text = response_text[2:-1]
            result = json.loads(response_text)

            if result.get("success", False):
                logger.info(f"Transferência bem-sucedida para {material}! Quantidade: {tr_qty}, Req No: {req_no}")
                transferred_parts.append({
                    "material": material,
                    "quantity": tr_qty,
                    "req_no": req_no
                })
            else:
                error_msg = f"Erro na transferência para {material}: {result.get('returnMessage', 'Erro desconhecido')}"
                logger.error(error_msg)
                dados_full["error"] = error_msg
                #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
                return False

        except requests.exceptions.RequestException as e:
            error_msg = f"Erro na requisição para {material}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return False
        except json.JSONDecodeError as e:
            error_msg = f"Erro ao parsear resposta para {material}: {e}"
            logger.error(error_msg)
            dados_full["error"] = error_msg
            #logger.debug(f"Estado de dados_full após erro: {json.dumps(dados_full, indent=2, default=str)}")
            return False

    dados_full["transferred_parts"] = transferred_parts
    logger.info(f"Todas as transferências ({len(transferred_parts)}) para o técnico foram concluídas com sucesso!")
    #logger.debug(f"Estado final de dados_full: {json.dumps(dados_full, indent=2, default=str)}")
    return True

if __name__ == "__main__":
    sincronizar_pecas('4172453900')