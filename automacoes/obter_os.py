from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

def obter_os_correspondentes(driver, os_input):
    """Obtém as OS do COS e do GSPN a partir de uma única entrada."""

    #original_window = driver.current_window_handle  # Salvar a aba original

    if len(os_input) == 10:  # Se for OS do GSPN
        print(f"🔍 Buscando OS do COS para a OS do GSPN {os_input}...")

        url_busca_cos = "http://192.168.25.131:8080/COS_CSO/BuscarOrdemServico.jsp"
        driver.execute_script(f"window.open('{url_busca_cos}', '_blank');")
        # Criar uma nova aba e alternar para ela
        #driver.execute_script("window.open('');")  # Criar uma nova aba vazia
        time.sleep(3)  # Pausa para garantir que a aba foi criada

        # Mudar para a nova aba criada
        #driver.switch_to.window(driver.window_handles[-1])  # Mudar para a nova aba

        # Carregar a URL na nova aba
        #driver.get(url_busca_cos)

        os_cos = None
        os_gspn = None

        try:
            # Localizar o campo de entrada da OS e inserir a OS do GSPN
            input_os = driver.find_element(By.ID, "OSFabricante")
            input_os.clear()
            input_os.send_keys(os_gspn)
            input_os.send_keys(Keys.RETURN)
            
            # Pequeno delay para garantir que a OS apareça na página
            time.sleep(1)
            
            # Coletar a OS do COS exibida na página
            elemento_os = driver.find_element(By.ID, "OrdemServico").text
            partes = elemento_os.split(" / ")
            os_cos = partes[0] if partes else ""
            # Capturar a OS do COS após a busca
            """elemento_os = driver.find_element(By.ID, "OrdemServico").text
            partes = elemento_os.split(" / ")
            os_cos = partes[0]
            os_gspn = os_input
            print(f"✅ OS do COS encontrada: {os_cos}")"""
            return os_cos
        except Exception as e:
            print(f"❌ Erro ao buscar OS do COS: {e}")
            os_cos = None

        """finally:
            # Fechar a aba da busca e voltar para a aba original
            #driver.close()
            #driver.switch_to.window(original_window)  # Voltar para a aba original
            time.sleep(2)

    return os_cos, os_gspn"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

def coleta_os_cos(driver, lista_os_gspn):
    """
    Consulta uma lista de OS do GSPN no sistema COS e retorna um dicionário com as OS correspondentes,
    status e tipo de atendimento.
    
    :param driver: Instância do WebDriver do Selenium já autenticado no COS.
    :param lista_os_gspn: Lista de números de OS do GSPN a serem consultadas.
    :return: Dicionário onde as chaves são OS do GSPN e os valores são dicionários com OS do COS, status e tipo de atendimento.
    """
    #os_dados = {}
    
    for os_gspn in lista_os_gspn:
        try:
            # Localizar o campo de entrada da OS e inserir a OS do GSPN
            input_os = driver.find_element(By.ID, "OSFabricante")
            input_os.clear()
            input_os.send_keys(os_gspn)
            input_os.send_keys(Keys.RETURN)
            
            # Pequeno delay para garantir que a OS apareça na página
            time.sleep(1)
            
            # Coletar a OS do COS exibida na página
            elemento_os = driver.find_element(By.ID, "OrdemServico").text
            partes = elemento_os.split(" / ")
            os_cos = partes[0] if partes else ""
        except Exception as e:
            print(f"Erro ao processar OS {os_gspn}: {e}")
        return os_cos
    
    """# Capturar status da OS dentro do tbody correto
    status_element = driver.find_element(By.XPATH, "//tbody[@id='TblResumoOS']//div[@id='Status']")
    status_text = status_element.text.strip()
    
    # Capturar tipo de atendimento dentro do tbody correto
    tipo_atendimento_element = driver.find_element(By.XPATH, "//tbody[@id='TblResumoOS']//div[@id='Atendimento']")
    tipo_atendimento_text = tipo_atendimento_element.text.strip()
    
    # Remover quebras de linha, espaços extras e parênteses do tipo de atendimento
    tipo_atendimento_text = " ".join(tipo_atendimento_text.replace("(", "").replace(")", "").split())
    
    # Armazenar os resultados no dicionário
    os_dados[os_gspn] = {
        "os_cos": os_cos,
        "status": status_text,
        "tipo_atendimento": tipo_atendimento_text
    }

except Exception as e:
    print(f"Erro ao processar OS {os_gspn}: {e}")
    os_dados[os_gspn] = None
    
    return os_dados
"""