
import time
import requests
import json
from bs4 import BeautifulSoup
from urllib.parse import quote
import os
import re
import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from cos.coletar_dados_cos import coletar_usadas_cos
from datetime import datetime
from login_gspn.cookies_manager import obter_cookies_validos_recentes
import requests
import json
import os

def fetch_os_data(object_id):
    """
    Baixa o HTML da Ordem de Serviço do GSPN e inicializa o dicionário dados_full.
    
    Args:
        object_id (str): ID da Ordem de Serviço.
    
    Returns:
        dict: Dicionário dados_full contendo o HTML da OS em 'html_os'.
    """
    # Inicializa o dicionário dados_full
    dados_full = {"object_id": object_id}
    # URL da requisição
    url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Headers
    headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "cache-control": "max-age=0",
        "connection": "keep-alive",
        "host": "biz6.samsungcsportal.com",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
    }

    cookies = obter_cookies_validos_recentes()

    dados_full['cookies'] = cookies  # Adiciona os cookies ao dicionário
    #print("Cookies obtidos:", cookies)
    # Payload para buscar a OS
    payload = {"cmd": "ZifGspnSvcMainLDCmd", "objectID": object_id}

    # Faz a requisição
    try:
        response = requests.get(url, headers=headers, cookies=cookies, params=payload, verify=False)
        response.raise_for_status()
        dados_full["html_os"] = response.text
        dados_full["cookies"] = cookies  # Adiciona cookies ao dicionário para uso posterior
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        dados_full["html_os"] = None
        dados_full["error"] = f"Erro na requisição: {e}"
    
    return dados_full


from bs4 import BeautifulSoup
import re

def extract_os_data_full(dados_full):
    """
    Extrai e organiza todos os dados relevantes da OS em variáveis e dicionários, incluindo PARTS_SEQ_NO.
    
    Args:
        dados_full (dict): Dicionário contendo 'html_os' (e possivelmente 'cookies' e 'error').
    
    Returns:
        dict: Dicionário dados_full atualizado com variáveis _l e dados da tabela de peças.
    """
    # Verifica se há HTML para processar
    if not dados_full.get("html_os"):
        if "error" not in dados_full:
            dados_full["error"] = "Nenhum HTML disponível para extração"
        return dados_full

    # Parseia o HTML
    soup = BeautifulSoup(dados_full["html_os"], 'html.parser')

    # Extrai variáveis JavaScript (_l e _l.u)
    script_tags = soup.find_all('script', type='text/javascript')
    l_data = {}
    for script in script_tags:
        if script.string and '_l' in script.string:
            matches = re.findall(r'_l\.(u\.)?(\w+) = ["\']?([^"\']+)["\']?;', script.string)
            for match in matches:
                prefix, key, value = match
                if prefix == 'u.':
                    l_data[f"u.{key}"] = value
                else:
                    l_data[key] = value

    # Campos extraídos de _l
    dados_full["asc_job_no"] = l_data.get("ASC_JOB_NO")
    dados_full["engineer"] = l_data.get("ENGINEER", l_data.get("u.ENGINEER"))
    dados_full["user_id"] = l_data.get("u.UserId")
    dados_full["company"] = l_data.get("u.c")
    dados_full["token_no"] = l_data.get(soup, "TOKEN_NO") or ""
    dados_full["req_date"] = l_data.get("today", datetime.now().strftime("%d/%m/%Y"))
    dados_full["account"] = l_data.get("u.AccountCode")
    dados_full["asc_code"] = l_data.get("u.AccountCode")
    dados_full["country_cd"] = l_data.get("u.CountryCd")
    dados_full["date_format"] = l_data.get("u.DateFormat")
    dados_full["locale"] = l_data.get("u.Locale")
    dados_full["in_out_wty"] = l_data.get("IN_OUT_WTY")
    dados_full["status_os"] = soup.find("input", {"id": "currStatus"}).get("value"),

    # Validação de campos obrigatórios
    missing_fields = []
    for field in ["asc_job_no", "engineer", "user_id", "company", "token_no", "req_date", "account", "asc_code"]:
        if not dados_full.get(field):
            missing_fields.append(field)
    if missing_fields:
        dados_full["error"] = f"Campos obrigatórios não encontrados na OS: {', '.join(missing_fields)}"
        return dados_full

    # Extrai dados da tabela de peças
    parts_table = soup.find('table', id='partsTable')
    if not parts_table:
        dados_full["error"] = "Tabela de peças não encontrada"
        return dados_full
    
    tbody = parts_table.find('tbody', id='partsTableBody')
    if not tbody:
        dados_full["error"] = "Corpo da tabela de peças não encontrado"
        return dados_full

    # Dicionário para armazenar dados das peças
    parts = {}
    for row in tbody.find_all('tr'):
        parts_code = row.find('input', {'name': 'PARTS_CODE'}).get('value') if row.find('input', {'name': 'PARTS_CODE'}) else ''
        quantity = row.find('input', {'name': 'PARTS_QTY'}).get('value') if row.find('input', {'name': 'PARTS_QTY'}) else '0'
        delivery = row.find('input', {'name': 'INVOICE_NO'}).get('value') if row.find('input', {'name': 'INVOICE_NO'}) else ''
        gi_date = row.find('input', {'name': 'GI_DATE'}).get('value') if row.find('input', {'name': 'GI_DATE'}) else ''
        parts_desc = row.find('input', {'name': 'PARTS_DESC'}).get('value') if row.find('input', {'name': 'PARTS_DESC'}) else ''
        request_no = row.find('input', {'name': 'REQUEST_NO'}).get('value') if row.find('input', {'name': 'REQUEST_NO'}) else ''
        seq_no = row.find('input', {'name': 'PARTS_SEQ_NO'}).get('value') if row.find('input', {'name': 'PARTS_SEQ_NO'}) else ''  # Novo campo
        
        gi_posted = bool(gi_date.strip() and gi_date != "00/00/0000")

        if parts_code:
            parts[parts_code] = {
                "quantity": quantity,
                "delivery": delivery,
                "gi_posted": gi_posted,
                "description": parts_desc,
                "request_no": request_no,
                "seq_no": seq_no,
                "gi_date": gi_date
            }

    dados_full["parts"] = parts
    return dados_full



