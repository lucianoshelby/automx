import requests
import json
import sys 
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from cos.login_cos import carregar_sessao
from bs4 import BeautifulSoup
from collections import Counter
from typing import List, Optional # Para type hints



URL_BASE = "http://192.168.25.131:8080/COS_CSO"
URL_BUSCA_COS = f"{URL_BASE}/ControleOrdemServico"
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": "http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept-Encoding": "gzip, deflate"
}
user = "Luciano Oliveira"
session = carregar_sessao(user)
def obter_os_correspondentes(os_input):
    """
    Obtém a OS correspondente (COS ou GSPN) com base no número fornecido.
    - Se os_input tem 10 dígitos (GSPN), retorna a OS do COS (6 dígitos).
    - Se os_input tem 6 dígitos (COS), retorna a OS do GSPN (10 dígitos).
    
    Args:
        session: Sessão HTTP configurada.
        os_input (str): Número da OS (6 ou 10 dígitos).
    
    Returns:
        str or None: O número da OS correspondente ou None em caso de erro.
    """
    # 📌 Verifica o comprimento da entrada
    if len(os_input) not in (6, 10):
        print(f"❌ Entrada inválida! A OS deve ter 6 (COS) ou 10 (GSPN) caracteres. Recebido: {len(os_input)}")
        return None

    # 📌 Determina a direção da consulta
    if len(os_input) == 10:

        params_key = "OSFabricante"
        params_value = f"OSFabricante={os_input}"
        return_key = "NumeroOS"
    else:  # len(os_input) == 6

        params_key = "OSInterna"
        params_value = f"NumeroOS={os_input}"  # Formato correto: NumeroOS=<valor>
        return_key = "OSFabricante"

    # 📌 Parâmetros base da requisição
    params = {
        "Acao": "BuscarOSResumo",
        "IDUsuario": "1417",
        "IP": "192.168.25.216",  # Corrigido para o IP da requisição fornecida
        "OSInterna": "",
        "OSFabricante": "",
        "IDunico": "",
        "Serial": "",
        "IMEI": "",
        "IDModeloProduto": "",
        "TipoDeAtendimento": "",
        "Status": "",
        "DataInicial": "",
        "DataFinal": "",
        "OSManual": "",
        "SelectTipoDeServico": "",
        "TipoData1": "DataEntrada",
        "SelectTipoSeguro": ""
    }

    # 📌 Define o parâmetro correto baseado na direção
    params[params_key] = params_value

    # 📌 Enviando requisição GET
    response = session.get(URL_BUSCA_COS, headers=HEADERS, cookies=session.cookies, params=params, verify=False)

    if response.status_code == 200:
        try:
            # 📌 Processando JSON
            dados_json = response.json()

            if "ResumoOrdemServico" in dados_json and dados_json["ResumoOrdemServico"]:
                os_data = dados_json["ResumoOrdemServico"][0]  # Primeiro item da lista

                # 📌 Obtém o valor correspondente
                os_correspondente = os_data.get(return_key, "Não encontrado")
                
                if os_correspondente == "Não encontrado":
                    print(f"⚠️ Campo {return_key} não encontrado na resposta.")
                    return None
                
                
                print(f"✅ OS correspondente encontrada: {os_correspondente}")

                return os_correspondente
            else:
                print("⚠️ Nenhuma OS correspondente encontrada.")
                return None
        except requests.exceptions.JSONDecodeError:
            print("❌ Erro ao processar resposta JSON.")
            return None
    else:
        print(f"❌ Erro ao acessar a página: {response.status_code}")
        return None

    
