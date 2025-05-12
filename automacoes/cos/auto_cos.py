import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX')
from automacoes.cos.login_cos import carregar_sessao
import requests
import json
from automacoes.cos.coletar_dados_cos import obter_os_correspondentes, coletar_pecas_requisitar, consultar_id_tecnico_cos, obter_ids_requisicoes_pendentes, coletar_dados_os
from automacoes.coletar_dados import extract_os_data_full, coletar_usadas_cos, comparar_pecas_os, fetch_os_data
from automacoes.pecas import remover_pecas_os
from automacoes.cos.users_cos import listar_nomes_usuarios
from datetime import datetime
import logging
import time

user = "Luciano Oliveira"
session = carregar_sessao(user)
URL_BASE = "http://192.168.25.131:8080/COS_CSO"
HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Referer": "http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Accept-Encoding": "gzip, deflate"
}
def deletar_cos(os_gspn):
    if len(os_gspn) == 6:
        os_cos = os_gspn
        os_gspn = obter_os_correspondentes(os_gspn)
        
    else:
        os_cos = obter_os_correspondentes(os_gspn)
    """Deleta a OS GSPN associada no COS e verifica a confirmação."""
    print(f"🗑️ Iniciando exclusão da OS {os_gspn} no COS...")
    
    url_delete = f"{URL_BASE}/ControleOrdemServicoGSPN?Acao=DeletarOSFabricante&IDUsuario=1417&IP=192.168.25.14&NumeroOS={os_cos}&NumeroOSFabricante={os_gspn}"
    response_delete = session.get(url_delete, headers=HEADERS, cookies=session.cookies, verify=False)
    
    if response_delete.status_code == 200:
        try:
            response_json = response_delete.json()
            if response_json.get("Sucesso"):
                print(f"✅ OS {os_gspn} deletada do COS com sucesso!")
            else:
                print(f"⚠️ Falha ao deletar OS {os_gspn}. Resposta do servidor: {response_json.get('Mensagem', 'Mensagem não disponível')} ")
        except requests.exceptions.JSONDecodeError:
            print("⚠️ Erro ao interpretar a resposta JSON do servidor.")
    else:
        print(f"❌ Falha ao deletar OS {os_gspn}. Código HTTP: {response_delete.status_code}")

def definir_defeito(descricao):
    descricao_lower = descricao.lower()
    
    if "repair kit" in descricao_lower or "tape" in descricao_lower:
        return None  # Ignorar essa peça
    if "vinyl" in descricao_lower or "protector" in descricao_lower:
        return "Troca obrigatória"  # Ignorar peças com esses termos
    if "pba main" in descricao_lower or "pba-main" in descricao_lower:
        return "NÃO LIGA"
    if any(term in descricao_lower for term in ["octa assy", "front-bt", "front-lte", "sub ub", "mea front-sm-r", "lcd", "sub oled", "smt-octa", "assy-oled", "main display", "main ub", "assy oled"]):
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
    return "Defeito desconhecido" 

def coletar_pecas_totais(os):
    """
    Faz a requisição para listar todas as peças compatíveis com a OS.
    Retorna um dicionário com keyname (equivalente a part.id) como chave e text como valor.
    """
    
    url = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServicoGSPN"
    params = {
        "Acao": "ListarPecasParaSAW",
        "numeroOS": os
    }
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
        pecas_totais = {item["keyName"]: item["text"] for item in data}
        print(f"Peças totais coletadas para OS {os}: {len(pecas_totais)} itens")
        return pecas_totais
    except Exception as e:
        print(f"Erro ao coletar peças totais para OS {os}: {e}")
        return {}
    
