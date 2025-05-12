import requests
import json
import sys
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from cos.login_cos import carregar_sessao
from cos.coletar_dados_cos import coletar_dados_os



# Constantes
URL_VINCULAR_OS = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServico"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?NumeroOSBusca={NumeroOS}",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
}

def vincular_os(numero_os, numero_os_fabricante):
    """
    Envia uma requisição GET para vincular uma ordem de serviço no sistema COS.
    
    Args:
        numero_os (str): Número da ordem de serviço (ex.: '352682').
        numero_os_fabricante (str): Número da OS do fabricante (ex.: '4172879968').
    
    Returns:
        bool: True se a vinculação foi bem-sucedida (resposta contém {"Sucesso": true}), False caso contrário.
    
    Raises:
        requests.RequestException: Erro na requisição HTTP.
        ValueError: Resposta inválida ou falha na vinculação.
    """
    try:
        daodos_os = coletar_dados_os(numero_os)
    except Exception as e:
        print(f"Erro ao coletar dados da OS: {e}")
        raise

    # Parâmetros fixos da requisição
    params = {
        "Acao": "InserirNumeroOSFabricante",
        "IDUsuario": "1417",
        "IP": "192.168.24.97",
        "NumeroOSFabricante": numero_os_fabricante,
        "NumeroOS": numero_os,
        "CodigoStatus": daodos_os["CodigoStatus"],
        "CodigoMotivo": daodos_os["CodigoMotivo"],
        "TipoAtendimento": daodos_os["TipoAtendimento"],
        "SerialDeclaracao": daodos_os["Serial"],
    }

    # Atualiza o Referer com o NumeroOS
    headers = HEADERS.copy()
    headers["Referer"] = f"http://192.168.25.131:8080/COS_CSO/EditarOrdemServico.jsp?NumeroOSBusca={numero_os}"
    session = carregar_sessao("Luciano Oliveira")
    try:
        # Envia a requisição GET
        response = session.get(
            URL_VINCULAR_OS,
            headers=headers,
            cookies=session.cookies,
            params=params,
            verify=False
        )
        response.raise_for_status()  # Levanta exceção para erros HTTP

        # Verifica a resposta
        data = response.json()
        if data.get("Sucesso") is True:
            return True
        else:
            raise ValueError(f"Falha na vinculação da OS: {data}")

    except requests.RequestException as e:
        print(f"Erro na requisição de vinculação da OS: {e}")
        raise
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Erro ao processar resposta da vinculação da OS: {e}")
        raise

if __name__ == "__main__":
    # Exemplo de uso da função
    numero_os = "352682"
    numero_os_fabricante = "4172879968"
    try:
        sucesso = vincular_os(numero_os, numero_os_fabricante)
        if sucesso:
            print(f"OS {numero_os} vinculada com sucesso!")
        else:
            print(f"Falha ao vincular a OS {numero_os}.")
    except Exception as e:
        print(f"Erro: {e}")