def coletar_dados_os(os_numero):
    """Coleta todas as informações da OS no COS, incluindo status, tipo de atendimento e peças."""

    if len(os_numero) == 10:
        os_cos = obter_os_correspondentes(os_numero)
        os_numero = os_cos
    print(f"🔍 Buscando dados da OS: {os_numero}")
    dados_os = {
        "status_os": "Não encontrado",
        "tipo_atendimento": "Não encontrado",
        "pecas_requisitadas": [],
        "pecas_gspn": [],
        "pecas_usadas": [],
        "pecas_cotacao": [],
        "orcamento_aprovado": [],
        "tecnico": "",
    }

    # ✅ Buscar Status e Tipo de Atendimento
    url_status = f"{URL_BASE}/ControleOrdemServico?Acao=BuscarOSEdicao&NumeroOSBusca={os_numero}&IDUsuario=1417&IP=192.168.25.14"
    response_status = session.get(url_status, headers=HEADERS, cookies=session.cookies, verify=False)
    if response_status.status_code == 200:
        try:
            dados_json = response_status.json()
            os_dados = dados_json.get("OrdemServicoEdicao", {})
            if os_dados:
                dados_os["status_os"] = os_dados.get("DescricaoStatus", "Não encontrado")
                dados_os["tipo_atendimento"] = os_dados.get("DescricaoAtendimento", "Não encontrado")
                dados_os["tecnico"] = os_dados.get("NomeTecnico")
                dados_os["data_entrada"] = os_dados.get("DataEntrada", "Não encontrado")
                dados_os["LinhaProduto"] = os_dados.get("LinhaProduto", "Não encontrado")
                dados_os["descricaoSeguro"] = os_dados.get("descricaoSeguro", "Não encontrado")
                dados_os["atendente"] = os_dados.get("NomeUsuario", "Não encontrado")
                dados_os["Serial"] = os_dados.get("Serial", "Não encontrado")
                dados_os["IMEI"] = os_dados.get("IMEI", "Não encontrado")
                dados_os["Acessorios"] = os_dados.get("Acessorios", "Não encontrado")
                dados_os["Defeito"] = os_dados.get("Defeito", "Não encontrado")
                dados_os["CondicoesProduto"] = os_dados.get("CondicoesProduto", "Não encontrado")
                dados_os["modelo_completo"] = os_dados.get("CodigoModeloGSPN", "Não encontrado")
                dados_os["cpf"] = os_dados.get("IdUnico", "Não encontrado")
                dados_os["CodigoStatus"] = os_dados.get("TB_Status_CodigoStatus", "Não encontrado")
                dados_os["CodigoMotivo"] = os_dados.get("TB_Motivo_CodigoMotivo", "Não encontrado")
                dados_os["TipoAtendimento"] = os_dados.get("TB_TipoAtendimento_CodigoAtendimento", "Não encontrado")
        except json.JSONDecodeError:
            print("⚠️ Erro ao processar JSON de status e atendimento.")

    # ✅ Buscar Peças Requisitadas
    url_pecas_req = f"{URL_BASE}/ControleEstoque?Acao=BuscarDadosRequisicaoEstoquePorOS&NumeroOS={os_numero}"
    response_pecas_req = session.get(url_pecas_req, headers=HEADERS, cookies=session.cookies, verify=False)
    
    if '{"ListaEstoque":null}' not in response_pecas_req.text:
        try:
            dados_json = response_pecas_req.json()
            lista_requisicoes = dados_json.get("ListaEstoque", [])
            for requisicao in lista_requisicoes:
                lista_pecas = requisicao.get("ListaPecas", None)
                if lista_pecas:
                    for peca in lista_pecas:
                        dados_os["pecas_requisitadas"].append({
                            "codigo": peca["CodigoPeca"],
                            "descricao": peca["DescricaoPeca"],
                            "qtd": peca["QtdPeca"]
                        })
        except json.JSONDecodeError:
            print("⚠️ Erro ao processar JSON de peças requisitadas.")

    # ✅ Buscar Peças Usadas
    url_pecas_usadas = f"{URL_BASE}/ControleEstoque?Acao=BuscarPecaInseridaNaOS&NumeroOS={os_numero}"
    response_pecas = session.get(url_pecas_usadas, headers=HEADERS, cookies=session.cookies, verify=False)
    if response_pecas.status_code == 200:
        try:
            dados_json = response_pecas.json()
            pecas = dados_json.get("DadosPeca", [])
            if pecas:
                for p in pecas:
                    dados_os["pecas_usadas"].append({
                        "codigo": p["CodigoPeca"],
                        "descricao": p["DescricaoPeca"],
                        "delivery": p.get("Delivery", "Não especificado")
                    })
                
        except json.JSONDecodeError:
            print("⚠️ Erro ao processar JSON de peças usadas.")

    # ✅ Buscar Peças Pedidas no GSPN
    url_pecas_gspn = f"{URL_BASE}/ControlePedidoPecaGSPN?Acao=BuscarPecaInseridaNaOSGSPN&NumeroOS={os_numero}"
    response_pecas_gspn = session.get(url_pecas_gspn, headers=HEADERS, cookies=session.cookies, verify=False)
    
    if response_pecas_gspn.status_code == 200:
        try:
            dados_json = response_pecas_gspn.json()
            pecas = dados_json.get("DadosPeca", None)
            
            if pecas:
                for p in pecas:
                    status = p.get("DescricaoStatusPedidoPecaGSPN", "").lower()
                    dados_os["pecas_gspn"].append({
                        "codigo": p["CodigoPeca"],
                        "descricao": p["DescricaoPeca"],
                        "status": status
                    })
        except json.JSONDecodeError:
            print("⚠️ Erro ao processar JSON de peças do GSPN.")
        # ✅ Buscar Peças na Cotação
    url_cotacao = f"{URL_BASE}/QuotationControl?&cmd=getQuotationData&so={os_numero}&modelCodeId=null&userId=1417&ip=192.168.24.39"
    response_cotacao = session.get(url_cotacao, headers=HEADERS, cookies=session.cookies, verify=False)
    
    if response_cotacao.status_code == 200:
        try:
            dados_json = response_cotacao.json()
            if dados_json.get("success") == True:
                # Extrair dados do orçamento
                info = dados_json.get("info", {})
                
                # Obter status de aprovação do orçamento
                so_dados = info.get("so", {})
                dados_os["orcamento_aprovado"] = so_dados.get("approvedQuotation", False)
                
                # Obter peças da cotação
                itens_cotacao = info.get("quotationItens", [])
                for item in itens_cotacao:
                    part_info = item.get("part", {})
                    dados_os["pecas_cotacao"].append({
                        "codigo": part_info.get("code", ""),
                        "id": part_info.get("description", ""),
                        "qtd": item.get("qty", 0)
                    })
                #print(itens_cotacao)
        except json.JSONDecodeError:
            print("⚠️ Erro ao processar JSON das peças da cotação.")    
    return dados_os