def coletar_pecas_usadas(os):
    """
    Faz a requisição para coletar peças usadas na OS e combina com peças totais.
    Retorna um dicionário com pecas_totais e pecas_usadas, usando keyname (equivalente a part.id).
    """
    resultado = {"pecas_totais": coletar_pecas_totais(os), "pecas_usadas": {}}
    
    url = "http://192.168.25.131:8080/COS_CSO/ControleEstoque"
    params = {
        "Acao": "BuscarPecaInseridaNaOS",
        "NumeroOS": os
    }
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
            key = item["TB_Peca_IDCodigoPeca"]  # Equivalente a part.id e keyName
            pecas_usadas[key] = {
                "keyname": key,
                "code": item["CodigoPeca"],
                "segunda_descricao": item["SegundaDescricaoPeca"],
                "defeito": definir_defeito(item["SegundaDescricaoPeca"])
            }
        resultado["pecas_usadas"] = pecas_usadas
        print(f"Peças usadas coletadas para OS {os}: {len(pecas_usadas)} itens")
    except Exception as e:
        print(f"Erro ao coletar peças usadas para OS {os}: {e}")
        resultado["pecas_usadas"] = {}

    return resultado

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
                    "coverage_id": coverage.get("id", "")
                })

        print(f"Peças do orçamento coletadas para OS {os}: {len(pecas_orcamento)} itens")
        return pecas_orcamento
    except Exception as e:
        print(f"Erro ao coletar peças do orçamento para OS {os}: {e}")
        return []
    
def filtrar_pecas_req(os):
    """
    Faz a requisição para requisitar peças na OS.
    """
    os_correspondente = obter_os_correspondentes(os)
    if os_correspondente != "Não encontrado" and os_correspondente != None:
        dados_full = fetch_os_data(os_correspondente)
        dados_os = extract_os_data_full(dados_full)
        dados_full.update(dados_os)
        status_os = dados_full["status_os"]
        print(f'Status OS: {status_os}')
        if "ST030" not in status_os and "ST025" not in status_os:
            print(f'Erro: impossível requisitar peças, A OS está fechada ou em reconhecimento')
            return "StatusError"
        pecas_inseridas_cos = coletar_usadas_cos(dados_full)
        dados_full.update(pecas_inseridas_cos)
        try:
            print('Chamando comparar peças...')
            remover = comparar_pecas_os(dados_full)
            
            print(f'Comparar peças retornou: {remover}')
        except Exception as e:
            print(f"Erro ao comparar peças: {e}")
            return False
        print(f'Peças a remover: {remover}')
        dados_full.update(remover)
        #print(f'Peças a remover: {dados_full}')
        pecas_filtradas = coletar_pecas_requisitar(os)
        pecas_requisitar = pecas_filtradas['pecas_requisitar']
        parts_to_remove = dados_full.get('parts_to_remove', [])
        print(f'Peças a remover: {parts_to_remove}')
        logging.info(f'Peças aaaaaa: {remover}')
        logging.info(f'Peças a requisitar: {pecas_requisitar}')
        

        if parts_to_remove:
            return parts_to_remove

    else:
        print('Não há OS correspondente no COS')
    return True

