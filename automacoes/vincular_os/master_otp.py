import requests
import json
import os
from datetime import datetime, date
import sys 
sys.path.insert(0, 'C:\\Users\\Gestão MX\\Documents\\AutoMX\\automacoes')
from cos.login_cos import carregar_sessao
 

# Constantes
URL_BUSCA_COS = "http://192.168.25.131:8080/COS_CSO/ControleOrdemServicoGSPN"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
    "Accept": "*/*",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "http://192.168.25.131:8080/COS_CSO/PaginaInicial.jsp",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6"
}
OTP_FILE = "master_otp.json"

def get_master_otp():
    """
    Consulta o MasterOTP no sistema COS ou retorna o valor salvo se válido.
    Salva o OTP em um arquivo JSON com a data para reutilização no mesmo dia.
    Retorna o MasterOTP como string.
    """
    # Verifica se o arquivo existe e se o OTP é do mesmo dia
    """if os.path.exists(OTP_FILE):
        with open(OTP_FILE, 'r') as f:
            data = json.load(f)
            saved_date = datetime.strptime(data['DataOTP'], "%d-%m-%Y %H:%M:%S").date()
            print(f"Data salva: {saved_date}")
            print(f"Data atual: {date.today()}")
            if saved_date == date.today():
                print('otp valido, retornando...')
                return data['MasterOTP']"""

    # Se não há OTP válido, faz a requisição

    params = {"Acao": "BuscarDadosUltimoOTP"}
    session = carregar_sessao("Luciano Oliveira")
    try:
        response = session.get(
            URL_BUSCA_COS,
            headers=HEADERS,
            cookies=session.cookies,
            params=params,
            verify=False
        )
        response.raise_for_status()  # Levanta exceção para erros HTTP

        # Extrai o MasterOTP da resposta
        data = response.json()
        if data.get("Sucesso") and "DadosUltimoOTP" in data:
            master_otp = data["DadosUltimoOTP"]["MasterOTP"]
            data_otp = data["DadosUltimoOTP"]["DataOTP"]

            # Salva no arquivo
            """with open(OTP_FILE, 'w') as f:
                json.dump({"MasterOTP": master_otp, "DataOTP": data_otp}, f)"""

            return master_otp
        else:
            raise ValueError("Resposta da API não contém MasterOTP válido.")
    except requests.RequestException as e:
        print(f"Erro na requisição do MasterOTP: {e}")
        raise
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"Erro ao processar resposta do MasterOTP: {e}")
        raise

# Exemplo de como usar a função:
if __name__ == "__main__":
    master_otp_obtido = get_master_otp()
    if master_otp_obtido:
        print(f"Master OTP obtido: {master_otp_obtido}")
    else:
        print("Não foi possível obter o Master OTP.")