# Funções de coleta de peças
def coletar_pecas_totais(os):
    url = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServicoGSPN"
    params = {"Acao": "ListarPecasParaSAW", "numeroOS": os}
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/SolicitarSAW.jsp?NumeroOS={os}&tipoServico=BAL&motivoOS=S02",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        return {item["keyName"]: item["text"] for item in data}
    except Exception as e:
        print(f"Erro ao coletar peças totais: {e}")
        return {}

def coletar_pecas_usadas(os):
    url = "http://192.168.25.131:8080/COS_CSO/ControleEstoque"
    params = {"Acao": "BuscarPecaInseridaNaOS", "NumeroOS": os}
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?NumeroOSBusca={os}",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        pecas_usadas = {}
        for item in data.get("DadosPeca", []):
            key = item["TB_Peca_IDCodigoPeca"]
            pecas_usadas[key] = {
                "keyname": key,
                "code": item["CodigoPeca"],
                "segunda_descricao": item["SegundaDescricaoPeca"]
            }
        return pecas_usadas
    except Exception as e:
        print(f"Erro ao coletar peças usadas: {e}")
        return {}

def coletar_pecas_orcamento(os):
    url = "http://192.168.25.131:8080/COS_CSO/QuotationControl"
    params = {"cmd": "getQuotationData", "so": os, "modelCodeId": "null", "userId": "1417", "ip": "192.168.25.216"}
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/new/so/Quotation.jsp?so={os}",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        quotation_itens = data.get("info", {}).get("quotationItens", [])
        pecas_orcamento = []
        for item in quotation_itens:
            part = item.get("part", {})
            coverage = item.get("coverage", {})
            if part.get("id") and part.get("code"):
                pecas_orcamento.append({
                    "keyname": part.get("id", ""),
                    "code": part.get("code", ""),
                    "coverage_id": coverage.get("id", "")
                })
        return pecas_orcamento
    except Exception as e:
        print(f"Erro ao coletar peças do orçamento: {e}")
        return []