def requisitar_pecas_cos(dados_full):
    """
    Envia uma requisição GET para o sistema COS para requisitar peças para uma Ordem de Serviço.

    Args:
        session: Objeto de sessão requests pré-configurado.
        dados_entrada: Dicionário contendo a lista de peças a requisitar.
                       Formato esperado: {'pecas_requisitar': [{'keyname': 'ID', 'qtd': QTD}, ...]}
        numero_os: O número da Ordem de Serviço (como string).

    Returns:
        True se a requisição foi bem-sucedida e a resposta indica sucesso, False caso contrário.
    """
        
    print('--- Iniciando requisição de peças ---')
    url = "http://192.168.25.131:8080/COS_CSO/PartsRequestControl"
    #dados_entrada = coletar_pecas_requisitar(numero_os)  # Coleta as peças do orçamento
    pecas_para_requisitar = dados_full.get('pecas_a_requisitar', [])
    print(f'Peças para requisitar: {pecas_para_requisitar}') # Lista de peças a requisitar
    numero_os = dados_full.get('ordem_servico')  # Número da OS
    nome_tecnico = dados_full.get('usuario_responsavel') # Nome do técnico
    aviso_status = dados_full.get('status_os')  
    tecnico = consultar_id_tecnico_cos(nome_tecnico)
    session = carregar_sessao(nome_tecnico)  # Coleta o ID do técnico
    id_tecnico = tecnico[1]  # ID do técnico
    pecas_a_remover = dados_full.get('pecas_a_remover_gspn', [])  # Lista de peças a remover
    

    remover_atualizado = []
    

    # Extrair os códigos de pecas_requisitar
    codigos_requisitar = {item['codigo'] for item in pecas_para_requisitar}

    # Gerar remover_atualizado com itens de parts_to_remove cujo codigo está em pecas_requisitar
    remover_atualizado = [
        item for item in pecas_a_remover
        if item['codigo'] in codigos_requisitar
    ]
    dados_full['parts_to_remove'] = remover_atualizado  # Atualiza a lista de peças a remover
    if remover_atualizado:
        try:
            if len(numero_os) != 10:
                os_gspn = obter_os_correspondentes(numero_os)
            html_os = fetch_os_data(os_gspn)
            dados_full.update(html_os)
            remover_pecas_os(dados_full)
        except Exception as e:
            print(f"Erro ao remover peças: {e}")
            return False
    requisicao_pendente = obter_ids_requisicoes_pendentes(numero_os)
    print(f"Requisições pendentes: {requisicao_pendente}")  # Lista de requisições pendentes
    if requisicao_pendente:
        try:
            cancelar_requisicoes_pendentes_cos(requisicao_pendente, numero_os)
        except Exception as e:
            print(f"Erro ao cancelar requisições pendentes: {e}")
            return False
        
    if aviso_status:
        try:
            alterar_status_tecnico_designado_cos(numero_os)
        except Exception as e:
            print(f"Erro ao alterar status técnico designado: {e}")
            return False
    # --- Montagem dos parâmetros preservando a ordem ---
    # Usamos uma lista de tuplas para garantir a ordem exata dos parâmetros na URL,
    # especialmente para os campos repetidos como IDCodigoPeca, qtd e local.
    params_list = [('acao', 'createNewRequest')]

    # 1. Adiciona todos os IDCodigoPeca
    for peca in pecas_para_requisitar:
        params_list.append(('IDCodigoPeca', str(peca.get('keyname', ''))))

    # 2. Adiciona todas as quantidades (qtd) na mesma ordem
    for peca in pecas_para_requisitar:
        params_list.append(('qtd', str(peca.get('quantidade', ''))))

    # 3. Adiciona os 'local' vazios, um para cada peça
    for _ in pecas_para_requisitar:
        params_list.append(('local', ''))

    # 4. Adiciona os parâmetros fixos e o NumeroOS
    params_list.extend([
        ('IDUsuario', id_tecnico),          # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
        ('IP', '192.168.24.39'),      # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
        ('NumeroOS', numero_os),
        ('ObservacaoRequisicao', '')    # Fixo e vazio
    ])
    # ----------------------------------------------------

    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0", # Usando o User-Agent do exemplo
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?NumeroOSBusca={numero_os}", # Referer dinâmico com o numero_os
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6" # Usando o Accept-Language do exemplo
        # O Cookie JSESSIONID será gerenciado pela session do requests
    }

    try:
        print(f"[*] Enviando requisição para requisitar peças da OS: {numero_os}")
        print(f"[*] URL: {url}")
        print(f"[*] Parâmetros: {params_list}") # Imprime a lista de tuplas para depuração
        print(f"[*] Headers: {headers}")

        # A biblioteca requests codificará a lista de tuplas params_list corretamente na URL
        response = session.get(url, params=params_list, headers=headers, timeout=180) # Timeout de 180 segundos

        # Verifica se houve erro HTTP (status code 4xx ou 5xx)
        response.raise_for_status()

        print(f"[*] Resposta Recebida (Status: {response.status_code})")
        # Tenta decodificar a resposta como JSON
        try:
            resposta_json = response.json()
            print(f"[*] Resposta JSON: {json.dumps(resposta_json, indent=2)}") # Imprime a resposta formatada

            # Verifica a condição de sucesso conforme especificado
            if resposta_json.get("success") is True and \
               resposta_json.get("message", "").startswith("Code: 10011 - Sucesso"):
                print("[+] Requisição de peças bem-sucedida!")
                return True
            else:
                print(f"[-] Requisição enviada, mas a resposta não indica sucesso total.")
                print(f"[-] Success: {resposta_json.get('success')}")
                print(f"[-] Message: {resposta_json.get('message')}")
                return False

        except json.JSONDecodeError:
            print(f"[-] Erro: A resposta não é um JSON válido.")
            print(f"[*] Conteúdo da Resposta:\n{response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[!] Erro durante a requisição HTTP: {e}")
        return False
    except Exception as e:
        print(f"[!] Erro inesperado na função requisitar_pecas_cos: {e}")
        return False

