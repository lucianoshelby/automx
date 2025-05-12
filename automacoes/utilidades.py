from selenium.webdriver.common.alert import Alert
from selenium.common.exceptions import TimeoutException, NoSuchElementException, NoSuchWindowException, NoAlertPresentException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import re

def fechar_popups(driver, timeout=10):
    """
    Fecha popups internos ou alertas do navegador usando WebDriverWait intercalados.
    Prioriza alertas para evitar erros quando eles aparecem primeiro.
    """
    popup_detectado = False
    print("🔍 Iniciando verificação de popups...")

    # Calcula o número de tentativas (timeout / 2, pois cada iteração tem 2 segundos no total)
    num_tentativas = timeout // 2
    print(f"ℹ️ Total de tentativas: {num_tentativas}")

    # Laço principal com tentativas intercaladas
    for tentativa in range(num_tentativas):
        print(f"🔄 Tentativa {tentativa + 1}/{num_tentativas}")

        # 1️⃣ Verifica alerta do navegador primeiro (1 segundo)
        try:
            print("🔎 Verificando alerta do navegador...")
            WebDriverWait(driver, 1).until(EC.alert_is_present())
            alert = driver.switch_to.alert
            print("🔴 Alerta do navegador detectado.")
            alert.accept()
            print("✅ Alerta aceito com sucesso.")
            popup_detectado = True
            break  # Sai do laço após aceitar o alerta

        except TimeoutException:
            print("ℹ️ Nenhum alerta presente nesta tentativa.")

        # 2️⃣ Verifica popup interno (1 segundo), mas só se não houver alerta
        try:
            print("🔎 Verificando popup interno...")
            WebDriverWait(driver, 1).until(
                lambda driver: driver.find_element(By.ID, "divConfirmNotice").is_displayed()
            )
            print("⚠️ Popup interno visível detectado.")
            popup_detectado = True
            
            # Trata o popup interno
            botao_salvar = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((
                    By.XPATH, 
                    "//div[@id='divConfirmNotice']//a[@onclick=\"saveServiceOrder('WARNING_SKIP');return false;\"]"
                ))
            )
            print("🔍 Botão 'Salvar' encontrado.")
            try:
                botao_salvar.click()
                print("✅ Popup interno salvo com sucesso.")
            except Exception as e:
                print(f"❌ Erro ao clicar em 'Salvar': {e}")
                driver.execute_script("arguments[0].click();", botao_salvar)
                print("✅ Clique via JavaScript executado.")
            
            break  # Sai do laço após tratar o popup interno

        except TimeoutException:
            print("ℹ️ Nenhum popup interno visível nesta tentativa.")
        except WebDriverException as e:
            print(f"❌ Erro ao verificar popup interno (provavelmente devido a um alerta): {e}")
            # Tenta aceitar um alerta que pode ter aparecido durante a verificação
            try:
                alert = driver.switch_to.alert
                print("🔴 Alerta detectado após erro no popup interno.")
                alert.accept()
                print("✅ Alerta aceito com sucesso.")
                popup_detectado = True
                break
            except NoAlertPresentException:
                print("ℹ️ Nenhum alerta encontrado após erro.")

    # 3️⃣ Após detectar algo, verifica alertas adicionais por 1 segundo
    if popup_detectado:
        print("🔍 Verificando alertas adicionais por 1 segundo...")
        start_time = time.time()
        while time.time() - start_time < 1:
            try:
                alert = driver.switch_to.alert
                print("🔴 Novo alerta do navegador detectado.")
                alert.accept()
                print("✅ Alerta adicional aceito.")
            except NoAlertPresentException:
                time.sleep(0.1)
        print("✅ Verificação de alertas adicionais concluída.")

    # 4️⃣ Resultado final
    if not popup_detectado:
        print("❌ Nenhum popup ou alerta foi detectado. O processo pode ter falhado.")
    
    return True

"""
def fechar_popups(driver, timeout=60):
    ""Fecha popups do navegador ou o popup interno de confirmação. Se nenhum popup for encontrado, retorna erro.""

    popup_detectado = False  # Flag para verificar se pelo menos um popup foi detectado

    try:
        print("🔍 Verificando se há popup interno (divConfirmNotice)...")
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.ID, "divConfirmNotice"))
        )
        print("⚠️ Popup interno detectado. Clicando em 'Salvar'...")
        time.sleep(1)
        
        try:
            #botao_salvar = driver.find_element(By.XPATH, "//div[@id='divConfirmNotice']//a[@onclick=\"saveServiceOrder('WARNING_SKIP');return false;\"]")
            print("🔍 Botão 'Salvar' encontrado.")
            botao_salvar = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'Salvar') and @onclick=\"saveServiceOrder('WARNING_SKIP');return false;\"]"))
            )

             #Tente clicar normalmente
            botao_salvar.click()
            print("✅ Clique executado normalmente.")
            
            # Alternativa com JavaScript
            
            #driver.execute_script("arguments[0].click();", botao_salvar)
            #print("✅ Clique via JavaScript também foi executado.")
            
        except Exception as e:
            print(f"❌ Erro ao clicar no botão 'Salvar': {e}")
        
        print("pós salvar popup")
        print("✅ Popup interno fechado com sucesso.")
        popup_detectado = True
    except Exception as e:
        print(f"✅ Nenhum popup interno detectado ou erro: {e}")

    try:
        # 1️⃣ Fechar popups do navegador (alert)
        WebDriverWait(driver, 3).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        print("🔴 Fechando popup do navegador...")
        alert.accept()
        popup_detectado = True  # Marcamos que um popup foi encontrado

    except:
        print("✅ Nenhum popup do navegador detectado.")

    

    # 3️⃣ Se nenhum popup foi detectado, retornar erro
    if not popup_detectado:
        raise Exception("❌ Nenhum popup foi detectado. O processo pode ter falhado.")
    return True"""
    