def filtrar_dados_saw(os, category):
    pecas_totais = coletar_pecas_totais(os)
    pecas_usadas = coletar_pecas_usadas(os)
    pecas_pre_preenchidas = {}
    alerta = ""

    if category == "pecas_cosmeticas":
        todos_none = True
        for key, peca in pecas_usadas.items():
            defeito = definir_defeito_cosmetico(peca["segunda_descricao"])
            if defeito is not None:
                pecas_pre_preenchidas[key] = {
                    "keyname": peca["keyname"],
                    "code": peca["code"],
                    "defeito": defeito,
                    "ow": False
                }
                todos_none = False
        if todos_none:
            pecas_pre_preenchidas = {key: {"keyname": p["keyname"], "code": p["code"], "defeito": p["segunda_descricao"], "ow": False}
                                     for key, p in pecas_usadas.items()}

    elif category == "oxidacao":
        for key, peca in pecas_usadas.items():
            defeito = definir_defeito(peca["segunda_descricao"])
            if defeito is not None:
                pecas_pre_preenchidas[key] = {
                    "keyname": peca["keyname"],
                    "code": peca["code"],
                    "defeito": defeito,
                    "ow": False
                }

    elif category == "os_mista":
        pecas_orcamento = coletar_pecas_orcamento(os)
        if pecas_orcamento:
            # Processar peças usadas com base no orçamento
            for key, peca in pecas_usadas.items():
                orcamento_peca = next((p for p in pecas_orcamento if p["keyname"] == key), None)
                if orcamento_peca:
                    if orcamento_peca["coverage_id"] == "ORC":
                        defeito = definir_defeito_mista_ow(peca["segunda_descricao"])
                        ow = True
                    elif orcamento_peca["coverage_id"] == "GAR":
                        defeito = definir_defeito(peca["segunda_descricao"])
                        ow = False
                    else:
                        defeito = definir_defeito(peca["segunda_descricao"]) or ""  # Caso coverage_id não seja ORC nem GAR
                        ow = False
                else:
                    defeito = "PEÇA FORA DO ORÇAMENTO"
                    ow = False
                
                if defeito is not None:
                    pecas_pre_preenchidas[key] = {
                        "keyname": peca["keyname"],
                        "code": peca["code"],
                        "defeito": defeito,
                        "ow": ow
                    }
            # Adicionar peças do orçamento que não estão em usadas
            for peca in pecas_orcamento:
                if peca["keyname"] not in pecas_usadas:
                    if peca["coverage_id"] == "ORC":
                        defeito = definir_defeito_mista_ow("") or ""
                        ow = True
                    elif peca["coverage_id"] == "GAR":
                        defeito = definir_defeito("") or ""
                        ow = False
                    else:
                        defeito = definir_defeito("") or ""
                        ow = False
                    pecas_pre_preenchidas[peca["keyname"]] = {
                        "keyname": peca["keyname"],
                        "code": peca["code"],
                        "defeito": defeito,
                        "ow": ow
                    }
            # Verificar divergência
            usadas_keys = set(pecas_usadas.keys())
            orcamento_keys = set(p["keyname"] for p in pecas_orcamento)
            if usadas_keys != orcamento_keys:
                alerta = "Atenção, o orçamento está divergente com as peças inseridas!"
        else:
            # Sem orçamento, usar definir_defeito
            for key, peca in pecas_usadas.items():
                defeito = definir_defeito(peca["segunda_descricao"])
                if defeito is not None:
                    pecas_pre_preenchidas[key] = {
                        "keyname": peca["keyname"],
                        "code": peca["code"],
                        "defeito": defeito,
                        "ow": False
                    }

    else:  # Uso excessivo de peças
        for key, peca in pecas_usadas.items():
            defeito = definir_defeito(peca["segunda_descricao"])
            if defeito is not None:
                pecas_pre_preenchidas[key] = {
                    "keyname": peca["keyname"],
                    "code": peca["code"],
                    "defeito": defeito,
                    "ow": False
                }

    return {
        "pecas_totais": pecas_totais,
        "pecas_pre_preenchidas": pecas_pre_preenchidas,
        "alerta": alerta
    }