def consultar_estoque_tecnico(dados_full):
    """
    Consulta o estoque de peças do técnico e incrementa os dados em dados_full.
    Depende exclusivamente dos cookies fornecidos em dados_full.
    
    Args:
        dados_full (dict): Dicionário contendo 'engineer', 'cookies' e possivelmente outros dados da OS.
    
    Returns:
        dict: Dicionário dados_full atualizado com o estoque do técnico em 'technician_stock'.
    """
    # Verifica se os campos necessários estão presentes
    engineer_code = dados_full.get("engineer")
    cookies = dados_full.get("cookies")
    
    if not engineer_code:
        dados_full["error"] = "Código do engenheiro (engineer) não encontrado em dados_full"
        return dados_full
    
    if not cookies:
        dados_full["error"] = "Cookies não encontrados em dados_full"
        return dados_full

    # URL da requisição
    url = "https://biz6.samsungcsportal.com/gspn/operate.do"

    # Headers
    headers = {
        "accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "accept-encoding": "gzip, deflate, br, zstd",
        "accept-language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "connection": "keep-alive",
        "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "host": "biz6.samsungcsportal.com",
        "origin": "https://biz6.samsungcsportal.com",
        "referer": "https://biz6.samsungcsportal.com/invmgnt/inv/StockTransfer.jsp?search_status=&searchContent=&menuBlock=&menuUrl=&naviDirValue=",
        "sec-ch-ua": '"Not(A:Brand";v="99", "Google Chrome";v="133", "Chromium";v="133"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "x-prototype-version": "1.7.2",
        "x-requested-with": "XMLHttpRequest"
    }

    # Payload para consultar o estoque do técnico
    payload = {
        "cmd": "EngineerStockCmd",
        "asc_code": dados_full.get("asc_code", "0002446971"),  # Usa asc_code da OS, se disponível
        "engineer": engineer_code,
        "account": dados_full.get("account", "0002446971"),  # Usa account da OS, se disponível
        "material": ""  # Consulta todas as peças
    }

    try:
        response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
        if response.status_code == 200:
            response_json = response.json()
            estoque = []
            if "ptData" in response_json and isinstance(response_json["ptData"], list):
                for item in response_json["ptData"]:
                    material = item.get("material", "N/A")
                    eng_stock_qty = item.get("eng_stock_qty", "0")
                    estoque.append({"material": material, "eng_stock_qty": eng_stock_qty})
            else:
                dados_full["error"] = "A resposta não contém 'ptData' no formato esperado"
                return dados_full
            # Incrementa os dados do estoque em dados_full
            dados_full["technician_stock"] = estoque
        else:
            dados_full["error"] = f"Erro na requisição: Status Code {response.status_code} - {response.text}"
    except requests.exceptions.RequestException as e:
        dados_full["error"] = f"Erro ao fazer a requisição: {e}"

    return dados_full