def esperar_elemento_visivel(driver, xpath, timeout=10):
    """Aguarda até que um elemento esteja visível na página."""
    try:
        WebDriverWait(driver, timeout).until(EC.visibility_of_element_located((By.XPATH, xpath)))
        return True
    except TimeoutException:
        return False

def esperar_elemento_clicavel(driver, xpath, timeout=10):
    """Aguarda até que um elemento esteja visível e clicável na página."""
    try:
        WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, xpath)))
        return True
    except TimeoutException:
        return False

def esperar_popup(driver, timeout=5):
    """Aguarda e fecha todos os popups que aparecerem."""
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        # Uma vez que o primeiro popup é detectado e fechado, mudar a lógica para os próximos
        while True:
            alert = driver.switch_to.alert
            print("🔴 Fechando popup do navegador...")
            alert.accept()
            # Espera curta de 1 segundo para verificar se há mais popups
            try:
                WebDriverWait(driver, 1).until(EC.alert_is_present())
            except:
                # Se não aparecer mais nenhum popup em 1 segundo, sair do loop
                print("✅ Nenhum popup adicional detectado.")
                break
            #time.sleep(1)  # Pequena pausa para estabilização do DOM
    except:
        print("✅ Nenhum popup do navegador detectado.")


    """except TimeoutException:
        print("❌ Nenhum popup detectado após 2 minutos. O salvamento pode não ter sido concluído!")
        return False

def esperar_popup(driver, timeout=2):
    #Aguarda e fecha todos os popups que aparecerem.
    try:
        while True:
            try:
                WebDriverWait(driver, timeout).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print("🔴 Fechando popup do navegador...")
                alert.accept()
                time.sleep(0.5)  # Pequena pausa para verificar se há mais popups
            except NoSuchWindowException:
                return True
    except TimeoutException:
        print("✅ Nenhum novo popup detectado. Continuando...")"""

def localizar_aba_gspn(driver):
    """Extrai o número da OS dentro do tr correto no formulário 'detailForm'."""
    try:
        # Esperar o elemento estar visível antes de tentar localizá-lo
        os_elemento = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, "//tr[@onclick=\"javascript: toggleTable('Main');\"]//span[contains(@title, 'Object ID')]"))
        )

        # Obter o texto visível do elemento
        os_text = os_elemento.text

        # Regex para capturar o primeiro número de 10 dígitos
        match = re.search(r'\b\d{10}\b', os_text)

        if match:
            os_extraida = match.group(0)  # Retorna apenas o número da OS encontrado
            print(f"✅ OS extraída com sucesso: {os_extraida}")
            return os_extraida

        print(f"⚠️ Não foi possível extrair a OS do texto: {os_text}")
        return None

    except Exception as e:
        print(f"❌ Erro ao localizar a OS: {e}")
        return None

    except Exception as e:
        print(f"❌ Erro ao localizar a OS: {e}")
        return None
    
def popup_curto(driver, timeout=3):
    """
    Aguarda e fecha um popup de alerta, se aparecer.
    """
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert = driver.switch_to.alert
        alert.accept()
        print('Popup curto fechado!')
        input('pausa')
    except TimeoutException:
        print("Nenhum popup de alerta apareceu.")

def gerenciar_popup_e_janela(driver, original_window, popup_handle, timeout=5):
    print('inciando gerenciar popup')
    """Função auxiliar para lidar com popups e fechamento de janelas."""
    try:
        # Aguarda um alerta e o aceita
        alert = WebDriverWait(driver, timeout).until(EC.alert_is_present())
        alert_text = alert.text
        print(f"🔴 Popup detectado com texto: '{alert_text}'")
        alert.accept()

        # Verifica se a janela popup ainda existe após aceitar o alerta
        if popup_handle in driver.window_handles:
            # Se a janela não fechou automaticamente, verifica o texto do alerta para decidir o próximo passo
            if "success" in alert_text.lower() or "Registered Stock is not found!" in alert_text:
                print("✅ Janela deve fechar automaticamente após 'success' ou estoque não encontrado.")
            elif "Material number for service already exists" in alert_text:
                print("🔧 Solicitação já existe, fechando janela manualmente.")
                driver.switch_to.window(popup_handle)
                driver.close()
        else:
            print("✅ Janela popup já foi fechada pelo alerta.")
        
        # Volta para a janela original
        if original_window in driver.window_handles:
            driver.switch_to.window(original_window)
            print("✅ Retornou para a janela original.")
        else:
            print("⚠️ Janela original não encontrada, usando a primeira disponível.")
            driver.switch_to.window(driver.window_handles[0])
        
        return alert_text  # Retorna o texto do alerta para análise posterior
    except TimeoutException:
        print("✅ Nenhum popup detectado.")
        return None
    except Exception as e:
        print(f"⚠️ Erro ao gerenciar popup/janela: {e}")
        if popup_handle in driver.window_handles:
            driver.switch_to.window(popup_handle)
            driver.close()
        driver.switch_to.window(original_window)
        return None