def definir_defeito(descricao):
    descricao_lower = descricao.lower()
    
    if "repair kit" in descricao_lower or "tape" in descricao_lower:
        return None  # Ignorar essa peça
    if "vinyl" in descricao_lower or "protector" in descricao_lower:
        return "Troca obrigatória"
    if "pba main" in descricao_lower or "pba-main" in descricao_lower:
        return "NÃO LIGA"
    if any(term in descricao_lower for term in ["octa assy","octa-assy", "front-bt", "front-lte", "sub ub", "mea front-sm-r", "lcd", "sub oled", "smt-octa", "assy-oled", "main display", "main ub", "assy oled"]):
        return "SEM IMAGEM"
    if "batt" in descricao_lower or "battery" in descricao_lower:
        return "TROCA OBRIGATÓRIA"
    if ("if pba" in descricao_lower or "sub pba" in descricao_lower) and not any(term in descricao_lower for term in ["fpcb", "camera", "volume", "frc", "ctc"]):
        return "NÃO CARREGA"
    if any(term in descricao_lower for term in ["fpcb", "frc", "ctc", "con to con", "con-to-con"]):
        return "MAL CONTATO"
    if "camera" in descricao_lower:
        return "NÃO FOCA"
    if any(term in descricao_lower for term in ["case-front", "case-rear", "metal front", "front module", "aro"]):
        return "FALHA DE REDE (ANTENA)"
    if any(term in descricao_lower for term in ["cover-back", "back cover", "back glass", "svc cover"]):
        return "DESCASCOU NA ABERTURA"
    return "Defeito desconhecido"  # Agora retorna None se não se encaixar em nenhuma regra

def definir_defeito_cosmetico(descricao):
    descricao_lower = descricao.lower()
    
    if "repair kit" in descricao_lower or "tape" in descricao_lower:
        return None  # Ignorar essa peça
    if "vinyl" in descricao_lower or "protector" in descricao_lower:
        return None
    if any(term in descricao_lower for term in ["case-front", "case-rear", "metal front", "front module", "aro"]):
        return "FALHA DE REDE (ANTENA)"
    if any(term in descricao_lower for term in ["cover-back", "back cover", "back glass", "svc cover", ]):
        return "DESCASCOU NA ABERTURA"
    return None  # Agora retorna None se não se encaixar em nenhuma regra


def definir_defeito_mista_ow(descricao):
    descricao_lower = descricao.lower()
    
    if "repair kit" in descricao_lower or "tape" in descricao_lower:
        return None  # Ignorar essa peça
    if "vinyl" in descricao_lower or "protector" in descricao_lower:
        return "Troca obrigatória"
    if "pba main" in descricao_lower or "pba-main" in descricao_lower:
        return "OXIDAÇÃO"
    if any(term in descricao_lower for term in ["octa assy", "front-bt", "front-lte", "sub ub", "mea front-sm-r", "lcd", "sub oled", "smt-octa", "assy-oled", "main display", "main ub", "assy oled"]):
        return "TRINCADO"
    if "batt" in descricao_lower or "battery" in descricao_lower:
        return "TROCA OBRIGATÓRIA"
    if ("if pba" in descricao_lower or "sub pba" in descricao_lower) and not any(term in descricao_lower for term in ["fpcb", "camera", "volume", "frc", "ctc"]):
        return "OXIDAÇÃO"
    if any(term in descricao_lower for term in ["fpcb", "frc", "ctc", "con to con", "con-to-con"]):
        return "OXIDAÇÃO"
    if "camera" in descricao_lower:
        return "DANO POR IMPACTO"
    if any(term in descricao_lower for term in ["case-front", "case-rear", "metal front", "front module", "aro"]):
        return "DANO POR IMPACTO"
    if any(term in descricao_lower for term in ["cover-back", "back cover", "back glass", "svc cover", "deco cam", "window display-2d_cam"]):
        return "TRINCADO"
    return "Defeito desconhecido"  # Agora retorna None se não se encaixar em nenhuma regra

def coletar_usadas_cos(dados_full):
    """
    Coleta as peças usadas associadas à OS de uma fonte externa e incrementa em dados_full.
    
    Args:
        dados_full (dict): Dicionário contendo 'object_id' e possivelmente outros dados.
    
    Returns:
        dict: Dicionário dados_full atualizado com 'used_parts_cos'.
    """
    # Extrai o número da OS de dados_full
    os_cos = dados_full.get("object_id")
    
    if not os_cos:
        dados_full["error"] = "Número da OS (object_id) não encontrado em dados_full"
        return dados_full

    # Função original coletar_dados_os (mantida como estava, assumindo que está definida Elsewhere)
    dados_os = coletar_dados_os(os_cos)
    #print(f'Dados coletados: {dados_os}')
    
    # Contar a quantidade de cada peça usada e armazenar o primeiro delivery
    contador_pecas = Counter()
    primeiro_delivery = {}
    
    for p in dados_os['pecas_usadas']:
        codigo = p['codigo']
        contador_pecas[codigo] += 1
        # Verifica se já registrou um delivery para este código
        if codigo not in primeiro_delivery:
            primeiro_delivery[codigo] = p['delivery']
    
    # Exibir no console o código, a quantidade de cada peça usada, e o primeiro delivery
    #for codigo, quantidade in contador_pecas.items():
        #print(f"Código: {codigo}, Quantidade: {quantidade}, Delivery: {primeiro_delivery[codigo]}")
    
    # Preparar os dados finais a serem retornados
    resultado_final = {
        codigo: {
            'quantidade': quantidade,
            'delivery': primeiro_delivery[codigo]
        } for codigo, quantidade in contador_pecas.items()
    }
    
    

    # Incrementa o resultado em dados_full
    dados_full["used_parts_cos"] = resultado_final

    return dados_full