"""if __name__ == "__main__":
    resultado = filtrar_pecas_req("350604")  # Exemplo de chamada da função
    if resultado == "StatusError":
        print("Erro: Status da OS não permite requisição de peças.")"""

def alterar_status_tecnico_designado_cos(numero_os):
    """
    Altera o status de uma Ordem de Serviço (OS) no COS para 'Técnico Designado' (S02/M10).

    Envia uma requisição GET para replicar a alteração de status via interface web.

    Args:
        session: Objeto de sessão requests pré-configurado.
        numero_os: O número da Ordem de Serviço (como string) a ser alterada.

    Returns:
        True se a requisição foi enviada e a resposta indica sucesso na alteração,
        False caso contrário.
    """
    url = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServico"

    # Obter data e hora atual no formato ddMMyyyyHHmmss
    agora = datetime.now()
    data_hora_atual_formatada = agora.strftime("%d%m%Y%H%M%S")

    # Parâmetros da requisição GET
    params = {
        "Acao": "AlteracaoEspecialStatus",
        "IP": "192.168.24.39",       # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
        "IDUsuario": "1417",         # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
        "Status": "S02",             # Status para "Técnico Designado"
        "Motivo": "M10",             # Motivo associado no exemplo
        "NumeroOS": numero_os,       # Número da OS fornecido
        "Observacao": "REQUISITANDO PEÇAS", # Observação fixa conforme exemplo (requests cuidará do encoding)
        "DataAtualAlteracaoOS": data_hora_atual_formatada # Data/Hora dinâmica formatada
    }

    # Cabeçalhos da requisição
    # O Referer inclui parâmetros fixos extraídos do exemplo. Verifique se são adequados.
    referer_url = (
        f"http://192.168.25.131:8080/COS_CSO/AdministrarOS.jsp?"
        f"NumeroOS={numero_os}&CodigoTecnico=CSA&QuantidadePecaUsadaNaOS=0&"
        f"NumeroGarantia=&IDEmprestimo=&CodigoMotivo=M10&TipoAtendimento=FGR"
    )

    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": referer_url,
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
        # O Cookie JSESSIONID será gerenciado pela session do requests
    }

    try:

        # Faz a requisição GET
        response = session.get(url, params=params, headers=headers, timeout=30) # Timeout de 30 segundos

        # Verifica se houve erro HTTP (status code 4xx ou 5xx)
        response.raise_for_status()

        # Tenta decodificar a resposta como JSON
        try:
            resposta_json = response.json()
            # Imprime a resposta formatada para depuração

            # Verifica a condição de sucesso conforme a resposta de exemplo {"Sucesso": true, ...}
            # Note a capitalização de "Sucesso"
            if resposta_json.get("Sucesso") is True:
                print(f"[+] Status da OS {numero_os} alterado com sucesso para 'Técnico Designado'.")
                return True
            else:
                print(f"[-] Requisição enviada, mas a resposta não indica sucesso.")
                print(f"[-] Sucesso: {resposta_json.get('Sucesso')}")
                print(f"[-] Mensagem: {resposta_json.get('Mensagem')}")
                return False

        except json.JSONDecodeError:
            print(f"[-] Erro: A resposta não é um JSON válido.")
            print(f"[*] Conteúdo da Resposta:\n{response.text}")
            return False

    except requests.exceptions.RequestException as e:
        print(f"[!] Erro durante a requisição HTTP: {e}")
        return False
    except Exception as e:
        print(f"[!] Erro inesperado na função alterar_status_tecnico_designado_cos: {e}")
        return False