def confere_qtd_pecas(dados_full):
    """
    Confere as quantidades de peças em used_parts_cos contra technician_stock e asc_stock,
    gerando ajustes para o estoque ASC e identificando faltas no estoque do técnico.
    Exclui peças de 'parts' com gi_posted = true de toda a lógica.

    Args:
        dados_full (dict): Dicionário contendo 'cookies', 'used_parts_cos', 'technician_stock' e 'parts'.

    Returns:
        dict: Dicionário dados_full atualizado com 'technician_stock_shortages', 'asc_stock' e 'asc_stock_adjustments'.
    """
    # Verifica se os campos necessários estão presentes
    cookies = dados_full.get("cookies")
    used_parts_cos = dados_full.get("used_parts_cos")
    technician_stock = dados_full.get("technician_stock")
    parts = dados_full.get("parts", {})  # Obtém o dicionário parts, default vazio se não existir

    if not cookies:
        dados_full["error"] = "Cookies não encontrados em dados_full"
        return dados_full
    
    if not used_parts_cos:
        dados_full["error"] = "Dados das peças usadas COS (used_parts_cos) não encontrados em dados_full"
        return dados_full
    
    #if not technician_stock:
        #dados_full["error"] = "Dados do estoque do técnico (technician_stock) não encontrados em dados_full"
        #return dados_full

    # Converte technician_stock para um dicionário de código: quantidade
    tech_stock_dict = {item["material"]: int(item["eng_stock_qty"]) for item in technician_stock}

    # Filtra used_parts_cos para excluir peças com gi_posted = true em parts
    filtered_used_parts_cos = {}
    for codigo, info in used_parts_cos.items():
        if not (parts and codigo in parts and parts[codigo].get("gi_posted", False)):
            filtered_used_parts_cos[codigo] = info
        else:
            print(f"Peça {codigo} excluída de toda a lógica (gi_posted = true)")

    # Identifica peças ausentes ou insuficientes no estoque do técnico
    technician_stock_shortages = []
    for codigo, info in filtered_used_parts_cos.items():
        quantidade_necessaria = int(info["quantidade"])
        quantidade_tecnico = tech_stock_dict.get(codigo, 0)
        
        if quantidade_tecnico < quantidade_necessaria:
            shortage = quantidade_necessaria - quantidade_tecnico
            technician_stock_shortages.append({
                "material": codigo,
                "shortage": shortage
            })
            print(f"Falta no estoque do técnico para {codigo}: {shortage}")
        else:
            print(f"Estoque do técnico suficiente para {codigo}")

    # Adiciona a lista de faltas ao estoque do técnico em dados_full
    dados_full["technician_stock_shortages"] = technician_stock_shortages

    # URL e headers da requisição ao ASC
    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    headers = {
        "Host": "biz6.samsungcsportal.com",
        "Connection": "keep-alive",
        "X-Prototype-Version": "1.7.2",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://biz6.samsungcsportal.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://biz6.samsungcsportal.com/invmgnt/inv/InventoryAdjust.jsp",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    # Payload base para consulta ao ASC
    payload_base = {
        "cmd": "BranchStockCmd",
        "numPerPage": "100",
        "currPage": "0",
        "Lang": "P",
        "account": "0002446971",
        "asc_code": "0002446971",
        "material": ""
    }

    # Dicionários para armazenar resultados
    asc_stock = {}
    asc_stock_adjustments = []

    # Consulta o ASC apenas para peças em filtered_used_parts_cos
    for codigo, info in filtered_used_parts_cos.items():
        quantidade_necessaria = int(info["quantidade"])
        quantidade_tecnico = tech_stock_dict.get(codigo, 0)
        
        # Se o estoque do técnico for suficiente, pula a consulta
        if quantidade_tecnico >= quantidade_necessaria:
            continue
        
        payload = payload_base.copy()
        payload["material"] = codigo

        try:
            response = requests.post(url, headers=headers, cookies=cookies, data=payload, verify=False)
            if response.status_code == 200:
                response_json = json.loads(response.text[3:-1] if response.text.startswith("41d") else response.text)
                quantidade_asc = int(response_json["ptData"][0].get("wh_stock_qty", "0")) if "ptData" in response_json and response_json["ptData"] else 0
                asc_stock[codigo] = str(quantidade_asc)
                print(f"Estoque ASC para {codigo}: {quantidade_asc}")
            else:
                asc_stock[codigo] = "0"
                print(f"Erro na requisição para {codigo}: Status {response.status_code}")
        
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            asc_stock[codigo] = "0"
            print(f"Erro ao consultar ASC para {codigo}: {e}")

        # Calcula ajustes, se necessário
        quantidade_asc = int(asc_stock[codigo])
        quantidade_total = quantidade_tecnico + quantidade_asc
        if quantidade_total < quantidade_necessaria:
            quantidade_a_adicionar = quantidade_necessaria - quantidade_total
            asc_stock_adjustments.append({
                "codigo": codigo,
                "quantidade": quantidade_a_adicionar
            })
            print(f"Ajuste necessário para {codigo}: adicionar {quantidade_a_adicionar} ao ASC")

    # Atualiza dados_full com os resultados
    dados_full["asc_stock"] = asc_stock
    dados_full["asc_stock_adjustments"] = asc_stock_adjustments

    return dados_full

def comparar_pecas_os(dados_full):
    """
    Compara as peças da OS com as peças usadas da COS e gera listas de ações corretivas.
    
    Args:
        dados_full (dict): Dicionário contendo 'parts' e 'used_parts_cos'.
    
    Returns:
        dict: Dicionário dados_full atualizado com 'parts_to_remove' e 'parts_to_add'.
    """
    print("Iniciando comparação de peças...")
    # Verifica os campos, permitindo parts vazio
    parts = dados_full.get("parts", {})  # Usa {} como padrão se parts for None
    used_parts_cos = dados_full.get("used_parts_cos")

    if not used_parts_cos:
        dados_full["error"] = "Dados das peças usadas COS (used_parts_cos) não encontrados em dados_full"
        print("Erro: Dados das peças usadas COS não encontrados.")
        #return dados_full

    # Converte parts para um formato comparável (código: quantidade), mesmo que vazio
    gspn_parts = {codigo: int(info["quantity"]) for codigo, info in parts.items()} if parts else {}

    # Converte used_parts_cos para um formato comparável (código: quantidade)
    cos_parts = {codigo: info["quantidade"] for codigo, info in used_parts_cos.items()}

    # Listas para peças a remover e adicionar
    parts_to_remove = []
    parts_to_add = []

    # Identifica peças para remover (presentes em gspn_parts mas não em cos_parts ou com quantidade divergente)
    for codigo, quantidade_gspn in gspn_parts.items():
        seq_no = parts[codigo]["seq_no"]  # Obtém o seq_no correspondente
        if codigo not in cos_parts:
            parts_to_remove.append({"codigo": codigo, "seq_no": seq_no})
        elif quantidade_gspn != cos_parts[codigo]:
            parts_to_remove.append({"codigo": codigo, "seq_no": seq_no})
            # Verifica se a peça tem delivery antes de adicionar
            if "delivery" in used_parts_cos[codigo] and used_parts_cos[codigo]["delivery"]:
                parts_to_add.append({
                    "codigo": codigo,
                    "quantidade": cos_parts[codigo],
                })

    # Identifica peças para adicionar (presentes em cos_parts mas ausentes ou insuficientes em gspn_parts)
    for codigo, quantidade_cos in cos_parts.items():
        # Só processa se tiver delivery
        if "delivery" not in used_parts_cos[codigo] or not used_parts_cos[codigo]["delivery"]:
            continue
            
        if codigo not in gspn_parts:
            parts_to_add.append({
                "codigo": codigo,
                "quantidade": quantidade_cos,
            })
        elif gspn_parts[codigo] < quantidade_cos:
            diferenca = quantidade_cos - gspn_parts[codigo]
            parts_to_add.append({
                "codigo": codigo,
                "quantidade": diferenca,
            })

    # Incrementa as listas em dados_full
    dados_full["parts_to_remove"] = parts_to_remove
    dados_full["parts_to_add"] = parts_to_add
    #print("Peças a remover:", parts_to_remove)

    return dados_full

def consulta_part_list_gspn(model):
    """
    Faz uma consulta ao portal Samsung GSPN e retorna uma lista de peças filtradas.
    
    Parâmetros:
    - model (str): Código do modelo (ex: "SM-S918BZKSZTO").
    
    Retorna:
    - dict: Dicionário com a chave 'part_list_gspn' contendo a lista de peças filtradas.
    """
    
    # Caminho do arquivo de cookies
    cookie_file = "C:\\Users\\Gestão MX\\Documents\\AutoMX\\cookies_temp.json"
    
    # Verifica se o arquivo de cookies existe
    if not os.path.exists(cookie_file):
        print(f"Erro: O arquivo {cookie_file} não foi encontrado.")
        return {
            "part_list_gspn": [],
            "error": f"Arquivo de cookies não encontrado: {cookie_file}"
        }
    
    # Carrega e filtra os cookies
    try:
        with open(cookie_file, "r") as f:
            cookies_list = json.load(f)
        cookies = {c["name"]: c["value"] for c in cookies_list if c.get("domain") in ["biz6.samsungcsportal.com", ".samsungcsportal.com"]}
        #print("Cookies carregados e filtrados:", cookies)
    except Exception as e:
        print(f"Erro ao carregar cookies: {e}")
        return {
            "part_list_gspn": [],
            "error": f"Erro ao carregar cookies: {str(e)}"
        }

    # URL do endpoint
    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    
    # Cabeçalhos da requisição
    headers = {
        "Host": "biz6.samsungcsportal.com",
        "Connection": "keep-alive",
        "X-Prototype-Version": "1.7.2",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
        "sec-ch-ua-mobile": "?0",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://biz6.samsungcsportal.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Referer": "https://biz6.samsungcsportal.com/master/part/PartListByModelVersion.jsp?search_status=&searchContent=&menuBlock=&menuUrl=&naviDirValue=",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    # Dados da requisição com valores fixos
    payload = {
        "cmd": "PartListByModelVersionCmd",
        "numPerPage": "100",
        "currPage": "0",
        "CicCorpCode": "C820",
        "Version": "0001",
        "serialNumber": "",
        "piExtFlag": "X",
        "marketingName": "",
        "Model": model,
        "serialHA": "",
        "partNo": "",
        "partDesc": "",
        "partLoc": ""
    }
    
    # Faz a requisição POST
    try:
        response = requests.post(url, headers=headers, data=payload, cookies=cookies, verify=False)
        response.raise_for_status()  # Levanta exceção para códigos de status HTTP 4xx/5xx
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição: {e}")
        return {
            "part_list_gspn": [],
            "error": f"Erro na requisição: {str(e)}"
        }
    
    # Processa a resposta
    try:
        data = response.json()
        if data.get("retcode") == "S" and data.get("success"):
            # Filtra os dados para capturar apenas matnr, maktx e avayn
            part_list = [
                {
                    "matnr": item["matnr"],
                    "maktx": item["maktx"],
                    "avayn": item["avayn"]
                }
                for item in data["dataLists"]
            ]
            return {
                "part_list_gspn": part_list,
                "error": None
            }
        else:
            print("Erro na resposta da API: ", data.get("retmsg"))
            return {
                "part_list_gspn": [],
                "error": f"Erro na resposta da API: {data.get('retmsg')}"
            }
    except ValueError as e:
        print(f"Erro ao parsear JSON: {e}")
        return {
            "part_list_gspn": [],
            "error": f"Erro ao parsear JSON: {str(e)}"
        }

def consultar_delivery(dados_full):
    # URL base fixa (sem parâmetros na URL)
    url = "https://biz6.samsungcsportal.com/gspn/operate.do"
    
    # Headers fixos baseados no exemplo
    headers_base = {
        "Host": "biz6.samsungcsportal.com",
        "Connection": "keep-alive",
        "X-Prototype-Version": "1.7.2",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-ch-ua": "\"Chromium\";v=\"134\", \"Not:A-Brand\";v=\"24\", \"Microsoft Edge\";v=\"134\"",
        "sec-ch-ua-mobile": "?0",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "text/javascript, text/html, application/xml, text/xml, */*",
        "Content-type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://biz6.samsungcsportal.com",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    # Lista para armazenar os resultados
    resultados = []
    
    # Verifica se 'used_parts_cos' existe em dados_full
    if 'used_parts_cos' not in dados_full or not dados_full['used_parts_cos']:
        return resultados
    
    # Itera sobre cada código em used_parts_cos
    for codigo, info in dados_full['used_parts_cos'].items():
        quantidade = info.get('quantidade')
        primeiro_delivery = info.get('delivery', '')

        # Ignora se não houver delivery ou se estiver vazio
        if not primeiro_delivery:
            continue

        # Monta o Referer dinamicamente
        referer = (
            f"https://biz6.samsungcsportal.com/wty/common/CISInvoiceSearchPop.jsp?"
            f"Part={codigo}&idx=0&partQty={quantidade}&account=0002446971&ascCode=0002446971&type=SO"
        )

        # Adiciona o Referer aos headers
        headers = headers_base.copy()
        headers["Referer"] = referer

        # Payload com todos os campos, fixos e dinâmicos
        payload = {
            "cmd": "DoBalanceSearchCmd",
            "numPerPage": "100",
            "currPage": "0",
            "Part": codigo,
            "StartDate": "",
            "EndDate": "",
            "asc_acctno": "0002446971",
            "partNo": codigo,
            "ASC_CODE": "0002446971",
            "INVOICE_NO": "",
            "PARTS_QTY": quantidade
        }

        try:
            # Faz a requisição POST usando os cookies de dados_full
            response = requests.post(
                url,
                headers=headers,
                data=payload,
                cookies=dados_full.get('cookies', {}),
                verify=False
            )
            
            # Verifica se a requisição foi bem-sucedida
            response.raise_for_status()
            data = response.json()

            # Verifica se há dados na resposta
            if not data.get("success", False) or "etDoData" not in data:
                continue

            deliveries = data["etDoData"]
            if not deliveries:
                continue

            # Procura o delivery correspondente ao primeiro_delivery
            encontrado = False
            for delivery in deliveries:
                vbeln = delivery.get("VBELN")
                posnr = delivery.get("POSNR", "").lstrip("0")  # Remove zeros à esquerda

                if vbeln == primeiro_delivery:
                    resultados.append({
                        "codigo": codigo,
                        "delivery": vbeln,
                        "item_no": posnr
                    })
                    encontrado = True
                    break

            # Se não encontrar o delivery correspondente, pega o primeiro da lista
            if not encontrado:
                primeiro_delivery_resposta = deliveries[0].get("VBELN")
                primeiro_posnr = deliveries[0].get("POSNR", "").lstrip("0")
                resultados.append({
                    "codigo": codigo,
                    "delivery": primeiro_delivery_resposta,
                    "item_no": primeiro_posnr
                })

        except requests.RequestException as e:
            print(f"Erro na requisição para o código {codigo}: {e}")
            continue

    # Adiciona os resultados em dados_full
    dados_full["delivery_resultados"] = resultados
    return dados_full

def coletar_pecas_gspn_total(dados_full):
    """
    Extrai o 'parts_code' e 'seq_no' de uma lista de dicionários aninhados.

    Args:
        dados_full (list): Uma lista de dicionários. Cada dicionário deve conter
                        uma chave 'parts', cujo valor é outro dicionário.
                        Este dicionário interno mapeia um 'parts_code' (chave)
                        para um dicionário de detalhes que inclui uma chave 'seq_no'.

                        Exemplo de estrutura de entrada para um item da lista:
                        {
                            "alguma_outra_chave": "valor",
                            "parts": {
                                "CODIGO1": {
                                    "quantity": 10,
                                    "delivery": "data1",
                                    "gi_posted": True,
                                    "description": "Desc A",
                                    "request_no": "REQ1",
                                    "seq_no": "001",
                                    "gi_date": "data_gi1"
                                },
                                "CODIGO2": {
                                        "quantity": 5,
                                        "delivery": "data2",
                                        "gi_posted": False,
                                        "description": "Desc B",
                                        "request_no": "REQ1",
                                        "seq_no": "002",
                                        "gi_date": None
                                }
                            }
                        }

    Returns:
        list: Uma lista de dicionários, onde cada dicionário contém as chaves
            'codigo' (o parts_code original) e 'seq_no'.

            Exemplo de estrutura de saída correspondente ao exemplo acima:
            [
                {"codigo": "CODIGO1", "seq_no": "001"},
                {"codigo": "CODIGO2", "seq_no": "002"}
            ]
            Se a lista de entrada tiver múltiplos dicionários, a saída
            combinará os resultados de todos eles.
    """
    resultado_final = []

    partes_dict = dados_full['parts']
    # Itera sobre cada código de peça e seus detalhes
    for parts_code, detalhes in partes_dict.items():
    # Verifica se 'seq_no' existe nos detalhes
        if 'seq_no' in detalhes:
            # Cria o novo dicionário no formato desejado
            novo_dict = {
                "codigo": parts_code,
                "seq_no": detalhes['seq_no']
            }
            resultado_final.append(novo_dict)
        # else: Você pode adicionar um tratamento aqui caso 'seq_no' possa faltar
        #      Por exemplo: print(f"Aviso: 'seq_no' não encontrado para parts_code {parts_code}")

    return resultado_final