def verificar_saw_pendente(numero_os, categoria):
    """
    Verifica se a OS possui uma SAW pendente da mesma categoria.
    Args:
        numero_os (str): Número da Ordem de Serviço.
        categoria (str): Categoria da SAW no formato do frontend (ex.: 'os_mista').
    Returns:
        bool: True se não houver SAW pendente, False se houver.
    """
    
    url = "http://192.168.25.131:8080/COS_CSO/SawControl"
    
    # Mapeamento das categorias do frontend para os códigos do backend
    categoria_map = {
        "oxidacao": "SRC73",
        "uso_excessivo": "SRC29",
        "os_mista": "SRC29",
        "pecas_cosmeticas": "SRZ15"
    }
    categoria_saw = categoria_map.get(categoria, "SRC29")  # Default para SRC29 se não mapeado

    params = {
        "acao": "verificarSePossuiSAWAbertoParaOS",
        "IP": "192.168.25.216",
        "IDUsuario": "1417",
        "NumeroOS": numero_os,
        "CategoriaSAW": categoria_saw  # Usa o código mapeado diretamente
    }

    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/SolicitarSAW.jsp?NumeroOS={numero_os}&tipoServico=BAL&motivoOS=S02",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = session.get(url, params=params, headers=headers)
        print(response.text)
        response.raise_for_status()
        result = response.json()
        
        # Verifica a resposta esperada
        if result.get("Sucesso", True) and result.get("Mensagem") == "Ok":
            return True  # Não há SAW pendente
        elif not result.get("Sucesso", False) and result.get("Mensagem") == "Já possui SAW dessa categoria em aberto":
            return False  # Há SAW pendente
        else:
            print(f"Resposta inesperada ao verificar SAW: {result}")
            return False  # Tratar como pendente por segurança
    except Exception as e:
        print(f"Erro ao verificar SAW pendente: {e}")
        return False  # Tratar erro como pendente por segurança
    

def coletar_pecas_orcamento(os):
    """
    Faz a requisição para coletar peças do orçamento da OS.
    Retorna uma lista de dicionários com keyname (equivalente a part.id), code e coverage_id, apenas para peças.
    """
    
    url = "http://192.168.25.131:8080/COS_CSO/QuotationControl"
    params = {
        "cmd": "getQuotationData",
        "so": os,
        "modelCodeId": "null",
        "userId": "1417",
        "ip": "192.168.25.216"
    }
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/new/so/Quotation.jsp?so={os}",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    try:
        response = session.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
        quotation_itens = data.get("info", {}).get("quotationItens", [])
        pecas_orcamento = []

        for item in quotation_itens:
            part = item.get("part", {})
            coverage = item.get("coverage", {})
            if part.get("id") and part.get("code"):  # Ignora serviços
                pecas_orcamento.append({
                    "keyname": part.get("id", ""),  # Equivalente a keyName e TB_Peca_IDCodigoPeca
                    "code": part.get("code", ""),
                    "coverage_id": coverage.get("id", ""),
                    "qtd": item.get("qty", 0),  # Adiciona a quantidade
                    "description": part.get("description", "")  # Adiciona a descrição
                })

        print(f"Peças do orçamento coletadas para OS {os}: {len(pecas_orcamento)} itens")
        print(f"Peças: {pecas_orcamento}")
        return pecas_orcamento
    except Exception as e:
        print(f"Erro ao coletar peças do orçamento para OS {os}: {e}")
        return []