def preparar_dados_para_formulario_requisicao(os: str) -> dict:
    """
    Orquestra a coleta e validação de dados para preencher o formulário de requisição.

    Args:
        os: O número da ordem de serviço (string).

    Returns:
        Um dicionário com:
        {
            "success": True,
            "data": { ... dados para o formulário ... }
        }
        ou
        {
            "success": False,
            "error_type": "TipoDoErro", # ex: "StatusError", "BudgetError", "GenericError"
            "message": "Mensagem descritiva do erro."
        }
    """
    print(f"\n--- Iniciando preparação para OS: {os} ---")
    parts_to_remove = [] # Inicializa como lista vazia
    pecas_inseridas = coletar_dados_os(os)
    usadas_cos = pecas_inseridas.get("pecas_usadas", {}) # Coleta as peças usadas na OS para comparação
    # 1. Filtrar Peças e Verificar Status GSPN
    try:
        resultado_filtro = filtrar_pecas_req(os)
        print(f"DEBUG: Resultado do filtro de peças: {resultado_filtro}")
        
        if resultado_filtro == "StatusError":
            print("ERRO: Status da OS no GSPN incompatível.")
            return {
                "success": False,
                "error_type": "StatusError",
                "message": "Verifique o status da OS do GSPN e se possui técnico designado."
            }
        elif isinstance(resultado_filtro, list):
            parts_to_remove = resultado_filtro
            print(f"INFO: Peças a serem removidas do GSPN identificadas: {parts_to_remove}")
        elif resultado_filtro is False: # Erro não tratado em filtrar_pecas_req
             print("ERRO: Falha não tratada ao filtrar peças.")
             return {
                "success": False,
                "error_type": "GenericError",
                "message": "Ocorreu um erro interno ao verificar as peças iniciais."
             }
        # Se for True, parts_to_remove continua vazia, fluxo segue.
        print("INFO: Filtro inicial OK.")

    except Exception as e:
        print(f"ERRO CRÍTICO em filtrar_pecas_req: {e}")
        return {
            "success": False,
            "error_type": "GenericError",
            "message": f"Erro inesperado ao verificar status/peças: {e}"
        }

    # 2. Coletar Dados da Requisição
    try:
        dados_coletados = coletar_pecas_requisitar(os)
        pecas_raw = dados_coletados.get('pecas_requisitar', [])
        orcamento_aprovado = dados_coletados.get('orcamento', False)
        nome_tecnico = dados_coletados.get('tecnico')
        status_os = dados_coletados.get('status_os') # Assumindo que esta função retorna o status

        print(f"INFO: Dados coletados. Orçamento aprovado: {orcamento_aprovado}")

        # 3. Verificar Orçamento
        if not orcamento_aprovado:
            print("ERRO: Orçamento não está aprovado.")
            return {
                "success": False,
                "error_type": "BudgetError",
                "message": "Orçamento não aprovado para esta OS."
            }

        # 4. Listar Usuários
        lista_usuarios = listar_nomes_usuarios()
        print(f"INFO: Lista de usuários obtida: {lista_usuarios}")

        # 5. Obter Requisições Pendentes
        requisicoes_pendentes = obter_ids_requisicoes_pendentes(os)
        if requisicoes_pendentes is None:
            requisicoes_pendentes = [] # Trata None como lista vazia por consistência
        print(f"INFO: Requisições pendentes obtidas: {requisicoes_pendentes}")

        # 6. Formatar Lista de Peças para o Frontend
        pecas_formatadas = []
        for item in pecas_raw:
            pecas_formatadas.append({
                "codigo": item.get("code", ""),
                "descricao": item.get("description", ""),
                "quantidade": item.get("qtd", 1),
                "keyname": item.get("keyname", ""), # keyname é o ID da peça
                # Inclua outros campos se o frontend precisar deles inicialmente
                # "keyname": item.get("keyname", ""),
                # "coverage_id": item.get("coverage_id", "")
            })
        print(f"INFO: Peças formatadas para formulário: {pecas_formatadas}")

        # 7. Preparar Avisos
        aviso_status_os = (status_os != "Técnico Designado")
        aviso_requisicoes_pendentes = bool(requisicoes_pendentes) # True se a lista não for vazia

        print(f"INFO: Aviso Status OS: {aviso_status_os}, Aviso Pendências: {aviso_requisicoes_pendentes}")

        # 8. Montar Resposta de Sucesso
        dados_para_frontend = {
            "pecas_para_requisitar": pecas_formatadas,
            "nome_tecnico_sugerido": nome_tecnico,
            "lista_usuarios": lista_usuarios,
            "status_os_cos": status_os,
            "aviso_status_os": aviso_status_os,
            "requisicoes_pendentes": requisicoes_pendentes,
            "aviso_requisicoes_pendentes": aviso_requisicoes_pendentes,
            "parts_to_remove": parts_to_remove, # Lista de peças a remover (pode estar vazia)
            "usadas_cos": usadas_cos # Lista de peças usadas na OS
        }

        print("--- Preparação concluída com sucesso ---")
        return {
            "success": True,
            "data": dados_para_frontend
        }

    except Exception as e:
        print(f"ERRO CRÍTICO durante coleta/processamento: {e}")
        import traceback
        traceback.print_exc() # Imprime o stack trace para debug
        return {
            "success": False,
            "error_type": "GenericError",
            "message": f"Erro inesperado ao preparar dados: {e}"
        }



def processar_submissao_requisicao(dados_recebidos: dict) -> dict:
    """
    Processa os dados recebidos do formulário do frontend, formata-os
    e chama a função para requisitar peças no COS.

    Args:
        dados_recebidos: Um dicionário representando o JSON enviado pelo frontend.
                         Exemplo esperado:
                         {
                             "os": "123456",
                             "usuario_selecionado": "Nome Usuario",
                             "pecas_final": [{"codigo": "P1", "quantidade": 1}, ...],
                             "parts_to_remove_original": [{"codigo": "P2", "quantidade": 1}, ...] ou []
                         }

    Returns:
        Um dicionário indicando o resultado da operação:
        {
            "success": True/False,
            "message": "Mensagem descritiva."
        }
    """
    print(f"\n--- Iniciando processamento da submissão ---")
    print("DEBUG: Dados recebidos do frontend (simulado):")
    print(json.dumps(dados_recebidos, indent=4, ensure_ascii=False))

    # 1. Extrair dados (com alguma segurança usando .get)
    try:
        os_submetida = dados_recebidos.get("os")
        usuario_final = dados_recebidos.get("usuario_selecionado")
        pecas_finais_usuario = dados_recebidos.get("pecas_final", [])
        pecas_originais_remover = dados_recebidos.get("parts_to_remove_original", [])
        aviso_status = dados_recebidos.get("aviso_status_os_original", False)
        # Validação básica (pode ser expandida)
        if not os_submetida or not usuario_final:
            print("ERRO: Informações essenciais (OS ou Usuário) faltando nos dados recebidos.")
            return {
                "success": False,
                "message": "Erro na submissão: OS ou usuário não fornecido."
            }

        # Garantir que 'pecas_originais_remover' seja uma lista
        if pecas_originais_remover is None:
             pecas_originais_remover = []

    except Exception as e:
         print(f"ERRO ao extrair dados da submissão: {e}")
         return {
            "success": False,
            "message": f"Erro interno ao ler os dados submetidos: {e}"
        }

    # 2. Montar o dicionário 'dados_full' para requisitar_pecas_cos
    #    Usando a estrutura que definimos anteriormente.
    dados_full_para_cos = {
        "ordem_servico": os_submetida,
        "usuario_responsavel": usuario_final,
        "pecas_a_requisitar": pecas_finais_usuario, # A lista já deve vir no formato correto do front
        "pecas_a_remover_gspn": pecas_originais_remover, # A lista original que veio da preparação
        "status_os": aviso_status, # Status da OS para verificação
    }


    print("\nDEBUG: Dicionário 'dados_full' montado para enviar ao COS:")
    print(json.dumps(dados_full_para_cos, indent=4, ensure_ascii=False))

    # 3. Chamar a função core de requisição e tratar o resultado
    try:
        sucesso_requisicao = requisitar_pecas_cos(dados_full_para_cos)

        if sucesso_requisicao:
            print("INFO: Requisição no COS processada com sucesso.")
            return {
                "success": True,
                "message": "Peças requisitadas com sucesso no sistema COS."
            }
        else:
            print("ERRO: A função requisitar_pecas_cos retornou False.")
            # Idealmente, requisitar_pecas_cos poderia fornecer mais detalhes do erro.
            return {
                "success": False,
                "message": "Falha ao requisitar peças no sistema COS. Verifique os logs ou tente novamente."
            }

    except Exception as e:
        print(f"ERRO CRÍTICO durante a chamada a requisitar_pecas_cos: {e}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Erro inesperado durante a requisição no COS: {e}"
        }