def coletar_pecas_requisitar(os):
    """
    Filtra as peças do orçamento que serão requisitadas.
    """
    if len(os) == 10:
        os_cos = obter_os_correspondentes(os)
        os = os_cos
    dados_os = coletar_dados_os(os)
    print(f'Dados coletados: {dados_os}')
    pecas_orcamento = coletar_pecas_orcamento(os)
    pecas_usadas = dados_os.get('pecas_usadas', [])
    orcamento = dados_os.get('orcamento_aprovado', "Não informado")
    status_os = dados_os.get('status_os', "Não informado")
    tecnico = dados_os.get('tecnico', "Não informado")

    # Extrai os códigos das peças já usadas
    codigos_usados = {peca['codigo'] for peca in pecas_usadas if 'codigo' in peca}

    pecas_requisitar = []
    pecas_ja_inseridas = []

    for peca in pecas_orcamento:
        # Verifica se o dicionário está vazio ou sem código
        if not peca or 'code' not in peca or not peca['code']:
            continue  # Pula itens inválidos
        
        if peca['code'] not in codigos_usados:
            pecas_requisitar.append(peca)
        else:
            pecas_ja_inseridas.append(peca)

    pecas_filtradas = {
        'pecas_requisitar': pecas_requisitar,
        'pecas_ja_inseridas': pecas_ja_inseridas,
        'orcamento': orcamento,
        'status_os': status_os,
        'tecnico': tecnico
    }
    print(f'peças filtradas: {pecas_filtradas}')
    return pecas_filtradas

def consultar_id_tecnico_cos(nome_tecnico):
    """
    Consulta o ID de um técnico no sistema COS pelo seu nome completo.

    Faz uma requisição GET para buscar todos os usuários e procura pelo nome
    fornecido no campo 'NomePessoa' da resposta. Retorna o 'IDUsuario' correspondente.

    Args:
        session: Objeto de sessão requests pré-configurado.
        nome_tecnico: O nome completo do técnico a ser consultado (case-insensitive).

    Returns:
        O IDUsuario (string) do técnico se encontrado, ou None caso contrário
        (não encontrado ou erro na requisição/processamento).
    """
    url = "http://192.168.25.131:8080/COS_CSO/ControleUsuario"

    # Parâmetros da requisição GET (fixos neste caso)
    params = {
        "Acao": "BuscarDadosUsuario"
    }

    # Cabeçalhos da requisição (fixos neste caso)
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://192.168.25.131:8080/COS_CSO/EditarUsuario.jsp", # Fixo conforme exemplo
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        # O Cookie JSESSIONID será gerenciado pela session do requests
    }

    try:
        # print(f"[*] Headers: {headers}") # Descomente se precisar depurar headers

        response = session.get(url, params=params, headers=headers, timeout=45) # Timeout aumentado um pouco
        response.raise_for_status() # Verifica erros HTTP

        resposta_texto = response.text

        # --- Tratamento da Resposta ---
        # A resposta de exemplo tem um número e newline antes do JSON.
        # Precisamos encontrar o início do JSON '{'.
        inicio_json = resposta_texto.find('{')
        if inicio_json == -1:
            print("[-] Erro: Não foi possível encontrar o início do JSON na resposta.")
            print(f"[*] Conteúdo da Resposta (início):\n{resposta_texto[:200]}...") # Mostra início da resposta
            return None

        json_string = resposta_texto[inicio_json:]

        # Tenta decodificar a string JSON extraída
        try:
            dados_resposta = json.loads(json_string)
            lista_usuarios = dados_resposta.get('ListaUsuario', [])
            usuario_completo = []
            if not lista_usuarios:
                print("[-] Aviso: A lista de usuários na resposta está vazia ou não foi encontrada.")
                return None

            # Procura pelo nome do técnico na lista (case-insensitive)
            nome_tecnico_lower = nome_tecnico.lower()
            for usuario in lista_usuarios:
                # Verifica se 'NomePessoa' existe e compara
                nome_pessoa = usuario.get("NomePessoa")
                if nome_pessoa and nome_pessoa.lower() == nome_tecnico_lower:
                    id_usuario = usuario.get("IDUsuario")
                    login_usuario = usuario.get("NomeUsuario")
                    usuario_completo.append(usuario.get("NomeUsuario"))
                    usuario_completo.append(usuario.get("IDUsuario"))
                    # Verifica se o IDUsuario existe
                    if id_usuario:
                        print(f"[+] Técnico '{nome_tecnico}' encontrado. IDUsuario: {id_usuario}")
                        return usuario_completo # Retorna o ID como string
                    else:
                        print(f"[-] Aviso: Técnico '{nome_tecnico}' encontrado, mas sem IDUsuario no registro.")
                        # Continua procurando caso haja duplicatas, mas uma tenha ID

            # Se o loop terminar sem encontrar
            print(f"[-] Técnico '{nome_tecnico}' não encontrado na lista de usuários.")
            return None

        except json.JSONDecodeError as e:
            print(f"[-] Erro ao decodificar JSON da resposta: {e}")
            print(f"[*] String JSON processada (início):\n{json_string[:200]}...")
            return None
        # -----------------------------

    except requests.exceptions.RequestException as e:
        print(f"[!] Erro durante a requisição HTTP: {e}")
        return None
    except Exception as e:
        print(f"[!] Erro inesperado na função consultar_id_tecnico_cos: {e}")
        return None