def processar_submissao_requisicao_para_fila(dados_recebidos, sid, queue, lock, processing_set):
    """
    Versão que executa a lógica e coloca o resultado na fila.
    """
    os_numero = dados_recebidos.get('os')
    if not os_numero:
        logging.error("processar_submissao_requisicao_para_fila: OS não fornecida.")
        return # Não pode prosseguir sem OS

    try:
        # 1. Informa que iniciou
        logging.info(f"[{os_numero}] Req Fila: Iniciando processamento.")
        queue.put({'os': os_numero, 'step': 'Processando requisição', 'status': 'running', 'sid': sid, 'type': 'requisition_progress'})
        time.sleep(0.5) # Pequena pausa para garantir que o 'processing' chegue

        # --- CHAMADA PARA A SUA LÓGICA ORIGINAL ---
        # Você chama sua função original aqui.
        # Ela retorna um dicionário como {'success': True/False, 'message': '...'}
        resultado_dict = processar_submissao_requisicao(dados_recebidos)
        sucesso = resultado_dict.get("success", False) # Pega o booleano
        mensagem = resultado_dict.get("message", "")
        # -----------------------------------------

        # 2. Coloca o resultado final na fila
        final_status = 'completed' if sucesso else 'failed'
        final_message = mensagem if mensagem else ('Concluído' if sucesso else 'Falha')

        logging.info(f"[{os_numero}] Req Fila: Processamento finalizado. Status: {final_status}")
        if sucesso:
            queue.put({'os': os_numero, 'step': 'Finalizado', 'status': 'completed', 'sid': sid, 'type': 'requisition_progress'})
        else:
            queue.put({'os': os_numero, 'step': 'Falha', 'status': 'failed', 'sid': sid, 'type': 'requisition_progress'})
            logging.error(f"[{os_numero}] Req Fila: Falha na requisição. Mensagem: {mensagem}")

    except Exception as e:
        # 3. Em caso de erro inesperado na lógica original
        error_message = f"Erro durante execução da requisição: {str(e)}"
        logging.error(f"[{os_numero}] Req Fila: {error_message}", exc_info=True)
        queue.put({'os': os_numero, 'step': 'Falha', 'status': 'failed', 'sid': sid, 'type': 'requisition_progress'})
    finally:
        # 4. Limpa o set de controle, independentemente do resultado
        with lock:
            if os_numero in processing_set:
                processing_set.remove(os_numero)
                logging.info(f"[{os_numero}] Req Fila: Removido do set.")


def cancelar_requisicoes_pendentes_cos(lista_ids_requisicao: list, numero_os: str):
    """
    Cancela uma ou mais requisições de peças pendentes no sistema COS.

    Itera sobre a lista de IDs de requisição fornecida e envia uma requisição
    HTTP GET para cada ID para solicitar o cancelamento.

    Args:
        session: Objeto de sessão requests pré-configurado.
        lista_ids_requisicao: Uma lista de strings, onde cada string é um ID
                               de requisição a ser cancelado ("IDSolicitacao").
        numero_os: O número da Ordem de Serviço associada (como string).

    Returns:
        bool: True se TODAS as requisições de cancelamento foram bem-sucedidas,
              False se alguma falhar (erro HTTP, erro de rede, ou resposta
              do servidor indicando falha).
    """
    if not lista_ids_requisicao:
        print("Aviso: A lista de IDs de requisição para cancelar está vazia.")
        return True # Considera sucesso pois não havia nada a fazer

    url = "http://192.168.25.131:8080/COS_CSO/ControleEstoque"

    # Cabeçalhos da requisição (maioria fixa, incluindo Referer neste caso)
    headers = {
        "Host": "192.168.25.131:8080",
        "Connection": "keep-alive",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0",
        "Accept": "*/*",
        "X-Requested-With": "XMLHttpRequest",
        # Referer fixo conforme exemplo para esta ação específica
        "Referer": "http://192.168.25.131:8080/COS_CSO/PecasRequisitadasPeloLaboratorio.jsp",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
    }

    # Itera sobre cada ID de requisição para enviar uma solicitação de cancelamento
    for id_req in lista_ids_requisicao:
        print(f"\n[*] Tentando cancelar requisição ID: {id_req} para OS: {numero_os}")

        # Obter data e hora atual para cada requisição no formato ddMMyyyyHHmmss
        agora = datetime.now()
        data_hora_atual_formatada = agora.strftime("%d%m%Y%H%M%S")

        # Parâmetros da requisição GET (montados para cada ID)
        params = {
            "Acao": "AtualizarStatusRequisicaoPeca",
            "IDUsuario": "1417",          # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
            "IP": "192.168.24.39",        # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
            "IDSolicitacao": str(id_req), # ID da requisição atual do loop
            "Motivo": "CNC",              # Motivo fixo para cancelamento no exemplo
            "ObservacaoRejeicao": "NOVA REQUISIÇÃO", # Observação fixa (requests codificará)
            "DataAtualAlteracao": data_hora_atual_formatada, # Data/Hora dinâmica
            "NomeUsuario": "LucianoOliveira", # Fixo conforme exemplo - ATENÇÃO: Pode precisar ser dinâmico
            "AuxNumeroOS": numero_os      # Número da OS associada
        }

        try:
            # print(f"[*] Parâmetros: {params}") # Descomente para depurar params
            response = session.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status() # Verifica erros HTTP (4xx, 5xx)

            print(f"[*] Resposta Recebida para ID {id_req} (Status: {response.status_code})")

            # Tenta decodificar a resposta como JSON
            try:
                resposta_json = response.json()
                print(f"[*] Resposta JSON para ID {id_req}: {json.dumps(resposta_json, indent=2)}")

                # Verifica a condição de sucesso específica desta API
                sucesso = resposta_json.get("Sucesso")
                mensagem = resposta_json.get("Mensagem")

                if sucesso is True and mensagem == "Status atualizado com sucesso.":
                    print(f"[+] Requisição ID {id_req} cancelada com sucesso.")
                    # Continua para o próximo ID no loop
                else:
                    print(f"[-] Falha ao cancelar requisição ID {id_req}.")
                    print(f"[-] Resposta do Servidor: Sucesso={sucesso}, Mensagem='{mensagem}'")
                    return False # Interrompe e retorna falha se qualquer uma falhar

            except json.JSONDecodeError:
                print(f"[-] Erro: A resposta para ID {id_req} não é um JSON válido.")
                print(f"[*] Conteúdo da Resposta:\n{response.text}")
                return False # Interrompe e retorna falha

        except requests.exceptions.Timeout:
            print(f"[!] Erro de Timeout ao tentar cancelar requisição ID {id_req}.")
            return False # Interrompe e retorna falha
        except requests.exceptions.RequestException as e:
            print(f"[!] Erro durante a requisição HTTP para ID {id_req}: {e}")
            return False # Interrompe e retorna falha
        except Exception as e:
            print(f"[!] Erro inesperado ao processar ID {id_req}: {e}")
            return False # Interrompe e retorna falha

    # Se o loop terminar sem retornar False, todas as requisições foram bem-sucedidas
    print("\n[+] Todas as requisições de cancelamento foram processadas com sucesso.")
    return True









if __name__ == "__main__":
    os_numero = "351339"
    result = preparar_dados_para_formulario_requisicao(os_numero)
    if result["success"]:
        print(f"Dados preparados com sucesso para a OS {os_numero}: {result['data']}")
    else:
        print(f"Falha ao preparar dados para a OS {os_numero}: {result['message']}")