def obter_ids_requisicoes_pendentes(numero_os: str) -> Optional[List[str]]:
    """
    Consulta as requisições de uma OS e retorna os IDs daquelas com status "Pendente".

    Args:
        session: Objeto de sessão requests pré-configurado.
        numero_os: O número da Ordem de Serviço (como string) para consulta.

    Returns:
        Uma lista contendo os IDs ("NumeroOSUso") das requisições pendentes.
        Retorna None se não houver requisições, nenhuma estiver pendente,
        ou em caso de erro na consulta/processamento.
    """
    url = "http://192.168.25.131:8080/COS_CSO/ControleEstoque"
    params = {
        "Acao": "BuscarDadosRequisicaoEstoquePorOS",
        "NumeroOS": numero_os
    }
    referer_url = f"http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?RequisitarAlteracaoOS=S&NumeroOSBusca={numero_os}"
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0", # Ajuste se necessário
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer_url,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        # Cookies são geralmente gerenciados pelo objeto 'session'
    }

    try:
        print(f"[*] Consultando requisições pendentes para a OS: {numero_os}")
        response = session.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)
        print(f"[*] Resposta Recebida (Status: {response.status_code})")

        try:
            dados_resposta = response.json()
            lista_requisicoes = dados_resposta.get("ListaEstoque")

            # Verifica se a lista existe e é realmente uma lista válida
            if lista_requisicoes is None:
                print(f"[*] Nenhuma requisição encontrada para a OS {numero_os} (ListaEstoque: null).")
                return None
            if not isinstance(lista_requisicoes, list):
                 print(f"[-] Erro: 'ListaEstoque' não é uma lista válida na resposta para OS {numero_os}.")
                 return None
            if not lista_requisicoes: # Lista vazia []
                print(f"[*] Nenhuma requisição encontrada para a OS {numero_os} (ListaEstoque: []).")
                return None

            # Lista para armazenar os IDs das requisições pendentes
            ids_pendentes = []

            # Itera sobre cada requisição na lista
            for requisicao in lista_requisicoes:
                status = requisicao.get("DescricaoStatus")
                id_requisicao = requisicao.get("NumeroOSUso")

                # Verifica se o status é "Pendente" e se o ID existe
                if status == "Solicitado" and id_requisicao:
                    # Adiciona o ID à lista (garante que seja string se necessário)
                    ids_pendentes.append(str(id_requisicao))

            # Retorna a lista de IDs se houver alguma pendente, senão retorna None
            if ids_pendentes:
                print(f"[+] IDs das requisições pendentes encontradas para OS {numero_os}: {ids_pendentes}")
                return ids_pendentes
            else:
                print(f"[*] Nenhuma requisição com status 'Pendente' encontrada para a OS {numero_os}.")
                return None

        except json.JSONDecodeError:
            print(f"[-] Erro: A resposta da OS {numero_os} não pôde ser decodificada como JSON.")
            # print(f"[*] Conteúdo da Resposta (início):\n{response.text[:200]}...") # Descomentar para debug
            return None

    except requests.exceptions.RequestException as e:
        print(f"[!] Erro durante a requisição HTTP para OS {numero_os}: {e}")
        return None
    except Exception as e:
        # Captura outros erros inesperados durante o processo
        print(f"[!] Erro inesperado ao processar OS {numero_os}: {e}")
        return None

if __name__ == "__main__":
    # Exemplo de uso
    ids = obter_ids_requisicoes_pendentes("350915")
    if ids:
        print(f"IDs das requisições pendentes: {ids}")
    else:
        print("Nenhuma requisição pendente encontrada ou erro na consulta.")